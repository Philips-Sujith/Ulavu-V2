import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Form, Request, Response, BackgroundTasks, Query, WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, AsyncSessionLocal
from app.models import InquiryLog, InquiryStatus
from app.matching import find_nearest_retailers, find_nearest_retailer, normalize_crop
from app.sms import send_match_sms
from app.exotel_voicebot import CROP_OPTIONS, LOCATION_OPTIONS

logger = logging.getLogger("ulavu.voice")

router = APIRouter(prefix="/voice", tags=["Voice Telephony"])

# In-memory call session cache keyed by CallSid
# Stores temporary call state (crop, farmer_phone, step, retries, matched retailers)
call_sessions: Dict[str, Dict[str, Any]] = {}


def _clean_dtmf(digits: Optional[str]) -> str:
    """Helper to strip quotes or spaces often added by Exotel applets (e.g. '\"1\"' -> '1')."""
    if not digits:
        return ""
    clean = str(digits).replace('"', '').replace("'", "").strip()
    return clean


@router.get("/exotel")
@router.post("/exotel")
@router.post("/incoming")
@router.get("/incoming")
async def exotel_passthru(
    request: Request,
    background_tasks: BackgroundTasks,
    CallSid: Optional[str] = Query(None),
    CallFrom: Optional[str] = Query(None),
    CallTo: Optional[str] = Query(None),
    Direction: Optional[str] = Query(None),
    CallType: Optional[str] = Query(None),
    DialWhomNumber: Optional[str] = Query(None),
    StartTime: Optional[str] = Query(None),
    EndTime: Optional[str] = Query(None),
    digits: Optional[str] = Query(None),
    customfield: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Exotel Inbound Call Webhook (Passthru Applet).
    Receives call metadata, caller phone, and DTMF keypad selections from Exotel IVR flow.
    Coordinates farmer crop & location selection, executes PostGIS matching, logs inquiries,
    and returns HTTP 200 OK required by Exotel Passthru.
    """
    params = dict(request.query_params)

    # Parse form data if sent via HTTP POST
    if request.method == "POST":
        try:
            form_data = await request.form()
            params.update(dict(form_data))
        except Exception:
            pass

    call_sid = CallSid or params.get("CallSid") or params.get("call_sid") or "N/A"
    call_from = CallFrom or params.get("CallFrom") or params.get("From") or "N/A"
    call_to = CallTo or params.get("CallTo") or params.get("To") or "N/A"
    direction = Direction or params.get("Direction") or "inbound"
    call_type = CallType or params.get("CallType") or "trans"
    dial_whom = DialWhomNumber or params.get("DialWhomNumber") or "N/A"
    start_time = StartTime or params.get("StartTime") or "N/A"
    end_time = EndTime or params.get("EndTime") or "N/A"
    raw_digits = digits if digits is not None else params.get("digits") or ""
    dtmf = _clean_dtmf(raw_digits)
    custom_field = customfield or params.get("customfield") or "N/A"

    logger.info(
        f"[EXOTEL PASSTHRU] CallSid={call_sid}, From={call_from}, To={call_to}, "
        f"Direction={direction}, DTMF='{dtmf}', CustomField={custom_field}"
    )

    # Maintain session state across IVR steps if CallSid is valid
    if call_sid and call_sid != "N/A":
        session = call_sessions.setdefault(call_sid, {
            "farmer_phone": call_from if call_from != "N/A" else "Exotel_Caller",
            "crop_key": None,
            "crop_slug": None,
            "location_key": None,
            "location_name": None,
            "matched_retailers": []
        })

        if call_from != "N/A" and session["farmer_phone"] == "Exotel_Caller":
            session["farmer_phone"] = call_from

        # Process keypad digit
        if dtmf:
            if not session.get("crop_slug"):
                # Caller selected crop
                if dtmf in CROP_OPTIONS:
                    crop_info = CROP_OPTIONS[dtmf]
                    session["crop_key"] = dtmf
                    session["crop_slug"] = crop_info["slug"]
                    session["crop_tamil"] = crop_info["tamil"]
                    logger.info(f"[EXOTEL PASSTHRU] Session {call_sid}: Crop set to {session['crop_slug']}")
                else:
                    logger.warning(f"[EXOTEL PASSTHRU] Session {call_sid}: Invalid crop DTMF '{dtmf}'")

            elif not session.get("location_name"):
                # Caller selected location
                if dtmf in LOCATION_OPTIONS:
                    loc_info = LOCATION_OPTIONS[dtmf]
                    session["location_key"] = dtmf
                    session["location_name"] = loc_info["name"]
                    session["location_tamil"] = loc_info["tamil"]
                    logger.info(f"[EXOTEL PASSTHRU] Session {call_sid}: Location set to {session['location_name']}")

                    # Execute matching
                    crop = session.get("crop_slug", "")
                    location = session.get("location_name", "")
                    matches = await find_nearest_retailers(
                        db=db,
                        crop=crop,
                        location_text=location,
                        radius_km=35.0,
                        limit=3
                    )
                    session["matched_retailers"] = matches
                    logger.info(f"[EXOTEL PASSTHRU] Session {call_sid}: Found {len(matches)} matches")

                    # Log inquiry
                    if matches:
                        primary_r, primary_dist = matches[0]
                        inquiry = InquiryLog(
                            farmer_phone=session["farmer_phone"],
                            crop_inquired=crop,
                            location_spoken=location,
                            matched_retailer_id=primary_r.id,
                            distance_km=primary_dist,
                            status=InquiryStatus.PENDING,
                            call_sid=call_sid
                        )
                        db.add(inquiry)
                        await db.commit()

                        # Dispatch SMS in background
                        background_tasks.add_task(
                            send_match_sms,
                            farmer_phone=session["farmer_phone"],
                            crop=crop,
                            location_spoken=location,
                            business_name=primary_r.business_name,
                            retailer_location=primary_r.location_name or location,
                            retailer_phone=primary_r.phone_number,
                            distance_km=primary_dist
                        )
                    else:
                        inquiry = InquiryLog(
                            farmer_phone=session["farmer_phone"],
                            crop_inquired=crop,
                            location_spoken=location,
                            matched_retailer_id=None,
                            distance_km=None,
                            status=InquiryStatus.NO_RESPONSE,
                            call_sid=call_sid
                        )
                        db.add(inquiry)
                        await db.commit()
                else:
                    logger.warning(f"[EXOTEL PASSTHRU] Session {call_sid}: Invalid location DTMF '{dtmf}'")

    # Exotel Passthru expects HTTP 200 with text/plain "OK"
    return Response(content="OK", status_code=200, media_type="text/plain")


@router.post("/crop-captured")
async def crop_captured_compat():
    """Compatibility endpoint for any legacy webhook references."""
    return Response(content="OK", status_code=200, media_type="text/plain")


@router.get("/sessions/{call_sid}")
async def get_call_session(call_sid: str):
    """Debug / inspection endpoint for active IVR call sessions."""
    session = call_sessions.get(call_sid)
    if not session:
        return {"found": False, "call_sid": call_sid}
    return {
        "found": True,
        "call_sid": call_sid,
        "farmer_phone": session.get("farmer_phone"),
        "crop": session.get("crop_slug"),
        "location": session.get("location_name"),
        "matches_count": len(session.get("matched_retailers", []))
    }


@router.websocket("/exotel/ws")
async def exotel_voicebot_ws(websocket: WebSocket):
    """
    Exotel Voicebot Bidirectional Audio Streaming WebSocket Endpoint.
    Connects to the Exotel Voicebot Applet.
    Streams synthesized Tamil audio, handles real-time DTMF keypad input,
    announces ranked nearby shops as 'Shop 1', 'Shop 2', etc. with digit-by-digit phone numbers,
    and terminates without connecting calls to retailers.
    """
    await websocket.accept()
    from app.exotel_voicebot import ExotelVoicebotSession
    session = ExotelVoicebotSession(websocket)
    await session.run()
