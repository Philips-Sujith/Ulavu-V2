import logging
from typing import Optional, Dict, Any
import requests
from app.config import settings

logger = logging.getLogger("ulavu.sms")

# Official Exotel Trial Predefined SMS Template (Allowed without KYC on trial accounts to verified numbers)
EXOTEL_PREDEFINED_TRIAL_MSG = "This is a test message powered by Exotel. Report abuse to +91808891888 -Exotel"

# Tamil Crop Display Names
CROP_DISPLAY_TAMIL: Dict[str, str] = {
    "onion": "வெங்காயம்",
    "tomato": "தக்காளி",
    "potato": "உருளைக்கிழங்கு",
    "brinjal": "கத்தரிக்காய்",
    "carrot": "கேரட்",
    "cabbage": "முட்டைக்கோஸ்",
    "cauliflower": "காலிஃப்ளவர்",
    "okra": "வெண்டைக்காய்",
    "chilli": "பச்சை மிளகாய்",
}

def format_phone_number(phone: str) -> str:
    """Formats phone number into clean numeric or E.164 string."""
    if not phone:
        return ""
    clean = "".join([c for c in str(phone) if c.isdigit() or c == "+"])
    return clean

def mask_phone_number(phone: str) -> str:
    """Masks phone number for privacy logging and portal display."""
    clean = format_phone_number(phone)
    if len(clean) >= 10:
        return clean[:len(clean) - 5] + "XXXXX"
    return "**********"

def build_farmer_sms(
    crop: str,
    location: str,
    retailer_name: str,
    retailer_location: str,
    retailer_phone: str
) -> str:
    """
    Constructs the Farmer SMS in the exact required Tamil format:
    ULAVU – அருகிலுள்ள விற்பனையாளர் கண்டறியப்பட்டுள்ளார்.

    பயிர்: <crop>
    இடம்: <farmer location>
    விற்பனையாளர்: <retailer name>
    விற்பனையாளர் இருப்பிடம்: <retailer location>
    தொலைபேசி: <retailer phone>
    """
    crop_name = CROP_DISPLAY_TAMIL.get(crop.lower().strip(), crop)
    return (
        "ULAVU – அருகிலுள்ள விற்பனையாளர் கண்டறியப்பட்டுள்ளார்.\n\n"
        f"பயிர்: {crop_name}\n"
        f"இடம்: {location}\n"
        f"விற்பனையாளர்: {retailer_name}\n"
        f"விற்பனையாளர் இருப்பிடம்: {retailer_location}\n"
        f"தொலைபேசி: {retailer_phone}"
    )

def build_retailer_sms(
    crop: str,
    location: str
) -> str:
    """
    Constructs the Retailer SMS in the exact required Tamil format:
    ULAVU – புதிய விவசாயி விசாரணை.

    பயிர்: <crop>
    விவசாயி இருப்பிடம்: <farmer location>
    """
    crop_name = CROP_DISPLAY_TAMIL.get(crop.lower().strip(), crop)
    return (
        "ULAVU – புதிய விவசாயி விசாரணை.\n\n"
        f"பயிர்: {crop_name}\n"
        f"விவசாயி இருப்பிடம்: {location}"
    )

