import io
import asyncio
import logging
from typing import Dict
import edge_tts
import miniaudio
from gtts import gTTS
import speech_recognition as sr

logger = logging.getLogger("ulavu.audio")

# In-memory cache for synthesized raw s16le PCM audio to ensure zero latency
_AUDIO_CACHE: Dict[str, bytes] = {}

# Tamil neural voice for Microsoft Edge TTS
TAMIL_VOICE = "ta-IN-PallaviNeural"

recognizer = sr.Recognizer()
recognizer.energy_threshold = 300
recognizer.dynamic_energy_threshold = True

async def text_to_s16le_pcm(text: str) -> bytes:
    """
    Converts Tamil text to RAW 16-bit signed Linear PCM (s16le), 8000 Hz, mono.
    NO WAV headers. Output length is padded to be a multiple of 320 bytes.
    Uses free Edge TTS (ta-IN-PallaviNeural) with gTTS fallback.
    Caches results in-memory.
    """
    clean_text = text.strip()
    if clean_text in _AUDIO_CACHE:
        return _AUDIO_CACHE[clean_text]

    pcm_bytes = b""

    # 1. Try Edge TTS
    try:
        comm = edge_tts.Communicate(clean_text, voice=TAMIL_VOICE)
        raw_audio = b""
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                raw_audio += chunk["data"]

        if raw_audio:
            # Decode directly to raw 16-bit signed mono PCM at 8000 Hz
            decoded = miniaudio.decode(
                raw_audio,
                nchannels=1,
                sample_rate=8000,
                output_format=miniaudio.SampleFormat.SIGNED16
            )
            pcm_bytes = decoded.samples.tobytes()
            logger.info(
                f"[TTS EdgeTTS SUCCESS] Generated {len(pcm_bytes)} bytes of s16le PCM "
                f"({len(pcm_bytes)/16000:.2f}s) for '{clean_text[:40]}...'"
            )
    except Exception as e:
        logger.warning(f"EdgeTTS failed ({e}), falling back to gTTS...")

    # 2. Fallback to gTTS (Google Translate TTS) if needed
    if not pcm_bytes:
        try:
            def _generate_gtts():
                tts = gTTS(text=clean_text, lang="ta")
                mp3_fp = io.BytesIO()
                tts.write_to_fp(mp3_fp)
                return mp3_fp.getvalue()

            mp3_data = await asyncio.to_thread(_generate_gtts)
            decoded = miniaudio.decode(
                mp3_data,
                nchannels=1,
                sample_rate=8000,
                output_format=miniaudio.SampleFormat.SIGNED16
            )
            pcm_bytes = decoded.samples.tobytes()
            logger.info(
                f"[TTS gTTS SUCCESS] Generated {len(pcm_bytes)} bytes of s16le PCM "
                f"({len(pcm_bytes)/16000:.2f}s) for '{clean_text[:40]}...'"
            )
        except Exception as e:
            logger.error(f"TTS generation failed completely: {e}")
            return b""

    # Pad with silence so length is a multiple of 320 bytes
    rem = len(pcm_bytes) % 320
    if rem > 0:
        pcm_bytes += b"\x00" * (320 - rem)

    _AUDIO_CACHE[clean_text] = pcm_bytes
    return pcm_bytes

# Backward-compatibility alias
text_to_mulaw = text_to_s16le_pcm

async def pcm_to_text(pcm_bytes: bytes, language: str = "ta-IN") -> str:
    """
    Converts raw 16-bit signed Linear PCM (s16le, 8000 Hz, mono) to text
    using Google Speech Recognition (free).
    """
    # Need at least 0.4s of audio (6400 bytes at 16000 bytes/sec)
    if not pcm_bytes or len(pcm_bytes) < 6400:
        return ""

    def _recognize():
        try:
            # Wrap raw s16le PCM samples directly (sample_width=2 for 16-bit)
            audio_data = sr.AudioData(pcm_bytes, sample_rate=8000, sample_width=2)
            # Recognize in Tamil (also catches transliterated English crop names)
            text = recognizer.recognize_google(audio_data, language=language)
            return text.strip()
        except sr.UnknownValueError:
            logger.debug("Speech recognition could not understand audio")
            return ""
        except sr.RequestError as e:
            logger.error(f"Speech recognition service error: {e}")
            return ""
        except Exception as e:
            logger.error(f"Error in speech recognition: {e}")
            return ""

    return await asyncio.to_thread(_recognize)

# Backward-compatibility alias
mulaw_to_text = pcm_to_text

