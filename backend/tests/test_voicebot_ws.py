import json
import base64
from fastapi.testclient import TestClient
from app.main import app

def test_exotel_voicebot_s16le_pcm():
    client = TestClient(app)
    with client.websocket_connect("/voice/exotel/ws") as websocket:
        # 1. Send connected event
        websocket.send_text(json.dumps({"event": "connected", "protocol": "Call", "version": "1.0.0"}))

        # 2. Send start event
        websocket.send_text(json.dumps({
            "event": "start",
            "stream_sid": "stream_exo_live_s16le",
            "start": {
                "stream_sid": "stream_exo_live_s16le",
                "callSid": "call_exo_live_001",
                "from": "+919876543210"
            }
        }))

        # 3. Receive initial prompt
        media_chunks = []
        while True:
            try:
                msg = websocket.receive_text()
                data = json.loads(msg)
                if data.get("event") == "media":
                    media = data.get("media", {})
                    payload_b64 = media.get("payload", "")
                    raw_audio = base64.b64decode(payload_b64)

                    # VERIFY REQUIREMENTS:
                    # Must contain stream_sid
                    assert "stream_sid" in data, "Must contain stream_sid in media event"
                    assert data["stream_sid"] == "stream_exo_live_s16le"

                    # Must be at least 3200 bytes
                    assert len(raw_audio) >= 3200, f"Chunk size {len(raw_audio)} must be >= 3200 bytes"

                    # Must be a multiple of 320 bytes
                    assert len(raw_audio) % 320 == 0, f"Chunk size {len(raw_audio)} must be a multiple of 320"

                    # Must NOT have WAV header (does NOT start with 'RIFF')
                    assert not raw_audio.startswith(b"RIFF"), "Media payload must be raw PCM without WAV headers"

                    media_chunks.append(raw_audio)
                    if len(media_chunks) >= 3:
                        break
            except Exception as e:
                break

        assert len(media_chunks) >= 3, "Bot must stream s16le PCM media chunks"
        print(f"VERIFIED: Received {len(media_chunks)} valid s16le PCM chunks! (Each {len(media_chunks[0])} bytes)")

        # 4. Send DTMF 1 for crop (Tomato)
        websocket.send_text(json.dumps({
            "event": "dtmf",
            "stream_sid": "stream_exo_live_s16le",
            "dtmf": {"digit": "1"}
        }))

        # 5. Receive location question audio
        loc_chunks = 0
        while True:
            try:
                msg = websocket.receive_text()
                data = json.loads(msg)
                if data.get("event") == "media":
                    raw = base64.b64decode(data["media"]["payload"])
                    assert len(raw) >= 3200
                    assert len(raw) % 320 == 0
                    loc_chunks += 1
                    if loc_chunks >= 3:
                        break
            except Exception:
                break

        assert loc_chunks >= 3, "Bot must stream location question in s16le PCM"
        print(f"VERIFIED: Location question received {loc_chunks} s16le PCM chunks.")

        # 6. Send DTMF 1 for location (Madurantakam)
        websocket.send_text(json.dumps({
            "event": "dtmf",
            "stream_sid": "stream_exo_live_s16le",
            "dtmf": {"digit": "1"}
        }))

        # 7. Receive matching result audio
        match_chunks = 0
        while True:
            try:
                msg = websocket.receive_text()
                data = json.loads(msg)
                if data.get("event") == "media":
                    raw = base64.b64decode(data["media"]["payload"])
                    assert len(raw) >= 3200
                    assert len(raw) % 320 == 0
                    match_chunks += 1
                    if match_chunks >= 3:
                        break
            except Exception:
                break

        assert match_chunks >= 3, "Bot must stream matching result in s16le PCM"
        print(f"VERIFIED: Matching result received {match_chunks} s16le PCM chunks.")

        # 8. Send stop event
        websocket.send_text(json.dumps({
            "event": "stop",
            "stream_sid": "stream_exo_live_s16le"
        }))

        print("\nALL EXOTEL S16LE PCM VOICEBOT REQUIREMENTS FULLY VERIFIED!")

if __name__ == "__main__":
    test_exotel_voicebot_s16le_pcm()
