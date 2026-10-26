import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app

async def run_api_tests():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Health & Root checks
        res = await client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["service"] == "ULAVU (உழவு)"
        assert data["voice_webhook_exotel"] == "/voice/exotel"
        print("Root endpoint verified.")

        res = await client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "healthy"}
        print("Health check endpoint verified.")

        # 2. Exotel Passthru GET webhook
        exotel_params = {
            "CallSid": "exo_call_998877",
            "CallFrom": "+919840123456",
            "CallTo": "08088919888",
            "Direction": "inbound",
            "CallType": "trans",
            "DialWhomNumber": "08088919888",
            "StartTime": "2026-09-15 22:00:00",
            "EndTime": "2026-09-15 22:01:00",
            "digits": "1",
            "customfield": "trial_test"
        }
        res = await client.get("/voice/exotel", params=exotel_params)
        assert res.status_code == 200
        assert res.text == "OK"
        print("Exotel Passthru GET /voice/exotel endpoint verified.")

        # 3. Exotel IVR Keypad Flow via Passthru POST
        test_call_sid = "exo_test_keypad_api_001"
        # Step 1: Caller enters crop (digit 2 = tomato)
        res = await client.post(
            "/voice/exotel",
            params={"CallSid": test_call_sid, "From": "+919876543210", "digits": "2"}
        )
        assert res.status_code == 200
        assert res.text == "OK"

        # Verify session has crop = tomato
        res = await client.get(f"/voice/sessions/{test_call_sid}")
        assert res.status_code == 200
        sess_data = res.json()
        assert sess_data["found"] is True
        assert sess_data["crop"] == "tomato"
        print("Exotel IVR crop selection step verified.")

        # Step 2: Caller enters location (digit 1 = Madurantakam)
        res = await client.post(
            "/voice/exotel",
            params={"CallSid": test_call_sid, "From": "+919876543210", "digits": "1"}
        )
        assert res.status_code == 200
        assert res.text == "OK"

        # Verify session has location and matches
        res = await client.get(f"/voice/sessions/{test_call_sid}")
        assert res.status_code == 200
        sess_data = res.json()
        assert sess_data["location"] == "Madurantakam"
        print("Exotel IVR location selection & matching step verified.")

        # 4. Portal REST APIs
        res = await client.get("/api/stats")
        assert res.status_code == 200
        stats = res.json()
        assert "total_retailers" in stats
        assert "active_retailer_count" in stats
        print("Portal /api/stats endpoint verified.")

        res = await client.get("/api/retailers")
        assert res.status_code == 200
        retailers = res.json()
        assert isinstance(retailers, list)
        print(f"Portal /api/retailers endpoint verified ({len(retailers)} retailers).")

        res = await client.get("/api/inquiries")
        assert res.status_code == 200
        inquiries = res.json()
        assert isinstance(inquiries, list)
        print(f"Portal /api/inquiries endpoint verified ({len(inquiries)} inquiries).")

if __name__ == "__main__":
    asyncio.run(run_api_tests())
    print("\nALL API TESTS PASSED SUCCESSFULLY!")