# Pre-defined prompt texts in natural Tamil
PROMPTS = {
    "CROP_MENU": (
        "வணக்கம்! உழவு சேவைக்கு வரவேற்கிறோம். "
        "உங்கள் காய்கறியை தேர்வு செய்யவும். "
        "வெங்காயத்திற்கு ஒன்று அழுத்தவும். "
        "தக்காளிக்கு இரண்டு அழுத்தவும். "
        "உருளைக்கிழங்கிற்கு மூன்று அழுத்தவும். "
        "கத்தரிக்காய்க்கு நான்கு அழுத்தவும். "
        "கேரட்டிற்கு ஐந்து அழுத்தவும். "
        "முட்டைக்கோஸிற்கு ஆறு அழுத்தவும். "
        "காலிஃப்ளவருக்கு ஏழு அழுத்தவும். "
        "வெண்டைக்காய்க்கு எட்டு அழுத்தவும். "
        "பச்சை மிளகாய்க்கு ஒன்பது அழுத்தவும்."
    ),
    "LOCATION_MENU": (
        "மதுராந்தகத்திற்கு ஒன்று அழுத்தவும். "
        "செங்கல்பட்டிற்கு இரண்டு அழுத்தவும். "
        "காஞ்சிபுரத்திற்கு மூன்று அழுத்தவும். "
        "திருக்கழுக்குன்றத்திற்கு நான்கு அழுத்தவும். "
        "உத்திரமேரூருக்கு ஐந்து அழுத்தவும். "
        "அச்சரப்பாக்கத்திற்கு ஆறு அழுத்தவும். "
        "செய்யூருக்கு ஏழு அழுத்தவும். "
        "ஸ்ரீபெரும்புதூருக்கு எட்டு அழுத்தவும். "
        "வாலாஜாபாத்திற்கு ஒன்பது அழுத்தவும்."
    ),
    "NO_INPUT": "உங்கள் தேர்வு கிடைக்கவில்லை. மீண்டும் முயற்சிக்கவும்.",
    "INVALID_INPUT": "தவறான தேர்வு. தயவுசெய்து மீண்டும் முயற்சிக்கவும்.",
    "MAX_RETRIES": "தேர்வு செய்ய முடியவில்லை. மீண்டும் தொடங்குகிறோம்.",
}

# Aliases for backward-compatibility
PROMPTS["GREETING_ASK_CROP"] = PROMPTS["CROP_MENU"]
PROMPTS["ASK_LOCATION"] = PROMPTS["LOCATION_MENU"]
PROMPTS["RETRY_CROP"] = PROMPTS["NO_INPUT"]
PROMPTS["RETRY_LOCATION"] = PROMPTS["NO_INPUT"]

# Tamil Digits (0 - 9)
TAMIL_DIGIT_WORDS: Dict[str, str] = {
    "0": "பூஜ்ஜியம்",
    "1": "ஒன்று",
    "2": "இரண்டு",
    "3": "மூன்று",
    "4": "நான்கு",
    "5": "ஐந்து",
    "6": "ஆறு",
    "7": "ஏழு",
    "8": "எட்டு",
    "9": "ஒன்பது",
}

# Cache for individual digit s16le PCM bytes
_DIGIT_CACHE: Dict[str, bytes] = {}

async def precache_digits():
    """Synthesizes and caches all 10 individual Tamil digits."""
    for digit, word in TAMIL_DIGIT_WORDS.items():
        if digit not in _DIGIT_CACHE:
            pcm = await text_to_s16le_pcm(word)
            _DIGIT_CACHE[digit] = pcm
    logger.info("Pre-cached all 10 Tamil digits (0-9) in s16le PCM.")

async def phone_number_to_slow_tamil_pcm(phone: str, pause_ms: int = 500) -> bytes:
    """
    Extracts digits from phone number, maps to Tamil words,
    and returns concatenated s16le PCM with 400-600ms pauses between digits.
    Never speaks the phone number as one continuous number.
    Substantially slower than normal conversational TTS.
    """
    # Extract only digits
    digits_only = [d for d in str(phone) if d.isdigit()]
    if not digits_only:
        return b""

    # Focus on last 10 digits for standard phone numbers
    read_digits = digits_only[-10:] if len(digits_only) >= 10 else digits_only

    # Pause audio (8000 Hz, 16-bit mono = 16000 bytes/sec)
    pause_samples = int((pause_ms / 1000.0) * 16000)
    # Ensure pause is a multiple of 320 bytes
    pause_samples = (pause_samples // 320) * 320
    silence_pause = b"\x00" * pause_samples

    result_pcm = bytearray()

    for idx, d in enumerate(read_digits):
        if d in _DIGIT_CACHE:
            digit_pcm = _DIGIT_CACHE[d]
        else:
            word = TAMIL_DIGIT_WORDS.get(d, "பூஜ்ஜியம்")
            digit_pcm = await text_to_s16le_pcm(word)
            _DIGIT_CACHE[d] = digit_pcm

        result_pcm.extend(digit_pcm)

        # Insert pause between digits (not after the final digit)
        if idx < len(read_digits) - 1:
            result_pcm.extend(silence_pause)

    # Pad total to multiple of 320 bytes
    rem = len(result_pcm) % 320
    if rem > 0:
        result_pcm.extend(b"\x00" * (320 - rem))

    return bytes(result_pcm)

async def precache_prompts():
    """Warms up the TTS cache on server startup for instant audio response."""
    logger.info("Pre-caching Tamil voice prompts (s16le raw PCM) for Exotel Voicebot...")
    for key, text in PROMPTS.items():
        try:
            await text_to_s16le_pcm(text)
        except Exception as e:
            logger.warning(f"Could not pre-cache prompt '{key}': {e}")
    await precache_digits()
    logger.info(f"Pre-cached {len(_AUDIO_CACHE)} voice prompts in s16le PCM.")
