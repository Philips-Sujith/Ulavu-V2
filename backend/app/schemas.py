from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field
from app.models import InquiryStatus, ConfirmedBy

class RetailerBase(BaseModel):
    business_name: str
    owner_name: Optional[str] = None
    phone_number: str
    location_name: Optional[str] = None
    accepted_crops: List[str] = Field(default_factory=list)

class RetailerCreate(RetailerBase):
    latitude: float
    longitude: float
    is_active: Optional[bool] = True

class RetailerResponse(RetailerBase):
    id: UUID
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: bool
    created_at: Optional[datetime] = None
    leads_count: Optional[int] = 0

    class Config:
        from_attributes = True

class RetailerStatusToggleResponse(BaseModel):
    id: UUID
    is_active: bool
    message: str

class InquiryLogResponse(BaseModel):
    id: UUID
    farmer_phone: str
    masked_farmer_phone: Optional[str] = None
    crop_inquired: Optional[str] = None
    location_spoken: Optional[str] = None
    matched_retailer_id: Optional[UUID] = None
    distance_km: Optional[float] = None
    status: InquiryStatus
    confirmed_by: Optional[ConfirmedBy] = None
    call_sid: Optional[str] = None
    timestamp: datetime

    class Config:
        from_attributes = True

class InquiryStatusUpdate(BaseModel):
    status: InquiryStatus

class StatsResponse(BaseModel):
    total_inquiries_today: int
    match_rate_percentage: float
    active_retailer_count: int
    total_retailers: int
