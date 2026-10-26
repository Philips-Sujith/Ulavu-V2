import enum
import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Enum as SQLEnum,
    func
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from geoalchemy2 import Geography
from app.database import Base

class InquiryStatus(str, enum.Enum):
    PENDING = "PENDING"
    SOLD = "SOLD"
    NOT_INTERESTED = "NOT_INTERESTED"
    NO_RESPONSE = "NO_RESPONSE"
    EXPIRED = "EXPIRED"

class ConfirmedBy(str, enum.Enum):
    RETAILER = "RETAILER"
    FARMER = "FARMER"
    SYSTEM_AUTO = "SYSTEM_AUTO"

class Retailer(Base):
    __tablename__ = "retailers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_name = Column(String, nullable=False)
    owner_name = Column(String, nullable=True)
    phone_number = Column(String, unique=True, nullable=False, index=True)
    location_name = Column(String, nullable=True)
    
    # Point geometry in WGS 84 (SRID 4326) - longitude, latitude
    coordinates = Column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=True),
        nullable=True
    )
    
    # Array of lowercase crop names e.g. ['tomato', 'onion', 'brinjal']
    accepted_crops = Column(ARRAY(String), nullable=False, default=list)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    leads = relationship(
        "InquiryLog",
        back_populates="retailer",
        cascade="all, delete-orphan",
        order_by="desc(InquiryLog.timestamp)"
    )

class InquiryLog(Base):
    __tablename__ = "inquiry_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    farmer_phone = Column(String, nullable=False, index=True)
    crop_inquired = Column(String, nullable=True)
    location_spoken = Column(String, nullable=True)
    matched_retailer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("retailers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    distance_km = Column(Float, nullable=True)
    status = Column(
        SQLEnum(InquiryStatus, name="inquiry_status_enum", native_enum=False),
        default=InquiryStatus.PENDING,
        nullable=False,
        index=True
    )
    confirmed_by = Column(
        SQLEnum(ConfirmedBy, name="confirmed_by_enum", native_enum=False),
        nullable=True
    )
    call_sid = Column(String, nullable=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    retailer = relationship("Retailer", back_populates="leads")
