import sys
import logging
from app.config import settings

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("test_sms")

def run_test_1_imports():
    """TEST 1: Verify application imports/startup successfully."""
    print("\n--- TEST 1: Verify application imports/startup successfully ---")
    try:
        from app.main import app
        from app.sms import (
            build_farmer_sms,
            build_retailer_sms,
            send_single_sms,
            send_match_sms,
            send_exotel_sms,
            mask_phone_number
        )
        from app.exotel_voicebot import ExotelVoicebotSession
        assert app is not None
        print("PASS: Application and SMS modules imported successfully.")
        return True
    except Exception as e:
        print(f"FAIL: Application import failed: {e}")
        return False

def run_test_2_farmer_sms_construction():
    """TEST 2: Verify SMS service can construct the Farmer SMS correctly."""
    print("\n--- TEST 2: Verify SMS service can construct the Farmer SMS correctly ---")
    from app.sms import build_farmer_sms

    sms = build_farmer_sms(
        crop="tomato",
        location="மதுராந்தகம்",
        retailer_name="முருகன் காய்கறி விற்பனை",
        retailer_location="மதுராந்தகம்",
        retailer_phone="9865741275"
    )

    print(f"Constructed Farmer SMS:\n{sms}\n")

    assert "ULAVU – அருகிலுள்ள விற்பனையாளர் கண்டறியப்பட்டுள்ளார்." in sms, "Header missing"
    assert "பயிர்: தக்காளி" in sms or "பயிர்: tomato" in sms, "Crop missing"
    assert "இடம்: மதுராந்தகம்" in sms, "Farmer location missing"
    assert "விற்பனையாளர்: முருகன் காய்கறி விற்பனை" in sms, "Retailer name missing"
    assert "விற்பனையாளர் இருப்பிடம்: மதுராந்தகம்" in sms, "Retailer location missing"
    assert "தொலைபேசி: 9865741275" in sms, "Retailer phone missing"

    print("PASS: Farmer SMS correctly constructed matching requirements.")
    return True

def run_test_3_retailer_sms_construction():
    """TEST 3: Verify SMS service can construct the Retailer SMS correctly."""
    print("\n--- TEST 3: Verify SMS service can construct the Retailer SMS correctly ---")
    from app.sms import build_retailer_sms

    sms = build_retailer_sms(
        crop="tomato",
        location="மதுராந்தகம்"
    )

    print(f"Constructed Retailer SMS:\n{sms}\n")

    assert "ULAVU – புதிய விவசாயி விசாரணை." in sms, "Header missing"
    assert "பயிர்: தக்காளி" in sms or "பயிர்: tomato" in sms, "Crop missing"
    assert "விவசாயி இருப்பிடம்: மதுராந்தகம்" in sms, "Farmer location missing"

    print("PASS: Retailer SMS correctly constructed matching requirements.")
    return True

def run_test_4_real_test_sms():
    """TEST 4: Send ONE real test SMS to verified demo number, IF Exotel trial allows it."""
    print("\n--- TEST 4: Send ONE real test SMS to verified demo number ---")
    from app.sms import send_single_sms

    target_phone = settings.DEMO_RETAILER_SMS_PHONE.strip() or settings.TEST_RETAILER_PHONE.strip()
    print(f"Configured DEMO_RETAILER_SMS_PHONE: '{target_phone}'")
    print(f"Configured EXOTEL_ACCOUNT_SID: '{settings.EXOTEL_ACCOUNT_SID}'")
    print(f"Configured EXOTEL_API_KEY: '{bool(settings.EXOTEL_API_KEY)}' (set: {bool(settings.EXOTEL_API_KEY)})")

    test_body = "ULAVU Test SMS: Demo connection verified."
    result = send_single_sms(target_phone or "+918939790971", test_body)
    print(f"SMS Dispatch Result: {result}")

    if result.get("success"):
        print(f"PASS: Real test SMS sent successfully via {result.get('provider')}! SID: {result.get('sid')}")
    else:
        print(f"REPORT: SMS sending could not complete over live network: {result.get('error')}")

    return result

def run_test_5_exception_safety():
    """TEST 5: Verify SMS failure does not raise an unhandled exception."""
    print("\n--- TEST 5: Verify SMS failure does not raise an unhandled exception ---")
    from app.sms import send_match_sms

    try:
        # Pass completely invalid parameters and trigger failure
        res = send_match_sms(
            farmer_phone="",
            crop="unknown_crop",
            location_spoken="unknown_location",
            business_name="test",
            retailer_location="test",
            retailer_phone="0000000000",
            distance_km=0.0
        )
        assert isinstance(res, dict), "Must return dict result"
        print(f"Handled safely without crash. Returned result: {res}")
        print("PASS: SMS failure handled safely without raising unhandled exceptions.")
        return True
    except Exception as e:
        print(f"FAIL: Unhandled exception raised: {e}")
        return False

def main():
    t1 = run_test_1_imports()
    t2 = run_test_2_farmer_sms_construction()
    t3 = run_test_3_retailer_sms_construction()
    t4 = run_test_4_real_test_sms()
    t5 = run_test_5_exception_safety()

    print("\n==================================================")
    print("MANDATORY TEST SUMMARY")
    print(f"TEST 1 (Imports): {'PASS' if t1 else 'FAIL'}")
    print(f"TEST 2 (Farmer SMS Content): {'PASS' if t2 else 'FAIL'}")
    print(f"TEST 3 (Retailer SMS Content): {'PASS' if t3 else 'FAIL'}")
    print(f"TEST 4 (Real SMS Check): Provider={t4.get('provider')}, Success={t4.get('success')}")
    print(f"TEST 5 (Exception Safety): {'PASS' if t5 else 'FAIL'}")
    print("==================================================")

if __name__ == "__main__":
    main()
