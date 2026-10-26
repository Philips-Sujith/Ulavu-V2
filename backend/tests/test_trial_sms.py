import sys
import logging
from app.main import app
from app.config import settings
from app.sms import send_match_sms, EXOTEL_PREDEFINED_TRIAL_MSG, send_exotel_sms

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_trial_sms")

def test_1_import_startup():
    print("\n--- TEST 1: Import / Startup Check ---")
    assert app is not None
    print("PASS: Application and SMS modules loaded successfully.")

def test_2_real_exotel_trial_sms():
    print("\n--- TEST 2: Real Exotel Trial SMS to DEMO_RETAILER_SMS_PHONE ---")
    target_phone = settings.DEMO_RETAILER_SMS_PHONE.strip()
    print(f"Target Verified Phone (from .env): {target_phone}")
    print(f"Exotel Account SID: {settings.EXOTEL_ACCOUNT_SID}")
    print(f"Predefined Message: \"{EXOTEL_PREDEFINED_TRIAL_MSG}\"")

    # Send ONE demo match SMS via Exotel trial
    result = send_match_sms(
        farmer_phone="caller_mobile",
        crop="tomato",
        location_spoken="மதுராந்தகம்",
        business_name="முருகன் காய்கறி விற்பனை",
        retailer_location="மதுராந்தகம்",
        retailer_phone="9865741275",
        distance_km=2.1
    )
    print("\nReal Exotel SMS Result:", result)
    return result

if __name__ == "__main__":
    test_1_import_startup()
    test_2_real_exotel_trial_sms()
