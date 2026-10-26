import logging
import math
from typing import Optional, Tuple, List
from sqlalchemy import select, func, cast
from sqlalchemy.ext.asyncio import AsyncSession
from geoalchemy2 import Geography
from app.models import Retailer

logger = logging.getLogger(__name__)

# Known seeded Tamil Nadu towns & coordinates: (latitude, longitude)
TOWN_COORDINATES = {
    "madurantakam": (12.5085, 79.8850),
    "chengalpattu": (12.6841, 79.9836),
    "kanchipuram": (12.8342, 79.7036),
    "tirukalukundram": (12.6105, 80.0537),
    "uthiramerur": (12.6152, 79.7570),
    "acharapakkam": (12.4419, 79.8174),
    "cheyyur": (12.3524, 80.0041),
    "sriperumbudur": (12.9675, 79.9427),
    "walajabad": (12.7937, 79.8169),
}

# Alias dictionary mapping spoken variants (Tamil & English) to town keys
TOWN_LOOKUP = {
    # 1. Madurantakam
    "madurantakam": "madurantakam",
    "maduranthakam": "madurantakam",
    "maduranthagam": "madurantakam",
    "madhurantakam": "madurantakam",
    "madhuranthakam": "madurantakam",
    "மதுராந்தகம்": "madurantakam",
    "மதுராந்தக": "madurantakam",
    
    # 2. Chengalpattu
    "chengalpattu": "chengalpattu",
    "chengalpet": "chengalpattu",
    "chenglepet": "chengalpattu",
    "chengleput": "chengalpattu",
    "செங்கல்பட்டு": "chengalpattu",
    "செங்கை": "chengalpattu",

    # 3. Kanchipuram
    "kanchipuram": "kanchipuram",
    "kancheepuram": "kanchipuram",
    "kanjeevaram": "kanchipuram",
    "kanchi": "kanchipuram",
    "காஞ்சிபுரம்": "kanchipuram",
    "காஞ்சி": "kanchipuram",

    # 4. Tirukalukundram
    "tirukalukundram": "tirukalukundram",
    "thirukazhukundram": "tirukalukundram",
    "tirukazhukundram": "tirukalukundram",
    "திருக்கழுக்குன்றம்": "tirukalukundram",
    "திருக்கழுகுன்றம்": "tirukalukundram",

    # 5. Uthiramerur
    "uthiramerur": "uthiramerur",
    "uttiramerur": "uthiramerur",
    "uthirameror": "uthiramerur",
    "உத்திரமேரூர்": "uthiramerur",
    "உத்திரமேர": "uthiramerur",

    # 6. Acharapakkam
    "acharapakkam": "acharapakkam",
    "acharapakam": "acharapakkam",
    "achirupakkam": "acharapakkam",
    "அச்சரப்பாக்கம்": "acharapakkam",

    # 7. Cheyyur
    "cheyyur": "cheyyur",
    "cheyur": "cheyyur",
    "செய்யூர்": "cheyyur",

    # 8. Sriperumbudur
    "sriperumbudur": "sriperumbudur",
    "sriperumbuthur": "sriperumbudur",
    "ஸ்ரீபெரும்புதூர்": "sriperumbudur",

    # 9. Walajabad
    "walajabad": "walajabad",
    "walajapet": "walajabad",
    "வாலாஜாபாத்": "walajabad",
}

# Crop name mappings from Tamil and spoken English to standardized slugs (All 9 Crops)
CROP_MAPPINGS = {
    # 1. Onion
    "onion": "onion",
    "onions": "onion",
    "vengayam": "onion",
    "chinna vengayam": "onion",
    "periya vengayam": "onion",
    "வெங்காயம்": "onion",
    "சின்ன வெங்காயம்": "onion",
    "பெரிய வெங்காயம்": "onion",

    # 2. Tomato
    "tomato": "tomato",
    "tomatoes": "tomato",
    "thakkali": "tomato",
    "தக்காளி": "tomato",
    "தக்காளி பழம்": "tomato",

    # 3. Potato
    "potato": "potato",
    "potatoes": "potato",
    "urulakilangu": "potato",
    "urulaikizhangu": "potato",
    "உருளைக்கிழங்கு": "potato",
    "உருளை": "potato",

    # 4. Brinjal
    "brinjal": "brinjal",
    "brinjals": "brinjal",
    "eggplant": "brinjal",
    "aubergine": "brinjal",
    "kathirikai": "brinjal",
    "kathiri": "brinjal",
    "கத்தரிக்காய்": "brinjal",
    "கத்திரி": "brinjal",

    # 5. Carrot
    "carrot": "carrot",
    "carrots": "carrot",
    "கேரட்": "carrot",

    # 6. Cabbage
    "cabbage": "cabbage",
    "muttaikose": "cabbage",
    "முட்டைக்கோஸ்": "cabbage",
    "கோஸ்": "cabbage",

    # 7. Cauliflower
    "cauliflower": "cauliflower",
    "காலிஃப்ளவர்": "cauliflower",
    "பூக்கோசு": "cauliflower",

    # 8. Okra
    "okra": "okra",
    "ladies finger": "okra",
    "lady finger": "okra",
    "ladyfinger": "okra",
    "bhindi": "okra",
    "vendaikkai": "okra",
    "vendai": "okra",
    "வெண்டைக்காய்": "okra",
    "வெண்டை": "okra",

    # 9. Green Chilli
    "chilli": "chilli",
    "chillies": "chilli",
    "chili": "chilli",
    "green chilli": "chilli",
    "milagai": "chilli",
    "pachai milagai": "chilli",
    "மிளகாய்": "chilli",
    "பச்சை மிளகாய்": "chilli",
}

