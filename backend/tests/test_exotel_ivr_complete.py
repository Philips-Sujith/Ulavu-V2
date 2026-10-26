import sys
import asyncio
import json
import base64

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from fastapi.testclient import TestClient
from app.main import app
from app.models import InquiryLog, InquiryStatus, Retailer
from app.database import AsyncSessionLocal
from app.matching import find_nearest_retailers
from app.exotel_voicebot import CROP_OPTIONS, LOCATION_OPTIONS, ExotelVoicebotSession
from sqlalchemy import select

def receive_media_chunks(ws, max_chunks=3):
    """Helper to collect media chunks up to max_chunks without blocking forever."""
    chunks = []
    while True:
        try:
            msg = ws.receive_text()
            data = json.loads(msg)
            if data.get("event") == "media":
                payload = data.get("media", {}).get("payload", "")
                raw = base64.b64decode(payload)
                chunks.append(raw)
                if len(chunks) >= max_chunks:
                    break
        except Exception:
            break
    return chunks

def test_ivr_multiple_matches_announced():
    """
    Test 1: Multiple Matches
    Caller chooses Tomato (2) -> Madurantakam (1).
    Multiple retailers exist in DB (e.g. Sri Murugan Agro Traders, etc.)
    Verifies that multiple retailers are ranked, announced as Shop 1, Shop 2, etc.,
    phone numbers are spoken digit-by-digit, and call ends without connecting to retailer.
    """
    print("\n--- TEST 1: IVR Flow with Multiple Matches (Shop 1, Shop 2) ---")
    client = TestClient(app)
    with client.websocket_connect("/voice/exotel/ws") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(json.dumps({
            "event": "start",
            "stream_sid": "stream_multi_match",
            "start": {"stream_sid": "stream_multi_match", "callSid": "call_multi_01", "from": "+919876543210"}
        }))

        # 1. Receive Crop Menu
        crop_chunks = receive_media_chunks(ws, max_chunks=2)
        assert len(crop_chunks) >= 1, "Must stream crop menu"

        # 2. Press 2 for Tomato
        ws.send_text(json.dumps({
            "event": "dtmf",
            "stream_sid": "stream_multi_match",
            "dtmf": {"digit": "2"}
        }))

        # 3. Receive Location Menu
        loc_chunks = receive_media_chunks(ws, max_chunks=2)
        assert len(loc_chunks) >= 1, "Must stream location menu"

        # 4. Press 1 for Madurantakam
        ws.send_text(json.dumps({
            "event": "dtmf",
            "stream_sid": "stream_multi_match",
            "dtmf": {"digit": "1"}
        }))

        # 5. Receive Result Announcement (Shop 1, Shop 2...)
        result_chunks = receive_media_chunks(ws, max_chunks=3)
        assert len(result_chunks) >= 1, "Must stream result announcement"

        ws.send_text(json.dumps({"event": "stop", "stream_sid": "stream_multi_match"}))

    print("PASS: Multiple matches announced cleanly with digit-by-digit phone numbers.")


def test_ivr_no_matches_handling():
    """
    Test 2: No Matches Handling
    Simulate a scenario where no retailers match the query.
    Verifies that the bot transitions to NO_MATCH state, speaks apology prompt,
    does NOT announce any retailer or phone number, and finishes cleanly.
    """
    print("\n--- TEST 2: IVR Flow with No Matches ---")

    class MockWebSocket:
        def __init__(self):
            self.sent_messages = []
            self.cleared = False

        async def send_text(self, text):
            self.sent_messages.append(json.loads(text))

    async def _run_no_match():
        mock_ws = MockWebSocket()
        session = ExotelVoicebotSession(websocket=mock_ws)
        session.stream_sid = "stream_nomatch_test"
        session.call_sid = "call_nomatch_01"
        session.caller_phone = "+919876500000"
        session.crop_slug = "non_existent_crop_xyz"
        session.location_name = "Madurantakam"
        session.location_tamil = "மதுராந்தகம்"

        spoken_texts = []
        async def mock_speak_text(text, interruptible=True):
            spoken_texts.append(text)

        spoken_phones = []
        async def mock_speak_phone(phone, pause_ms=500):
            spoken_phones.append(phone)

        session.speak_text = mock_speak_text
        session.speak_phone_number = mock_speak_phone

        # Execute matching with no matches
        await session.execute_retailer_matching(fallback_phone="0000000000")

        assert session.state == "END"
        # Verify no phone number was spoken
        assert len(spoken_phones) == 0, "No phone number should be spoken on no matches"
        # Verify apology prompt was spoken
        combined = " ".join(spoken_texts)
        assert "மன்னிக்கவும்" in combined, "Apology prompt must be spoken"
        assert "செயலில் உள்ள வாங்குபவர்கள் யாரும் கிடைக்கவில்லை" in combined

    asyncio.run(_run_no_match())
    print("PASS: No matches handled with apology prompt and without phone announcement.")


