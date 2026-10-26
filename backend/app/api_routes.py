import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime, date
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update
from geoalchemy2.shape import to_shape
from geoalchemy2 import Geography

from app.database import get_db
from app.models import Retailer, InquiryLog, InquiryStatus, ConfirmedBy
from app.schemas import (
    RetailerCreate,
    RetailerResponse,
    RetailerStatusToggleResponse,
    InquiryLogResponse,
    InquiryStatusUpdate,
    StatsResponse,
)
from app.sms import mask_phone_number
from app.matching import normalize_crop, find_nearest_retailer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Retailer Portal API"])


def _extract_coords(coordinates) -> tuple[Optional[float], Optional[float]]:
    """Helper to extract (latitude, longitude) from GeoAlchemy2 Geography Point."""
    if coordinates is None:
        return None, None
    try:
        point = to_shape(coordinates)
        return float(point.y), float(point.x)  # lat is y, lng is x
    except Exception as e:
        logger.debug(f"Could not parse shape coordinates: {e}")
        return None, None


@router.get("/retailers", response_model=List[RetailerResponse])
async def list_retailers(db: AsyncSession = Depends(get_db)):
    """
    Returns all registered retailers with parsed coordinates and lead counts.
    """
    stmt = select(Retailer).order_by(Retailer.created_at.desc())
    result = await db.execute(stmt)
    retailers = result.scalars().all()

    # Pre-fetch lead counts
    lead_counts_stmt = (
        select(InquiryLog.matched_retailer_id, func.count(InquiryLog.id))
        .where(InquiryLog.matched_retailer_id.is_not(None))
        .group_by(InquiryLog.matched_retailer_id)
    )
    counts_res = await db.execute(lead_counts_stmt)
    counts_map = dict(counts_res.all())

    response_items = []
    for r in retailers:
        lat, lng = _extract_coords(r.coordinates)
        response_items.append(
            RetailerResponse(
                id=r.id,
                business_name=r.business_name,
                owner_name=r.owner_name,
                phone_number=r.phone_number,
                location_name=r.location_name,
                accepted_crops=r.accepted_crops or [],
                is_active=r.is_active,
                created_at=r.created_at,
                latitude=lat,
                longitude=lng,
                leads_count=counts_map.get(r.id, 0)
            )
        )
    return response_items


@router.post("/retailers", response_model=RetailerResponse, status_code=status.HTTP_201_CREATED)
async def create_retailer(
    payload: RetailerCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Onboards a new retailer from the portal with coordinates and accepted crops.
    """
    # Check if phone number already exists
    existing = await db.execute(
        select(Retailer).where(Retailer.phone_number == payload.phone_number.strip())
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A retailer with this phone number is already registered."
        )

    # Normalize accepted crops to lowercase
    normalized_crops = [c.strip().lower() for c in payload.accepted_crops if c.strip()]

    # Construct WKT Point (longitude latitude) for WGS84
    wkt_point = f"SRID=4326;POINT({payload.longitude} {payload.latitude})"

    new_retailer = Retailer(
        business_name=payload.business_name.strip(),
        owner_name=payload.owner_name.strip() if payload.owner_name else None,
        phone_number=payload.phone_number.strip(),
        location_name=payload.location_name.strip() if payload.location_name else None,
        coordinates=wkt_point,
        accepted_crops=normalized_crops,
        is_active=payload.is_active if payload.is_active is not None else True
    )

    db.add(new_retailer)
    await db.commit()
    await db.refresh(new_retailer)

    lat, lng = _extract_coords(new_retailer.coordinates)
    return RetailerResponse(
        id=new_retailer.id,
        business_name=new_retailer.business_name,
        owner_name=new_retailer.owner_name,
        phone_number=new_retailer.phone_number,
        location_name=new_retailer.location_name,
        accepted_crops=new_retailer.accepted_crops or [],
        is_active=new_retailer.is_active,
        created_at=new_retailer.created_at,
        latitude=lat,
        longitude=lng,
        leads_count=0
    )


@router.patch("/retailers/{retailer_id}/toggle-status", response_model=RetailerStatusToggleResponse)
async def toggle_retailer_status(
    retailer_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Flips the is_active status of a retailer (Active <-> Paused).
    """
    retailer = await db.get(Retailer, retailer_id)
    if not retailer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Retailer not found"
        )

    retailer.is_active = not retailer.is_active
    await db.commit()
    await db.refresh(retailer)

    status_str = "ACTIVE" if retailer.is_active else "PAUSED"
    return RetailerStatusToggleResponse(
        id=retailer.id,
        is_active=retailer.is_active,
        message=f"Retailer is now {status_str}"
    )