def send_exotel_sms(to_phone: str, body: Optional[str] = None) -> Dict[str, Any]:
    """
    Sends an SMS via Exotel REST API.
    For Exotel trial accounts, sends the official predefined trial message.
    Endpoint: https://api.exotel.com/v1/Accounts/{EXOTEL_ACCOUNT_SID}/Sms/send.json
    Auth: Basic Auth with EXOTEL_API_KEY and EXOTEL_API_TOKEN
    """
    account_sid = settings.EXOTEL_ACCOUNT_SID.strip()
    api_key = settings.EXOTEL_API_KEY.strip()
    api_token = settings.EXOTEL_API_TOKEN.strip()
    subdomain = settings.EXOTEL_SUBDOMAIN.strip() or "api.exotel.com"
    from_phone = settings.EXOTEL_PHONE_NUMBER.strip()

    if not (account_sid and api_key and api_token):
        logger.warning("[SMS EXOTEL] Credentials not configured in .env")
        return {
            "success": False,
            "provider": "exotel",
            "error": "EXOTEL_ACCOUNT_SID, EXOTEL_API_KEY, or EXOTEL_API_TOKEN not configured in .env"
        }

    url = f"https://{subdomain}/v1/Accounts/{account_sid}/Sms/send.json"
    
    # Destination formatting for Indian mobile numbers
    clean_to = format_phone_number(to_phone)
    if clean_to.startswith("+91"):
        dest = clean_to[3:]
    elif clean_to.startswith("91") and len(clean_to) == 12:
        dest = clean_to[2:]
    else:
        dest = clean_to

    # Use official predefined trial message for Exotel trial account
    sms_body = EXOTEL_PREDEFINED_TRIAL_MSG

    payload = {
        "From": from_phone,
        "To": dest,
        "Body": sms_body
    }

    try:
        logger.info(
            f"[SMS EXOTEL TRIAL] Dispatching predefined trial SMS to verified number {mask_phone_number(dest)} "
            f"via {url}..."
        )
        response = requests.post(url, data=payload, auth=(api_key, api_token), timeout=10.0)
        
        if response.status_code in (200, 201):
            res_data = response.json() if response.content else {}
            sms_sid = res_data.get("SMSMessage", {}).get("Sid") or "exotel_queued"
            logger.info(f"[SMS EXOTEL SUCCESS] Predefined trial SMS successfully dispatched! SID: {sms_sid}")
            return {
                "success": True,
                "provider": "exotel",
                "sid": sms_sid,
                "status_code": response.status_code,
                "body": sms_body
            }
        else:
            err_text = response.text
            logger.warning(f"[SMS EXOTEL FAILED] HTTP {response.status_code}: {err_text}")
            return {
                "success": False,
                "provider": "exotel",
                "status_code": response.status_code,
                "error": err_text
            }
    except Exception as e:
        logger.error(f"[SMS EXOTEL EXCEPTION]: {e}")
        return {"success": False, "provider": "exotel", "error": str(e)}

def send_single_sms(to_phone: str, body: Optional[str] = None) -> Dict[str, Any]:
    """
    Sends a single SMS using the current Exotel trial SMS implementation.
    Sends ONLY the official Exotel trial message:
    'This is a test message powered by Exotel. Report abuse to +91808891888 -Exotel'
    """
    if not to_phone:
        logger.warning("[SMS] Recipient phone number is empty. Skipping SMS.")
        return {"success": False, "provider": "exotel", "error": "Recipient phone number is empty"}

    try:
        return send_exotel_sms(to_phone=to_phone, body=EXOTEL_PREDEFINED_TRIAL_MSG)
    except Exception as e:
        logger.error(f"[SMS ERROR] send_single_sms exception: {e}")
        return {"success": False, "provider": "exotel", "error": str(e)}

def send_match_sms(
    farmer_phone: str,
    crop: str,
    location_spoken: str,
    business_name: str,
    retailer_location: str,
    retailer_phone: str,
    distance_km: Optional[float] = None
) -> Dict[str, Any]:
    """
    Demo SMS Dispatcher:
    1. Generates and logs the proper ULAVU Tamil messages for Farmer & Retailer.
    2. Sends ONE Exotel trial SMS (official predefined message) to DEMO_RETAILER_SMS_PHONE.
    3. Does NOT send duplicate messages.
    4. Does NOT use Twilio fallback.
    5. Fully non-blocking and exception-safe.
    """
    demo_phone = settings.DEMO_RETAILER_SMS_PHONE.strip()

    # 1. Build and log the proper internal ULAVU Tamil messages
    farmer_msg = build_farmer_sms(
        crop=crop,
        location=location_spoken,
        retailer_name=business_name,
        retailer_location=retailer_location,
        retailer_phone=retailer_phone
    )
    retailer_msg = build_retailer_sms(
        crop=crop,
        location=location_spoken
    )

    logger.info(f"[SMS DEMO NOTIFICATION] Generated Farmer SMS:\n{farmer_msg}")
    logger.info(f"[SMS DEMO NOTIFICATION] Generated Retailer SMS:\n{retailer_msg}")

    if not demo_phone:
        logger.warning("[SMS DEMO] DEMO_RETAILER_SMS_PHONE not configured in .env. Skipping dispatch.")
        return {
            "success": False,
            "provider": "exotel",
            "error": "DEMO_RETAILER_SMS_PHONE not set in .env"
        }

    # 2. Send ONE Exotel trial SMS representing the match notification
    logger.info(
        f"[SMS DEMO] Sending ONE Exotel trial SMS to verified number {mask_phone_number(demo_phone)} "
        f"representing Farmer & Retailer notification demo."
    )

    try:
        result = send_exotel_sms(demo_phone)
        return result
    except Exception as e:
        logger.error(f"[SMS ERROR] Uncaught exception during demo SMS dispatch: {e}")
        return {"success": False, "provider": "exotel", "error": str(e)}