# Predefined Demo Retailers Fallback for the 9 Demo Locations (Designated demo lines)
DEMO_LOCATION_FALLBACKS = {
    "1": {"phone": "9865741275", "name": "முருகன் காய்கறி விற்பனை", "location": "மதுராந்தகம்", "dist": 2.1},
    "2": {"phone": "9865741275", "name": "முருகன் காய்கறி விற்பனை", "location": "மதுராந்தகம்", "dist": 3.4},
    "3": {"phone": "9644157852", "name": "செல்வம் காய்கறி மையம்", "location": "காஞ்சிபுரம்", "dist": 1.8},
    "4": {"phone": "9644157852", "name": "செல்வம் காய்கறி மையம்", "location": "காஞ்சிபுரம்", "dist": 4.2},
    "5": {"phone": "9785632147", "name": "ராஜா விவசாய விற்பனை", "location": "உத்திரமேரூர்", "dist": 2.5},
    "6": {"phone": "9785632147", "name": "ராஜா விவசாய விற்பனை", "location": "உத்திரமேரூர்", "dist": 3.8},
    "7": {"phone": "9367821450", "name": "குமார் காய்கறி வர்த்தகம்", "location": "செய்யூர்", "dist": 1.9},
    "8": {"phone": "9367821450", "name": "குமார் காய்கறி வர்த்தகம்", "location": "செய்யூர்", "dist": 4.0},
    "9": {"phone": "9874516328", "name": "அருண் வேளாண் விற்பனை", "location": "வாலாஜாபாத்", "dist": 2.0},
}

def normalize_crop(crop_input: str) -> str:
    """Normalize spoken or typed crop input to standard slug."""
    if not crop_input:
        return ""
    clean = crop_input.strip().lower()
    for phrase, standard in CROP_MAPPINGS.items():
        if phrase in clean:
            return standard
    return clean

def resolve_location_coordinates(location_input: str) -> Optional[Tuple[float, float]]:
    """Resolve spoken or typed location text to (latitude, longitude)."""
    if not location_input:
        return None
    clean = location_input.strip().lower()
    for alias, town_key in TOWN_LOOKUP.items():
        if alias in clean:
            return TOWN_COORDINATES[town_key]
    return None

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great circle distance in kilometers between two points."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def find_nearest_retailers(
    db: AsyncSession,
    crop: str,
    location_text: str,
    radius_km: float = 25.0,
    limit: int = 3
) -> List[Tuple[Retailer, float]]:
    """
    Finds up to `limit` active retailers buying the specified crop within radius_km (default 25km),
    ranked by proximity ascending (nearest first).
    Uses PostGIS ST_DWithin and ST_Distance on geography, with a Haversine distance fallback.
    """
    normalized_crop = normalize_crop(crop)
    coords = resolve_location_coordinates(location_text)

    if not coords or not normalized_crop:
        logger.info(
            f"Matching failed early: coords={coords}, normalized_crop='{normalized_crop}' "
            f"from crop='{crop}', location='{location_text}'"
        )
        return []

    lat, lng = coords
    radius_meters = radius_km * 1000.0

    try:
        # Create PostGIS geography point (longitude, latitude for WGS84)
        target_point = func.ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)
        target_geog = cast(target_point, Geography)

        distance_expr = (func.ST_Distance(Retailer.coordinates, target_geog) / 1000.0).label("distance_km")

        # PostGIS query: active = true, crop in accepted_crops, within radius_km
        stmt = (
            select(Retailer, distance_expr)
            .where(
                Retailer.is_active.is_(True),
                Retailer.accepted_crops.any(normalized_crop),
                func.ST_DWithin(Retailer.coordinates, target_geog, radius_meters)
            )
            .order_by(distance_expr.asc())
            .limit(limit)
        )

        result = await db.execute(stmt)
        rows = result.all()
        if rows:
            return [(r, round(float(dist), 2)) for r, dist in rows]

    except Exception as err:
        logger.warning(f"PostGIS query failed or unsupported in current environment, falling back to python distance: {err}")

    # Fallback: Query active retailers accepting this crop and compute haversine distance
    try:
        stmt = (
            select(Retailer)
            .where(
                Retailer.is_active.is_(True),
                Retailer.accepted_crops.any(normalized_crop)
            )
        )
        result = await db.execute(stmt)
        retailers = result.scalars().all()

        matches: List[Tuple[Retailer, float]] = []

        for r in retailers:
            if r.coordinates is not None:
                try:
                    from geoalchemy2.shape import to_shape
                    shape = to_shape(r.coordinates)
                    r_lng, r_lat = shape.x, shape.y
                    dist = haversine_distance(lat, lng, r_lat, r_lng)
                    if dist <= radius_km:
                        matches.append((r, round(dist, 2)))
                except Exception as ex:
                    logger.debug(f"Error parsing coordinates for retailer {r.id}: {ex}")

        matches.sort(key=lambda x: x[1])
        return matches[:limit]
    except Exception as fallback_err:
        logger.error(f"Fallback distance calculation failed: {fallback_err}")
        return []


async def find_nearest_retailer(
    db: AsyncSession,
    crop: str,
    location_text: str,
    radius_km: float = 25.0
) -> Optional[Tuple[Retailer, float]]:
    """
    Finds the single nearest active retailer buying the specified crop within radius_km.
    Convenience wrapper around find_nearest_retailers with limit=1.
    """
    matches = await find_nearest_retailers(
        db=db,
        crop=crop,
        location_text=location_text,
        radius_km=radius_km,
        limit=1
    )
    return matches[0] if matches else None
