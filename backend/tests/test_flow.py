# Standalone tests for ULAVU matching, Exotel keypad mappings, and formatting logic
from app.matching import normalize_crop, resolve_location_coordinates, haversine_distance
from app.sms import mask_phone_number
from app.exotel_voicebot import CROP_OPTIONS, LOCATION_OPTIONS

def test_crop_normalization():
    assert normalize_crop("tomato") == "tomato"
    assert normalize_crop("TOMATOES") == "tomato"
    assert normalize_crop("தக்காளி") == "tomato"
    assert normalize_crop("எனக்கு தக்காளி விற்க வேண்டும்") == "tomato"
    assert normalize_crop("onion") == "onion"
    assert normalize_crop("வெங்காயம்") == "onion"
    assert normalize_crop("brinjal") == "brinjal"
    assert normalize_crop("கத்தரிக்காய்") == "brinjal"
    assert normalize_crop("மிளகாய்") == "chilli"
    assert normalize_crop("okra") == "okra"
    assert normalize_crop("ladies finger") == "okra"
    assert normalize_crop("வெண்டைக்காய்") == "okra"

def test_location_resolution():
    madurantakam_coords = resolve_location_coordinates("Madurantakam")
    assert madurantakam_coords == (12.5085, 79.8850)

    tamil_madurantakam = resolve_location_coordinates("மதுராந்தகம்")
    assert tamil_madurantakam == (12.5085, 79.8850)

    chengalpattu_coords = resolve_location_coordinates("near Chengalpattu junction")
    assert chengalpattu_coords == (12.6841, 79.9836)

    kanchipuram_coords = resolve_location_coordinates("காஞ்சிபுரம்")
    assert kanchipuram_coords == (12.8342, 79.7036)

    tirukalukundram_coords = resolve_location_coordinates("Thirukazhukundram")
    assert tirukalukundram_coords == (12.6105, 80.0537)

def test_phone_masking():
    masked = mask_phone_number("+919876543210")
    assert "XXXXX" in masked
    assert not masked.endswith("3210") or masked == "+9198765XXXXX"

def test_haversine_distance():
    # Distance between Madurantakam (12.5085, 79.8850) and Chengalpattu (12.6841, 79.9836)
    dist = haversine_distance(12.5085, 79.8850, 12.6841, 79.9836)
    assert 20.0 < dist < 25.0  # Approx 22.2 km

def test_exotel_keypad_mappings():
    # Verify 9 crops mapped to digits 1-9
    assert len(CROP_OPTIONS) == 9
    assert CROP_OPTIONS["1"]["slug"] == "onion"
    assert CROP_OPTIONS["2"]["slug"] == "tomato"
    assert CROP_OPTIONS["3"]["slug"] == "potato"
    assert CROP_OPTIONS["4"]["slug"] == "brinjal"
    assert CROP_OPTIONS["5"]["slug"] == "carrot"
    assert CROP_OPTIONS["6"]["slug"] == "cabbage"
    assert CROP_OPTIONS["7"]["slug"] == "cauliflower"
    assert CROP_OPTIONS["8"]["slug"] == "okra"
    assert CROP_OPTIONS["9"]["slug"] == "chilli"

    # Verify 9 locations mapped to digits 1-9
    assert len(LOCATION_OPTIONS) == 9
    assert LOCATION_OPTIONS["1"]["name"] == "Madurantakam"
    assert LOCATION_OPTIONS["2"]["name"] == "Chengalpattu"
    assert LOCATION_OPTIONS["3"]["name"] == "Kanchipuram"
    assert LOCATION_OPTIONS["4"]["name"] == "Tirukalukundram"
    assert LOCATION_OPTIONS["5"]["name"] == "Uthiramerur"
    assert LOCATION_OPTIONS["6"]["name"] == "Acharapakkam"
    assert LOCATION_OPTIONS["7"]["name"] == "Cheyyur"
    assert LOCATION_OPTIONS["8"]["name"] == "Sriperumbudur"
    assert LOCATION_OPTIONS["9"]["name"] == "Walajabad"

if __name__ == "__main__":
    test_crop_normalization()
    test_location_resolution()
    test_phone_masking()
    test_haversine_distance()
    test_exotel_keypad_mappings()
    print("All backend logic and Exotel keypad tests passed successfully!")
