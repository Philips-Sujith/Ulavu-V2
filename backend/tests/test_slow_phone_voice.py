import asyncio
import logging
from app.audio_service import (
    TAMIL_DIGIT_WORDS,
    phone_number_to_slow_tamil_pcm,
    text_to_s16le_pcm,
    precache_digits,
    _DIGIT_CACHE,
)
from app.exotel_voicebot import ExotelVoicebotSession, DEMO_RETAILER_FALLBACKS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test")

async def test_tamil_digit_mapping():
    """Verify all 10 digits 0-9 are mapped to correct Tamil words."""
    assert TAMIL_DIGIT_WORDS["0"] == "பூஜ்ஜியம்"
    assert TAMIL_DIGIT_WORDS["1"] == "ஒன்று"
    assert TAMIL_DIGIT_WORDS["2"] == "இரண்டு"
    assert TAMIL_DIGIT_WORDS["3"] == "மூன்று"
    assert TAMIL_DIGIT_WORDS["4"] == "நான்கு"
    assert TAMIL_DIGIT_WORDS["5"] == "ஐந்து"
    assert TAMIL_DIGIT_WORDS["6"] == "ஆறு"
    assert TAMIL_DIGIT_WORDS["7"] == "ஏழு"
    assert TAMIL_DIGIT_WORDS["8"] == "எட்டு"
    assert TAMIL_DIGIT_WORDS["9"] == "ஒன்பது"
    print("PASS: test_tamil_digit_mapping")

async def test_slow_phone_pcm_generation():
    """
    Verify phone_number_to_slow_tamil_pcm produces valid s16le PCM,
    inserts ~500ms silence pauses between digits, and is significantly slower
    than normal continuous conversational TTS.
    """
    demo_phone = "9865741275"
    
    # 1. Generate slow phone number PCM with 500ms pause
    slow_pcm = await phone_number_to_slow_tamil_pcm(demo_phone, pause_ms=500)
    assert len(slow_pcm) > 0, "Slow PCM should not be empty"
    assert len(slow_pcm) % 320 == 0, "PCM audio must be aligned to 320 bytes"

    slow_duration_sec = len(slow_pcm) / 16000.0
    print(f"Slow phone number duration: {slow_duration_sec:.2f} seconds")

    # 10 digits spoken with 9 pauses of ~500ms = at least 4.5s of pause alone + digit speech
    assert slow_duration_sec >= 7.0, f"Duration {slow_duration_sec}s too short for slow digit-by-digit speech"

    # 2. Compare against normal continuous speech
    normal_text = "ஒன்பது எட்டு பூஜ்ஜியம் பூஜ்ஜியம் பூஜ்ஜியம் பூஜ்ஜியம் பூஜ்ஜியம் பூஜ்ஜியம் பூஜ்ஜியம் ஒன்று"
    normal_pcm = await text_to_s16le_pcm(normal_text)
    normal_duration_sec = len(normal_pcm) / 16000.0
    print(f"Normal conversational text duration: {normal_duration_sec:.2f} seconds")

    assert slow_duration_sec > (normal_duration_sec * 1.5), (
        f"Slow phone audio ({slow_duration_sec:.2f}s) must be substantially slower "
        f"than normal continuous TTS ({normal_duration_sec:.2f}s)"
    )
    print("PASS: test_slow_phone_pcm_generation")

async def test_speak_phone_number_masked_logging():
    """Verify that speak_phone_number logs '[VOICEBOT] Speaking phone number slowly: **********' without exposing real digits."""
    log_records = []
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            log_records.append(self.format(record))
    
    handler = InterceptHandler()
    logging.getLogger("ulavu.voicebot").addHandler(handler)

    session = ExotelVoicebotSession(websocket=None)
    played_chunks = []
    async def mock_speak_pcm(pcm_bytes):
        played_chunks.append(len(pcm_bytes))
    session.speak_pcm = mock_speak_pcm

    real_phone = "9876543210"
    await session.speak_phone_number(real_phone, pause_ms=500)

    logged_text = "\n".join(log_records)
    assert "[VOICEBOT] Speaking phone number slowly: **********" in logged_text, f"Log missing expected message: {logged_text}"
    assert real_phone not in logged_text, "Real phone number must NOT be logged!"
    assert len(played_chunks) == 1
    assert played_chunks[0] > 0
    print("PASS: test_speak_phone_number_masked_logging")

async def test_demo_retailers_have_designated_demo_numbers():
    """Verify all fallback demo retailers use designated 10-digit demo numbers."""
    expected_numbers = {"9865741275", "9644157852", "9785632147", "9367821450", "9874516328"}
    for key, retailer in DEMO_RETAILER_FALLBACKS.items():
        phone = retailer["phone"]
        assert len(phone) == 10
        assert phone.isdigit()
        assert phone in expected_numbers, f"Unexpected demo number: {phone}"
    print("PASS: test_demo_retailers_have_designated_demo_numbers")

async def main():
    await test_tamil_digit_mapping()
    await test_slow_phone_pcm_generation()
    await test_speak_phone_number_masked_logging()
    await test_demo_retailers_have_designated_demo_numbers()
    print("\nALL VOICE POLISH TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(main())
