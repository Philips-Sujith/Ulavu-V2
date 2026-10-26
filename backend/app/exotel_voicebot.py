import json
import base64
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models import Retailer, InquiryLog, InquiryStatus
from app.matching import find_nearest_retailers, find_nearest_retailer
from app.sms import send_match_sms
from app.audio_service import text_to_s16le_pcm, PROMPTS, TAMIL_DIGIT_WORDS

logger = logging.getLogger("ulavu.voicebot")

# 9 Predefined Crops
CROP_OPTIONS: Dict[str, Dict[str, str]] = {
    "1": {"slug": "onion", "tamil": "வெங்காயம்"},
    "2": {"slug": "tomato", "tamil": "தக்காளி"},
    "3": {"slug": "potato", "tamil": "உருளைக்கிழங்கு"},
    "4": {"slug": "brinjal", "tamil": "கத்தரிக்காய்"},
    "5": {"slug": "carrot", "tamil": "கேரட்"},
    "6": {"slug": "cabbage", "tamil": "முட்டைக்கோஸ்"},
    "7": {"slug": "cauliflower", "tamil": "காலிஃப்ளவர்"},
    "8": {"slug": "okra", "tamil": "வெண்டைக்காய்"},
    "9": {"slug": "chilli", "tamil": "பச்சை மிளகாய்"},
}

# 9 Predefined Locations mapped to 5 Demo Retailers (Designated demo lines)
LOCATION_OPTIONS: Dict[str, Dict[str, str]] = {
    "1": {"name": "Madurantakam", "tamil": "மதுராந்தகம்", "fallback_phone": "9865741275"},
    "2": {"name": "Chengalpattu", "tamil": "செங்கல்பட்டு", "fallback_phone": "9865741275"},
    "3": {"name": "Kanchipuram", "tamil": "காஞ்சிபுரம்", "fallback_phone": "9644157852"},
    "4": {"name": "Tirukalukundram", "tamil": "திருக்கழுக்குன்றம்", "fallback_phone": "9644157852"},
    "5": {"name": "Uthiramerur", "tamil": "உத்திரமேரூர்", "fallback_phone": "9785632147"},
    "6": {"name": "Acharapakkam", "tamil": "அச்சரப்பாக்கம்", "fallback_phone": "9785632147"},
    "7": {"name": "Cheyyur", "tamil": "செய்யூர்", "fallback_phone": "9367821450"},
    "8": {"name": "Sriperumbudur", "tamil": "ஸ்ரீபெரும்புதூர்", "fallback_phone": "9367821450"},
    "9": {"name": "Walajabad", "tamil": "வாலாஜாபாத்", "fallback_phone": "9874516328"},
}

# Predefined In-Memory Demo Retailers (Designated demo accounts)
DEMO_RETAILER_FALLBACKS: Dict[str, Dict[str, str]] = {
    "9865741275": {"name": "முருகன் காய்கறி விற்பனை", "location": "மதுராந்தகம்", "phone": "9865741275"},
    "9644157852": {"name": "செல்வம் காய்கறி மையம்", "location": "காஞ்சிபுரம்", "phone": "9644157852"},
    "9785632147": {"name": "ராஜா விவசாய விற்பனை", "location": "உத்திரமேரூர்", "phone": "9785632147"},
    "9367821450": {"name": "குமார் காய்கறி வர்த்தகம்", "location": "செய்யூர்", "phone": "9367821450"},
    "9874516328": {"name": "அருண் வேளாண் விற்பனை", "location": "வாலாஜாபாத்", "phone": "9874516328"},
}

# 3200 bytes = 1600 samples at 8000Hz 16-bit mono = exactly 200ms (multiple of 320, >= 3200)
CHUNK_SIZE_BYTES = 3200
SAMPLE_RATE = 8000
SAMPLE_WIDTH = 2  # 16-bit signed PCM
BYTES_PER_SEC = SAMPLE_RATE * SAMPLE_WIDTH  # 16000 bytes/sec
DTMF_WAIT_TIMEOUT_SEC = 6.0

