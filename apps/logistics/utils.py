"""
Utility functions for logistics calculations, including geocoding and distance calculation.
"""

import math
import requests
from django.core.cache import cache

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
CACHE_TIMEOUT = 86400  # 24 hours


def geocode_postcode(postcode: str) -> tuple[float, float] | None:
    """
    Convert a UK postcode to latitude and longitude using Nominatim.
    Results are cached for 24 hours to minimize API calls.

    Args:
        postcode: UK postcode string (e.g., "SW1A 1AA")

    Returns:
        Tuple of (latitude, longitude) or None if geocoding fails
    """
    if not postcode:
        return None

    # Normalize postcode for caching
    normalized = postcode.strip().upper().replace(" ", "")
    cache_key = f"geocode:{normalized}"

    # Check cache first
    cached = cache.get(cache_key)
    if cached == "NONE":
        return None
    if cached:
        return cached

    try:
        # Add UK country code for better accuracy with UK postcodes
        params = {
            "q": postcode,
            "format": "json",
            "limit": 1,
            "countrycodes": "gb",
        }
        headers = {"User-Agent": "DESD-Group3-FoodMiles/1.0"}

        response = requests.get(
            NOMINATIM_URL, params=params, headers=headers, timeout=5
        )
        response.raise_for_status()
        data = response.json()

        if data and len(data) > 0:
            lat = float(data[0]["lat"])
            lon = float(data[0]["lon"])
            result = (lat, lon)
            # Cache the result
            cache.set(cache_key, result, CACHE_TIMEOUT)
            return result
        else:
            # Cache negative result to avoid hammering the API
            cache.set(cache_key, "NONE", CACHE_TIMEOUT)

    except (requests.RequestException, KeyError, ValueError):
        # Log error but don't crash - return None
        pass

    return None


def haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate the great-circle distance between two points on Earth.

    Args:
        lat1, lon1: Latitude and longitude of point 1 (in degrees)
        lat2, lon2: Latitude and longitude of point 2 (in degrees)

    Returns:
        Distance in miles
    """
    # Earth's radius in miles
    R = 3956

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_distance_between_postcodes(
    postcode1: str, postcode2: str
) -> float | None:
    """
    Calculate the straight-line distance between two postcodes.
    Results are cached to avoid redundant geocoding API calls.

    Args:
        postcode1: First postcode
        postcode2: Second postcode

    Returns:
        Distance in miles or None if calculation fails
    """
    if not postcode1 or not postcode2:
        return None

    # Normalize postcodes for caching
    pc1 = postcode1.strip().upper().replace(" ", "")
    pc2 = postcode2.strip().upper().replace(" ", "")

    # Ensure consistent key regardless of order
    sorted_pcs = sorted([pc1, pc2])
    cache_key = f"dist:{sorted_pcs[0]}:{sorted_pcs[1]}"

    # Check cache first
    cached = cache.get(cache_key)
    if cached == "NONE":
        return None
    if cached is not None:
        return cached

    coords1 = geocode_postcode(postcode1)
    coords2 = geocode_postcode(postcode2)

    if coords1 is None or coords2 is None:
        # Cache the failure to avoid re-calculating
        cache.set(cache_key, "NONE", CACHE_TIMEOUT)
        return None

    distance = haversine_distance(coords1[0], coords1[1], coords2[0], coords2[1])

    # Cache the distance result
    cache.set(cache_key, distance, CACHE_TIMEOUT)

    return distance
