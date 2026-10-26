import asyncio
import logging
from sqlalchemy import select, delete
from app.database import AsyncSessionLocal, init_db
from app.models import Retailer, InquiryLog, InquiryStatus, ConfirmedBy
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Primary test phone number for live SMS notifications
PRIMARY_TEST_PHONE = settings.TEST_RETAILER_PHONE or "+919876543210"

SAMPLE_RETAILERS = [
    {
        "business_name": "Sri Murugan Agro Traders",
        "owner_name": "K. Murugesan",
        "phone_number": PRIMARY_TEST_PHONE,
        "location_name": "Madurantakam",
        "lat": 12.5085,
        "lng": 79.8850,
        "accepted_crops": ["tomato", "onion", "chilli"],
        "is_active": True,
    },
    {
        "business_name": "Cauvery Green Mandi",
        "owner_name": "S. Arumugam",
        "phone_number": "+919442183952",
        "location_name": "Madurantakam",
        "lat": 12.5150,
        "lng": 79.8920,
        "accepted_crops": ["brinjal", "okra", "tomato"],
        "is_active": False,
    },
    {
        "business_name": "Chengalpattu Farmers Hub",
        "owner_name": "P. Selvam",
        "phone_number": "+919840371946",
        "location_name": "Chengalpattu",
        "lat": 12.6841,
        "lng": 79.9836,
        "accepted_crops": ["tomato", "brinjal", "okra"],
        "is_active": True,
    },
    {
        "business_name": "Vetri Agro Wholesalers",
        "owner_name": "V. Thangavel",
        "phone_number": "+919788241590",
        "location_name": "Chengalpattu",
        "lat": 12.6900,
        "lng": 79.9750,
        "accepted_crops": ["onion", "chilli"],
        "is_active": False,
    },
    {
        "business_name": "Kanchipuram Uzhavar Vanigam",
        "owner_name": "M. Ramanathan",
        "phone_number": "+919884219573",
        "location_name": "Kanchipuram",
        "lat": 12.8342,
        "lng": 79.7036,
        "accepted_crops": ["tomato", "onion", "brinjal", "chilli", "okra"],
        "is_active": True,
    },
    {
        "business_name": "Tirukalukundram Bio Mandi",
        "owner_name": "R. Natarajan",
        "phone_number": "+919940825317",
        "location_name": "Tirukalukundram",
        "lat": 12.6105,
        "lng": 80.0537,
        "accepted_crops": ["tomato", "okra", "onion"],
        "is_active": True,
    },
]

async def seed_database():
    """Initializes schema and seeds sample Tamil Nadu retailers and initial leads."""
    logger.info("Initializing database schema...")
    await init_db()

    async with AsyncSessionLocal() as session:
        logger.info("Checking existing retailers...")
        # Check if table already has data
        result = await session.execute(select(Retailer))
        existing_retailers = result.scalars().all()

        if existing_retailers:
            logger.info(f"Database already contains {len(existing_retailers)} retailers. Syncing sample retailer phones...")
            updated_count = 0
            sample_map = {r["business_name"]: r["phone_number"] for r in SAMPLE_RETAILERS}
            for r in existing_retailers:
                if r.business_name == "Sri Murugan Agro Traders" and settings.TEST_RETAILER_PHONE:
                    if r.phone_number != settings.TEST_RETAILER_PHONE:
                        r.phone_number = settings.TEST_RETAILER_PHONE
                        updated_count += 1
                elif r.business_name in sample_map and r.business_name != "Sri Murugan Agro Traders":
                    target_phone = sample_map[r.business_name]
                    if r.phone_number != target_phone:
                        r.phone_number = target_phone
                        updated_count += 1
                        logger.info(f"Updated {r.business_name} phone to realistic number: {target_phone}")
            if updated_count > 0:
                await session.commit()
                logger.info(f"Committed {updated_count} sample retailer phone updates.")
            return

        logger.info("Seeding 6 sample retailers across Tamil Nadu...")
        seeded_objects = []
        for item in SAMPLE_RETAILERS:
            wkt_point = f"SRID=4326;POINT({item['lng']} {item['lat']})"
            retailer = Retailer(
                business_name=item["business_name"],
                owner_name=item["owner_name"],
                phone_number=item["phone_number"],
                location_name=item["location_name"],
                coordinates=wkt_point,
                accepted_crops=item["accepted_crops"],
                is_active=item["is_active"],
            )
            session.add(retailer)
            seeded_objects.append(retailer)

        await session.commit()
        for r in seeded_objects:
            await session.refresh(r)
        logger.info(f"Successfully seeded {len(seeded_objects)} retailers.")

        # Seed 3 initial inquiry leads for Sri Murugan and Chengalpattu
        sri_murugan = seeded_objects[0]
        chengalpattu_hub = seeded_objects[2]

        sample_leads = [
            InquiryLog(
                farmer_phone="+919710482615",
                crop_inquired="tomato",
                location_spoken="Madurantakam",
                matched_retailer_id=sri_murugan.id,
                distance_km=2.4,
                status=InquiryStatus.PENDING,
                call_sid="CA_demo_seed_001"
            ),
            InquiryLog(
                farmer_phone="+919820593741",
                crop_inquired="onion",
                location_spoken="Maduranthagam",
                matched_retailer_id=sri_murugan.id,
                distance_km=3.1,
                status=InquiryStatus.SOLD,
                confirmed_by=ConfirmedBy.RETAILER,
                call_sid="CA_demo_seed_002"
            ),
            InquiryLog(
                farmer_phone="+919930847125",
                crop_inquired="okra",
                location_spoken="Chengalpattu",
                matched_retailer_id=chengalpattu_hub.id,
                distance_km=1.8,
                status=InquiryStatus.PENDING,
                call_sid="CA_demo_seed_003"
            ),
        ]
        session.add_all(sample_leads)
        await session.commit()
        logger.info(f"Successfully seeded {len(sample_leads)} initial sample inquiry leads.")

if __name__ == "__main__":
    asyncio.run(seed_database())