class ExotelVoicebotSession:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.stream_sid: str = ""
        self.call_sid: str = ""
        self.caller_phone: str = ""

        # State machine: WELCOME, CROP_SELECTION, LOCATION_SELECTION, SEARCHING, RESULT, END
        self.state: str = "WELCOME"
        self.crop_key: str = ""
        self.crop_slug: str = ""
        self.crop_tamil: str = ""

        self.location_key: str = ""
        self.location_name: str = ""
        self.location_tamil: str = ""

        # Attempt counters
        self.crop_attempt: int = 1
        self.location_attempt: int = 1

        # Playback synchronization
        self._speak_lock = asyncio.Lock()
        self._current_playback_task: Optional[asyncio.Task] = None
        self._dtmf_timer_task: Optional[asyncio.Task] = None
        self._is_terminating: bool = False
        self._sms_dispatched: bool = False
        self._matched_details: Optional[Dict[str, Any]] = None

    def _dispatch_match_sms_background(self):
        """Asynchronously dispatches Farmer & Retailer SMS without blocking call flow."""
        if self._sms_dispatched or not self._matched_details:
            return
        self._sms_dispatched = True
        details = self._matched_details

        def _worker():
            try:
                logger.info(f"[VOICEBOT SMS] Dispatching post-call SMS to Farmer & Retailer...")
                send_match_sms(
                    farmer_phone=details.get("farmer_phone") or self.caller_phone or "Exotel_Caller",
                    crop=details.get("crop") or self.crop_tamil or self.crop_slug,
                    location_spoken=details.get("location") or self.location_tamil or self.location_name,
                    business_name=details.get("retailer_name", ""),
                    retailer_location=details.get("retailer_location", ""),
                    retailer_phone=details.get("retailer_phone", ""),
                    distance_km=details.get("distance_km")
                )
            except Exception as e:
                logger.warning(f"[VOICEBOT SMS WARNING] Background SMS dispatch failed: {e}")

        asyncio.create_task(asyncio.to_thread(_worker))

    async def send_media_chunk(self, pcm_chunk: bytes, chunk_idx: int = 1, total_chunks: int = 1):
        """Sends raw s16le PCM audio chunk encoded with base64 to Exotel."""
        if not self.stream_sid:
            return

        payload = base64.b64encode(pcm_chunk).decode("ascii")
        msg = {
            "event": "media",
            "stream_sid": self.stream_sid,
            "streamSid": self.stream_sid,
            "media": {
                "payload": payload
            }
        }
        await self.ws.send_text(json.dumps(msg))

    async def send_clear(self):
        """Sends clear event to Exotel to interrupt/flush remaining audio buffer."""
        if not self.stream_sid:
            return
        msg = {
            "event": "clear",
            "stream_sid": self.stream_sid,
            "streamSid": self.stream_sid
        }
        try:
            await self.ws.send_text(json.dumps(msg))
            logger.info(f"[AUDIO] clear event sent to stream_sid={self.stream_sid}")
        except Exception:
            pass

    async def speak_text(self, text: str, interruptible: bool = True):
        """
        Synthesizes raw s16le PCM (8000Hz, mono) and streams in 3200-byte chunks
        at real-time pacing with strict concurrency locking.
        """
        async with self._speak_lock:
            try:
                # 1. Synthesize audio
                pcm_audio = await text_to_s16le_pcm(text)
                if not pcm_audio:
                    logger.warning(f"[AUDIO] Empty PCM generated for prompt: '{text[:30]}...'")
                    return

                total_bytes = len(pcm_audio)
                total_duration = total_bytes / BYTES_PER_SEC
                total_chunks = (total_bytes + CHUNK_SIZE_BYTES - 1) // CHUNK_SIZE_BYTES

                logger.info(
                    f"[AUDIO] PCM bytes={total_bytes} duration={total_duration:.2f}s "
                    f"chunks={total_chunks} prompt='{text[:40]}...'"
                )

                # Send clear before starting new speech to prevent overlapping
                await self.send_clear()

                for chunk_idx in range(total_chunks):
                    start_pos = chunk_idx * CHUNK_SIZE_BYTES
                    chunk = pcm_audio[start_pos:start_pos + CHUNK_SIZE_BYTES]

                    # Pad trailing chunk with zero samples to keep >= 3200 bytes & multiple of 320
                    if len(chunk) < CHUNK_SIZE_BYTES:
                        chunk = chunk + b"\x00" * (CHUNK_SIZE_BYTES - len(chunk))

                    chunk_duration = len(chunk) / BYTES_PER_SEC

                    await self.send_media_chunk(chunk, chunk_idx + 1, total_chunks)

                    # Real-time pacing (sleep for chunk duration)
                    if chunk_idx < total_chunks - 1:
                        await asyncio.sleep(chunk_duration * 0.98)

                logger.info(f"[AUDIO] playback complete for stream_sid={self.stream_sid}")

            except asyncio.CancelledError:
                logger.info(f"[AUDIO] Playback cancelled/interrupted for stream_sid={self.stream_sid}")
                await self.send_clear()
                raise
            except Exception as e:
                logger.error(f"[AUDIO ERROR]: {e}")

    async def speak_pcm(self, pcm_audio: bytes):
        """Streams pre-rendered raw s16le PCM bytes in 3200-byte chunks at real-time pacing."""
        async with self._speak_lock:
            try:
                total_bytes = len(pcm_audio)
                total_duration = total_bytes / BYTES_PER_SEC
                total_chunks = (total_bytes + CHUNK_SIZE_BYTES - 1) // CHUNK_SIZE_BYTES

                logger.info(
                    f"[AUDIO] PCM bytes={total_bytes} duration={total_duration:.2f}s "
                    f"chunks={total_chunks} [raw pcm stream]"
                )

                for chunk_idx in range(total_chunks):
                    start_pos = chunk_idx * CHUNK_SIZE_BYTES
                    chunk = pcm_audio[start_pos:start_pos + CHUNK_SIZE_BYTES]

                    if len(chunk) < CHUNK_SIZE_BYTES:
                        chunk = chunk + b"\x00" * (CHUNK_SIZE_BYTES - len(chunk))

                    chunk_duration = len(chunk) / BYTES_PER_SEC
                    await self.send_media_chunk(chunk, chunk_idx + 1, total_chunks)

                    if chunk_idx < total_chunks - 1:
                        await asyncio.sleep(chunk_duration * 0.98)

                logger.info(f"[AUDIO] playback complete for stream_sid={self.stream_sid}")

            except asyncio.CancelledError:
                logger.info(f"[AUDIO] Playback cancelled/interrupted for stream_sid={self.stream_sid}")
                await self.send_clear()
                raise
            except Exception as e:
                logger.error(f"[AUDIO ERROR]: {e}")

    async def speak_phone_number(self, phone: str, pause_ms: int = 500):
        """
        Reusable helper to speak a 10-digit phone number slowly digit-by-digit in Tamil
        with 400-600ms pauses between digits.
        """
        logger.info("[VOICEBOT] Speaking phone number slowly: **********")

        from app.audio_service import phone_number_to_slow_tamil_pcm
        slow_pcm = await phone_number_to_slow_tamil_pcm(phone, pause_ms=pause_ms)
        if slow_pcm:
            await self.speak_pcm(slow_pcm)

    def _cancel_current_playback(self):
        """Safely stops any active audio playback."""
        if self._current_playback_task and not self._current_playback_task.done():
            self._current_playback_task.cancel()
            self._current_playback_task = None

    def _cancel_dtmf_timer(self):
        """Cancels any pending DTMF wait timer."""
        if self._dtmf_timer_task and not self._dtmf_timer_task.done():
            self._dtmf_timer_task.cancel()
            self._dtmf_timer_task = None

    async def _play_and_wait(self, text: str, stage: str, attempt: int):
        """
        Helper that speaks a prompt, then starts the DTMF wait timeout timer.
        """
        self._cancel_dtmf_timer()
        self._current_playback_task = asyncio.create_task(self.speak_text(text))
        try:
            await self._current_playback_task
        except asyncio.CancelledError:
            return

        # Start waiting for DTMF after prompt playback finishes
        self._dtmf_timer_task = asyncio.create_task(self._dtmf_timeout_loop(stage, attempt))

    async def _dtmf_timeout_loop(self, stage: str, attempt: int):
        """
        Waits for DTMF input. If user doesn't press anything within timeout,
        handles retries or resets gracefully.
        """
        try:
            await asyncio.sleep(DTMF_WAIT_TIMEOUT_SEC)
            logger.info(f"[DTMF] Timeout on stage={stage} (attempt {attempt}/3)")

            if stage == "CROP_SELECTION":
                if attempt < 3:
                    logger.info(f"[VOICEBOT] Repeating crop menu (attempt {attempt + 1}/3)")
                    self.crop_attempt = attempt + 1
                    # Speak no input prompt, then replay crop menu
                    retry_text = f"{PROMPTS['NO_INPUT']} {PROMPTS['CROP_MENU']}"
                    await self._play_and_wait(retry_text, "CROP_SELECTION", self.crop_attempt)
                else:
                    logger.info("[VOICEBOT] 3 crop attempts failed. Restarting call flow.")
                    self.crop_attempt = 1
                    reset_text = f"{PROMPTS['MAX_RETRIES']} {PROMPTS['CROP_MENU']}"
                    await self._play_and_wait(reset_text, "CROP_SELECTION", 1)

            elif stage == "LOCATION_SELECTION":
                if attempt < 3:
                    logger.info(f"[VOICEBOT] Repeating location menu (attempt {attempt + 1}/3)")
                    self.location_attempt = attempt + 1
                    retry_text = f"{PROMPTS['NO_INPUT']} {PROMPTS['LOCATION_MENU']}"
                    await self._play_and_wait(retry_text, "LOCATION_SELECTION", self.location_attempt)
                else:
                    logger.info("[VOICEBOT] 3 location attempts failed. Restarting from crop menu.")
                    self.state = "CROP_SELECTION"
                    self.crop_attempt = 1
                    self.location_attempt = 1
                    reset_text = f"{PROMPTS['MAX_RETRIES']} {PROMPTS['CROP_MENU']}"
                    await self._play_and_wait(reset_text, "CROP_SELECTION", 1)

        except asyncio.CancelledError:
            pass

    async def handle_dtmf(self, digit: str):
        """
        DTMF is the AUTHORITATIVE input.
        Safely validates input, cancels active playback, and advances the state machine.
        """
        logger.info(f"[DTMF] Received: '{digit}' in state: {self.state}")

        # Cancel timeout timer immediately upon receiving input
        self._cancel_dtmf_timer()

        # Interrupt current playback cleanly
        self._cancel_current_playback()

        if self.state == "CROP_SELECTION":
            if digit in CROP_OPTIONS:
                crop_info = CROP_OPTIONS[digit]
                self.crop_key = digit
                self.crop_slug = crop_info["slug"]
                self.crop_tamil = crop_info["tamil"]
                logger.info(f"[VOICEBOT] Crop selected: {self.crop_slug} ({self.crop_tamil})")

                # Advance to LOCATION_SELECTION
                self.state = "LOCATION_SELECTION"
                self.crop_attempt = 1
                self.location_attempt = 1
                logger.info("[VOICEBOT] State: LOCATION_SELECTION")

                # Speak confirmation and location menu
                confirmation = (
                    f"சரி. நீங்கள் {self.crop_tamil} தேர்வு செய்துள்ளீர்கள். "
                    f"இப்போது உங்கள் இருப்பிடத்தை தேர்வு செய்யவும். "
                    f"{PROMPTS['LOCATION_MENU']}"
                )
                await self._play_and_wait(confirmation, "LOCATION_SELECTION", 1)

            else:
                # Invalid crop digit (0, *, #, etc.)
                logger.info(f"[DTMF] Invalid crop digit: '{digit}' (attempt {self.crop_attempt}/3)")
                if self.crop_attempt < 3:
                    self.crop_attempt += 1
                    msg = f"{PROMPTS['INVALID_INPUT']} {PROMPTS['CROP_MENU']}"
                    await self._play_and_wait(msg, "CROP_SELECTION", self.crop_attempt)
                else:
                    self.crop_attempt = 1
                    msg = f"{PROMPTS['MAX_RETRIES']} {PROMPTS['CROP_MENU']}"
                    await self._play_and_wait(msg, "CROP_SELECTION", 1)

        elif self.state == "LOCATION_SELECTION":
            if digit in LOCATION_OPTIONS:
                loc_info = LOCATION_OPTIONS[digit]
                self.location_key = digit
                self.location_name = loc_info["name"]
                self.location_tamil = loc_info["tamil"]
                logger.info(f"[VOICEBOT] Location selected: {self.location_name} ({self.location_tamil})")

                # Advance to SEARCHING
                self.state = "SEARCHING"
                logger.info("[VOICEBOT] State: SEARCHING")

                # Speak searching transition prompt
                search_notice = "சரி. உங்கள் இருப்பிடம் தேர்வு செய்யப்பட்டது. அருகிலுள்ள விற்பனையாளரை தேடுகிறோம். தயவுசெய்து காத்திருக்கவும்."
                await self.speak_text(search_notice)

                # Execute matching
                await self.execute_retailer_matching(loc_info["fallback_phone"])

            else:
                # Invalid location digit (0, *, #, etc.)
                logger.info(f"[DTMF] Invalid location digit: '{digit}' (attempt {self.location_attempt}/3)")
                if self.location_attempt < 3:
                    self.location_attempt += 1
                    msg = f"{PROMPTS['INVALID_INPUT']} {PROMPTS['LOCATION_MENU']}"
                    await self._play_and_wait(msg, "LOCATION_SELECTION", self.location_attempt)
                else:
                    self.state = "CROP_SELECTION"
                    self.crop_attempt = 1
                    self.location_attempt = 1
                    msg = f"{PROMPTS['MAX_RETRIES']} {PROMPTS['CROP_MENU']}"
                    await self._play_and_wait(msg, "CROP_SELECTION", 1)

    async def execute_retailer_matching(self, fallback_phone: str):
        """
        Executes PostGIS nearby search with multi-match support and ranking.
        Announces matching retailers as Shop 1, Shop 2, etc., and reads phone numbers digit-by-digit.
        Handles no matches and safety fallback cleanly without connecting calls to retailers.
        """
        logger.info(f"[POSTGIS] Searching nearby retailers for crop='{self.crop_slug}' at '{self.location_name}'...")

        matches = []
        db_error = False

        try:
            async with AsyncSessionLocal() as db:
                matches = await find_nearest_retailers(
                    db=db,
                    crop=self.crop_slug,
                    location_text=self.location_name,
                    radius_km=35.0,
                    limit=3
                )
                logger.info(f"[POSTGIS] Found {len(matches)} matches for crop='{self.crop_slug}' at '{self.location_name}'")

                # If matches found, log inquiry with primary match
                if matches:
                    primary_r, primary_dist = matches[0]
                    inquiry = InquiryLog(
                        farmer_phone=self.caller_phone or "Exotel_Caller",
                        crop_inquired=self.crop_slug,
                        location_spoken=self.location_name,
                        matched_retailer_id=primary_r.id,
                        distance_km=primary_dist,
                        status=InquiryStatus.PENDING,
                        call_sid=self.call_sid
                    )
                    db.add(inquiry)
                    await db.commit()
                    logger.info("[DATABASE] InquiryLog saved with matched retailer.")
                else:
                    # Log as no response if DB query returned 0 matches
                    inquiry = InquiryLog(
                        farmer_phone=self.caller_phone or "Exotel_Caller",
                        crop_inquired=self.crop_slug,
                        location_spoken=self.location_name,
                        matched_retailer_id=None,
                        distance_km=None,
                        status=InquiryStatus.NO_RESPONSE,
                        call_sid=self.call_sid
                    )
                    db.add(inquiry)
                    await db.commit()
                    logger.info("[DATABASE] InquiryLog saved as NO_RESPONSE (no matches).")

        except Exception as err:
            logger.error(f"[DATABASE ERROR]: {err}")
            db_error = True

        # Safety fallback ONLY if database threw an unexpected error/unreachable
        if db_error and not matches:
            fb = DEMO_RETAILER_FALLBACKS.get(fallback_phone, DEMO_RETAILER_FALLBACKS["9865741275"])
            mock_r = Retailer(
                business_name=fb["name"],
                location_name=fb["location"],
                phone_number=fb["phone"]
            )
            matches = [(mock_r, 2.0)]
            logger.info(f"[FALLBACK] Database unavailable, using demo fallback: {fb['name']}")

        # Case 1: Matching retailers found
        if matches:
            self.state = "RESULT"
            primary_r, primary_dist = matches[0]
            self._matched_details = {
                "farmer_phone": self.caller_phone or "Exotel_Caller",
                "crop": self.crop_tamil or self.crop_slug,
                "location": self.location_tamil or self.location_name,
                "retailer_name": primary_r.business_name,
                "retailer_location": primary_r.location_name or self.location_tamil,
                "retailer_phone": primary_r.phone_number,
                "distance_km": primary_dist
            }

            intro_text = (
                f"உங்களுக்கு அருகில் {len(matches)} வாங்குபவர்கள் கிடைத்துள்ளனர்."
                if len(matches) > 1
                else "உங்களுக்கு அருகிலுள்ள வாங்குபவர் கிடைத்துள்ளார்."
            )
            await self.speak_text(intro_text)

            # Announce each retailer as "Shop 1" / "கடை 1", "Shop 2" / "கடை 2", etc.
            for idx, (r, dist) in enumerate(matches):
                shop_num = idx + 1
                shop_word = TAMIL_DIGIT_WORDS.get(str(shop_num), str(shop_num))
                shop_announcement = (
                    f"Shop {shop_num}. கடை {shop_word}: {r.business_name}. "
                    f"இருப்பிடம்: {r.location_name or self.location_tamil}. "
                    f"தொலைபேசி எண்:"
                )
                await self.speak_text(shop_announcement)
                await self.speak_phone_number(r.phone_number, pause_ms=500)
                await asyncio.sleep(0.4)

            # Closing prompt
            outro_text = (
                "இந்த விவரங்கள் உங்கள் தொலைபேசிக்கு குறுஞ்செய்தியாகவும் அனுப்பப்பட்டுள்ளது. "
                "உழவு சேவையை பயன்படுத்தியதற்கு நன்றி."
            )
            await self.speak_text(outro_text)

            self.state = "END"
            logger.info("[VOICEBOT] State: END | Call flow complete.")
            self._dispatch_match_sms_background()
            await asyncio.sleep(1.5)

        # Case 2: No matching retailers found
        else:
            self.state = "NO_MATCH"
            logger.info(f"[VOICEBOT] State: NO_MATCH | No matching retailers for crop '{self.crop_slug}' at '{self.location_name}'")

            no_match_text = (
                "மன்னிக்கவும், உங்கள் பகுதியில் இந்த விளைபயிருக்கு தற்போது செயலில் உள்ள வாங்குபவர்கள் யாரும் கிடைக்கவில்லை. "
                "தயவுசெய்து சிறிது நேரம் கழித்து மீண்டும் முயற்சிக்கவும். உழவு நன்றி!"
            )
            await self.speak_text(no_match_text)

            self.state = "END"
            logger.info("[VOICEBOT] State: END | No match call flow complete.")
            await asyncio.sleep(1.5)

    async def run(self):
        """Main WebSocket loop handling Exotel Voicebot events."""
        logger.info("[VOICEBOT] New Exotel WebSocket connection accepted.")
        try:
            while True:
                msg_text = await self.ws.receive_text()
                try:
                    data = json.loads(msg_text)
                except Exception:
                    continue

                event = data.get("event")

                if event == "connected":
                    logger.info("[VOICEBOT] Event: 'connected'")

                elif event == "start":
                    start_data = data.get("start", {})
                    self.stream_sid = (
                        data.get("stream_sid")
                        or data.get("streamSid")
                        or start_data.get("stream_sid")
                        or start_data.get("streamSid", "")
                    )
                    self.call_sid = start_data.get("callSid") or start_data.get("call_sid", "")
                    self.caller_phone = (
                        start_data.get("from")
                        or start_data.get("customField")
                        or start_data.get("caller_id", "")
                    )
                    logger.info(
                        f"[VOICEBOT] Event: 'start' | stream_sid={self.stream_sid}, "
                        f"callSid={self.call_sid}, caller={self.caller_phone}"
                    )

                    # Start Call Flow: Welcome -> Crop Menu
                    self.state = "CROP_SELECTION"
                    self.crop_attempt = 1
                    logger.info("[VOICEBOT] State: CROP_SELECTION")
                    asyncio.create_task(
                        self._play_and_wait(PROMPTS["CROP_MENU"], "CROP_SELECTION", 1)
                    )

                elif event == "dtmf":
                    dtmf_info = data.get("dtmf", {})
                    digit = dtmf_info.get("digit", "")
                    if digit:
                        asyncio.create_task(self.handle_dtmf(str(digit)))

                elif event == "clear":
                    logger.debug("[VOICEBOT] Event: 'clear'")

                elif event == "stop":
                    logger.info(f"[VOICEBOT] Event: 'stop' for stream_sid={self.stream_sid}")
                    self._cancel_current_playback()
                    self._cancel_dtmf_timer()
                    break

        except WebSocketDisconnect:
            logger.info(f"[VOICEBOT] WebSocket disconnected by Exotel/Caller (stream_sid={self.stream_sid})")
            self._cancel_current_playback()
            self._cancel_dtmf_timer()
        except Exception as e:
            logger.error(f"[VOICEBOT ERROR]: {e}")
            self._cancel_current_playback()
            self._cancel_dtmf_timer()
        finally:
            # Ensure SMS is dispatched if match was reached before disconnect
            self._dispatch_match_sms_background()