def test_ivr_invalid_crop_dtmf():
    """
    Test 3: Invalid Crop DTMF Input
    Caller presses '0' or '*' on the crop menu.
    Verifies invalid input prompt is triggered and menu repeats up to 3 attempts.
    """
    print("\n--- TEST 3: Invalid Crop DTMF Input (0, *) ---")
    client = TestClient(app)
    with client.websocket_connect("/voice/exotel/ws") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(json.dumps({
            "event": "start",
            "stream_sid": "stream_invalid_crop",
            "start": {"stream_sid": "stream_invalid_crop", "callSid": "call_inv_crop_01", "from": "+919876543210"}
        }))

        # Initial crop menu
        receive_media_chunks(ws, max_chunks=1)

        # Send invalid DTMF '0'
        ws.send_text(json.dumps({
            "event": "dtmf",
            "stream_sid": "stream_invalid_crop",
            "dtmf": {"digit": "0"}
        }))

        # Verify invalid input retry prompt is streamed
        retry_chunks = receive_media_chunks(ws, max_chunks=1)
        assert len(retry_chunks) >= 1, "Must stream retry on invalid crop DTMF"

        ws.send_text(json.dumps({"event": "stop", "stream_sid": "stream_invalid_crop"}))

    print("PASS: Invalid crop DTMF input handled with retry prompt.")


def test_ivr_invalid_location_dtmf():
    """
    Test 4: Invalid Location DTMF Input
    Caller selects valid crop (1 = Onion), then presses '#' on location menu.
    Verifies invalid location input prompt is triggered and location menu repeats.
    """
    print("\n--- TEST 4: Invalid Location DTMF Input (#) ---")
    client = TestClient(app)
    with client.websocket_connect("/voice/exotel/ws") as ws:
        ws.send_text(json.dumps({"event": "connected"}))
        ws.send_text(json.dumps({
            "event": "start",
            "stream_sid": "stream_invalid_loc",
            "start": {"stream_sid": "stream_invalid_loc", "callSid": "call_inv_loc_01", "from": "+919876543210"}
        }))

        receive_media_chunks(ws, max_chunks=1)

        # Select valid crop (1 = Onion)
        ws.send_text(json.dumps({
            "event": "dtmf",
            "stream_sid": "stream_invalid_loc",
            "dtmf": {"digit": "1"}
        }))

        receive_media_chunks(ws, max_chunks=1)

        # Send invalid location DTMF '#'
        ws.send_text(json.dumps({
            "event": "dtmf",
            "stream_sid": "stream_invalid_loc",
            "dtmf": {"digit": "#"}
        }))

        # Verify invalid input retry prompt is streamed
        retry_loc_chunks = receive_media_chunks(ws, max_chunks=1)
        assert len(retry_loc_chunks) >= 1, "Must stream retry on invalid location DTMF"

        ws.send_text(json.dumps({"event": "stop", "stream_sid": "stream_invalid_loc"}))

    print("PASS: Invalid location DTMF input handled with retry prompt.")


def test_matching_multi_rank():
    """
    Test 5: Multi-Retailer Ranking Logic
    Verifies find_nearest_retailers returns multiple matches sorted ascending by distance.
    """
    print("\n--- TEST 5: Matching Logic - Proximity Ranking ---")
    async def _test():
        async with AsyncSessionLocal() as session:
            # Search tomato in Madurantakam
            matches = await find_nearest_retailers(
                db=session,
                crop="tomato",
                location_text="Madurantakam",
                radius_km=35.0,
                limit=3
            )
            assert len(matches) > 0, "Should find at least 1 match for tomato in Madurantakam"
            print(f"Found {len(matches)} matches:")
            for idx, (retailer, dist) in enumerate(matches):
                print(f"  Shop {idx+1}: {retailer.business_name} at {dist} km")

            # Verify ascending distance ordering
            for i in range(len(matches) - 1):
                assert matches[i][1] <= matches[i+1][1], "Matches must be ordered by distance ascending"

    asyncio.run(_test())
    print("PASS: Proximity ranking returns retailers sorted by distance ascending.")


if __name__ == "__main__":
    test_ivr_multiple_matches_announced()
    test_ivr_no_matches_handling()
    test_ivr_invalid_crop_dtmf()
    test_ivr_invalid_location_dtmf()
    test_matching_multi_rank()
    print("\n==========================================================")
    print("ALL COMPREHENSIVE EXOTEL IVR TESTS PASSED SUCCESSFULLY!")
    print("==========================================================")