@router.get("/retailers/{retailer_id}/leads", response_model=List[InquiryLogResponse])
async def get_retailer_leads(
    retailer_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches all incoming leads/inquiries routed to this retailer, ordered latest first.
    """
    stmt = (
        select(InquiryLog)
        .where(InquiryLog.matched_retailer_id == retailer_id)
        .order_by(desc(InquiryLog.timestamp))
    )
    result = await db.execute(stmt)
    inquiries = result.scalars().all()

    response_items = []
    for inq in inquiries:
        response_items.append(
            InquiryLogResponse(
                id=inq.id,
                farmer_phone=inq.farmer_phone,
                masked_farmer_phone=mask_phone_number(inq.farmer_phone),
                crop_inquired=inq.crop_inquired,
                location_spoken=inq.location_spoken,
                matched_retailer_id=inq.matched_retailer_id,
                distance_km=inq.distance_km,
                status=inq.status,
                confirmed_by=inq.confirmed_by,
                call_sid=inq.call_sid,
                timestamp=inq.timestamp
            )
        )
    return response_items


@router.patch("/inquiries/{inquiry_id}/status", response_model=InquiryLogResponse)
async def update_inquiry_status(
    inquiry_id: UUID,
    payload: InquiryStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Updates lead status (SOLD, NOT_INTERESTED, NO_RESPONSE) and sets confirmed_by = RETAILER.
    """
    inquiry = await db.get(InquiryLog, inquiry_id)
    if not inquiry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inquiry not found"
        )

    inquiry.status = payload.status
    inquiry.confirmed_by = ConfirmedBy.RETAILER

    await db.commit()
    await db.refresh(inquiry)

    return InquiryLogResponse(
        id=inquiry.id,
        farmer_phone=inquiry.farmer_phone,
        masked_farmer_phone=mask_phone_number(inquiry.farmer_phone),
        crop_inquired=inquiry.crop_inquired,
        location_spoken=inquiry.location_spoken,
        matched_retailer_id=inquiry.matched_retailer_id,
        distance_km=inquiry.distance_km,
        status=inquiry.status,
        confirmed_by=inquiry.confirmed_by,
        call_sid=inquiry.call_sid,
        timestamp=inquiry.timestamp
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Returns aggregated KPIs:
    - Total inquiries today
    - Match rate (%)
    - Active retailer count
    - Total retailer count
    """
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # Inquiries today
    today_stmt = select(func.count(InquiryLog.id)).where(InquiryLog.timestamp >= today_start)
    today_res = await db.execute(today_stmt)
    inquiries_today = today_res.scalar() or 0

    # Total inquiries all time
    total_inq_stmt = select(func.count(InquiryLog.id))
    total_inq_res = await db.execute(total_inq_stmt)
    total_inquiries = total_inq_res.scalar() or 0

    # Total matched inquiries
    matched_inq_stmt = select(func.count(InquiryLog.id)).where(InquiryLog.matched_retailer_id.is_not(None))
    matched_inq_res = await db.execute(matched_inq_stmt)
    matched_inquiries = matched_inq_res.scalar() or 0

    match_rate = (
        round((matched_inquiries / total_inquiries) * 100, 1)
        if total_inquiries > 0
        else 100.0
    )

    # Active and total retailers
    active_retailers_stmt = select(func.count(Retailer.id)).where(Retailer.is_active.is_(True))
    active_res = await db.execute(active_retailers_stmt)
    active_count = active_res.scalar() or 0

    total_retailers_stmt = select(func.count(Retailer.id))
    total_ret_res = await db.execute(total_retailers_stmt)
    total_retailers = total_ret_res.scalar() or 0

    return StatsResponse(
        total_inquiries_today=inquiries_today,
        match_rate_percentage=match_rate,
        active_retailer_count=active_count,
        total_retailers=total_retailers
    )


@router.get("/inquiries", response_model=List[InquiryLogResponse])
async def get_all_inquiries(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns latest inquiries across all retailers for portal oversight.
    """
    stmt = select(InquiryLog).order_by(desc(InquiryLog.timestamp)).limit(limit)
    result = await db.execute(stmt)
    inquiries = result.scalars().all()

    return [
        InquiryLogResponse(
            id=inq.id,
            farmer_phone=inq.farmer_phone,
            masked_farmer_phone=mask_phone_number(inq.farmer_phone),
            crop_inquired=inq.crop_inquired,
            location_spoken=inq.location_spoken,
            matched_retailer_id=inq.matched_retailer_id,
            distance_km=inq.distance_km,
            status=inq.status,
            confirmed_by=inq.confirmed_by,
            call_sid=inq.call_sid,
            timestamp=inq.timestamp
        )
        for inq in inquiries
    ]


@router.get("/options")
async def get_crop_and_location_options():
    """
    Returns supported crops and location presets consistent with voicebot and matching engine.
    """
    from app.exotel_voicebot import CROP_OPTIONS, LOCATION_OPTIONS
    from app.matching import TOWN_COORDINATES

    crops = [
        {"id": info["slug"], "name": info["slug"].replace("_", " ").title(), "tamil": info["tamil"]}
        for info in CROP_OPTIONS.values()
    ]
    locations = [
        {
            "name": info["name"],
            "tamil": info["tamil"],
            "lat": TOWN_COORDINATES.get(info["name"].lower(), (0.0, 0.0))[0],
            "lng": TOWN_COORDINATES.get(info["name"].lower(), (0.0, 0.0))[1],
        }
        for info in LOCATION_OPTIONS.values()
    ]
    return {"crops": crops, "locations": locations}
