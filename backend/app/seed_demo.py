import asyncio
import logging
from sqlalchemy import select
from app.database import AsyncSessionLocal, init_db
from app.models import Retailer

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ulavu.seed_demo")

# All 9 demo crops supported by all 5 demo retailers
ALL_9_CROPS = [
    "onion",
    "tomato",
    "potato",
    "brinjal",
    "carrot",
    "cabbage",
    "cauliflower",
    "okra",
    "chilli",
]

# 5 Predefined Demo Retailers with 9 Location Mappings (Clearly designated demo lines)
DEMO_RETAILERS_DATA = [
    {
        "business_name": "முருகன் காய்கறி விற்பனை",
        "owner_name": "டெமோ விற்பனையாளர் (Demo Account 1)",
        "phone_number": "9865741275",
        "location_name": "மதுராந்தகம்",
        "lat": 12.5085,
        "lng": 79.8850,
        "assigned_locations": [1, 2],  # Madurantakam, Chengalpattu
    },
    {
        "business_name": "செல்வம் காய்கறி மையம்",
        "owner_name": "டெமோ விற்பனையாளர் (Demo Account 2)",
        "phone_number": "9644157852",
        "location_name": "காஞ்சிபுரம்",
        "lat": 12.8342,
        "lng": 79.7036,
        "assigned_locations": [3, 4],  # Kanchipuram, Tirukalukundram
    },
    {
        "business_name": "ராஜா விவசாய விற்பனை",
        "owner_name": "டெமோ விற்பனையாளர் (Demo Account 3)",
        "phone_number": "9785632147",
        "location_name": "உத்திரமேரூர்",
        "lat": 12.6152,
        "lng": 79.7570,
        "assigned_locations": [5, 6],  # Uthiramerur, Acharapakkam
    },
    {
        "business_name": "குமார் காய்கறி வர்த்தகம்",
        "owner_name": "டெமோ விற்பனையாளர் (Demo Account 4)",
        "phone_number": "9367821450",
        "location_name": "செய்யூர்",
        "lat": 12.3524,
        "lng": 80.0041,
        "assigned_locations": [7, 8],  # Cheyyur, Sriperumbudur
    },
    {
        "business_name": "அருண் வேளாண் விற்பனை",
        "owner_name": "டெமோ விற்பனையாளர் (Demo Account 5)",
        "phone_number": "9874516328",
        "location_name": "வாலாஜாபாத்",
        "lat": 12.7937,
        "lng": 79.8169,
        "assigned_locations": [9],  # Walajabad
    },
]

async def seed_demo_retailers():
    """
    Idempotent seeder: creates or updates the 5 predefined demo retailers.
    Supports all 9 crops, assigns coordinates, and keeps them active.
    Safe to run repeatedly without creating duplicates.
    """
    logger.info("Initializing database schema...")
    await init_db()

    async with AsyncSessionLocal() as session:
        logger.info("Seeding/updating 5 demo retailers...")

        for data in DEMO_RETAILERS_DATA:
            phone = data["phone_number"]
            result = await session.execute(
                select(Retailer).where(
                    (Retailer.phone_number == phone) | (Retailer.business_name == data["business_name"])
                )
            )
            retailer = result.scalars().first()

            wkt_point = f"SRID=4326;POINT({data['lng']} {data['lat']})"

            if retailer:
                # Update existing retailer to ensure active, updated phone and all 9 crops
                retailer.business_name = data["business_name"]
                retailer.owner_name = data["owner_name"]
                retailer.phone_number = phone
                retailer.location_name = data["location_name"]
                retailer.coordinates = wkt_point
                retailer.accepted_crops = ALL_9_CROPS
                retailer.is_active = True
                logger.info(f"Updated demo retailer: {data['business_name']} ({phone})")
            else:
                # Create new retailer
                new_r = Retailer(
                    business_name=data["business_name"],
                    owner_name=data["owner_name"],
                    phone_number=phone,
                    location_name=data["location_name"],
                    coordinates=wkt_point,
                    accepted_crops=ALL_9_CROPS,
                    is_active=True,
                )
                session.add(new_r)
                logger.info(f"Created demo retailer: {data['business_name']} ({phone})")

        await session.commit()
        logger.info("Successfully seeded/verified all 5 demo retailers with all 9 crops!")

if __name__ == "__main__":
    asyncio.run(seed_demo_retailers())
