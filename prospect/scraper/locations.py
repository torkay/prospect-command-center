"""Location expansion for deeper searches."""

import math
from dataclasses import dataclass
from typing import List, Dict, Optional

from prospect import _native


@dataclass
class Location:
    """Location with coordinates."""
    name: str
    lat: float
    lng: float
    type: str = "suburb"  # suburb, city, cbd, region


# Major Australian cities with suburbs
AUSTRALIAN_LOCATIONS: Dict[str, List[Location]] = {
    "brisbane": [
        Location("Brisbane CBD", -27.4698, 153.0251, "cbd"),
        Location("South Brisbane", -27.4818, 153.0205, "suburb"),
        Location("Fortitude Valley", -27.4568, 153.0358, "suburb"),
        Location("West End", -27.4833, 153.0089, "suburb"),
        Location("New Farm", -27.4670, 153.0508, "suburb"),
        Location("Paddington", -27.4600, 153.0050, "suburb"),
        Location("Milton", -27.4700, 153.0000, "suburb"),
        Location("Woolloongabba", -27.4900, 153.0350, "suburb"),
        Location("Kangaroo Point", -27.4800, 153.0350, "suburb"),
        Location("Spring Hill", -27.4617, 153.0233, "suburb"),
        Location("Newstead", -27.4500, 153.0450, "suburb"),
        Location("Teneriffe", -27.4533, 153.0483, "suburb"),
        Location("Ascot", -27.4317, 153.0583, "suburb"),
        Location("Hamilton", -27.4367, 153.0633, "suburb"),
        Location("Bulimba", -27.4517, 153.0617, "suburb"),
        Location("Coorparoo", -27.4950, 153.0550, "suburb"),
        Location("Greenslopes", -27.5050, 153.0450, "suburb"),
        Location("Annerley", -27.5100, 153.0350, "suburb"),
        Location("Toowong", -27.4850, 152.9883, "suburb"),
        Location("Indooroopilly", -27.5000, 152.9750, "suburb"),
        Location("Chermside", -27.3850, 153.0300, "suburb"),
        Location("Stafford", -27.4100, 153.0117, "suburb"),
        Location("Nundah", -27.3983, 153.0617, "suburb"),
        Location("Clayfield", -27.4200, 153.0517, "suburb"),
        Location("Kedron", -27.4017, 153.0283, "suburb"),
    ],
    "sydney": [
        Location("Sydney CBD", -33.8688, 151.2093, "cbd"),
        Location("Surry Hills", -33.8838, 151.2117, "suburb"),
        Location("Darlinghurst", -33.8763, 151.2183, "suburb"),
        Location("Potts Point", -33.8700, 151.2267, "suburb"),
        Location("Bondi", -33.8917, 151.2667, "suburb"),
        Location("Newtown", -33.8967, 151.1783, "suburb"),
        Location("Glebe", -33.8783, 151.1833, "suburb"),
        Location("Pyrmont", -33.8700, 151.1933, "suburb"),
        Location("Paddington", -33.8850, 151.2267, "suburb"),
        Location("Redfern", -33.8933, 151.2033, "suburb"),
        Location("Manly", -33.7950, 151.2867, "suburb"),
        Location("Parramatta", -33.8150, 151.0011, "suburb"),
        Location("Chatswood", -33.7950, 151.1800, "suburb"),
        Location("North Sydney", -33.8383, 151.2067, "suburb"),
        Location("Mosman", -33.8267, 151.2433, "suburb"),
        Location("Crows Nest", -33.8267, 151.2050, "suburb"),
        Location("Double Bay", -33.8783, 151.2450, "suburb"),
        Location("Neutral Bay", -33.8317, 151.2200, "suburb"),
        Location("Balmain", -33.8567, 151.1800, "suburb"),
        Location("Leichhardt", -33.8850, 151.1567, "suburb"),
    ],
    "melbourne": [
        Location("Melbourne CBD", -37.8136, 144.9631, "cbd"),
        Location("South Yarra", -37.8383, 144.9917, "suburb"),
        Location("Richmond", -37.8183, 145.0000, "suburb"),
        Location("Fitzroy", -37.7950, 144.9783, "suburb"),
        Location("Carlton", -37.7950, 144.9667, "suburb"),
        Location("St Kilda", -37.8667, 144.9800, "suburb"),
        Location("Prahran", -37.8500, 144.9917, "suburb"),
        Location("Collingwood", -37.8017, 144.9883, "suburb"),
        Location("Brunswick", -37.7667, 144.9600, "suburb"),
        Location("South Melbourne", -37.8317, 144.9583, "suburb"),
        Location("Docklands", -37.8150, 144.9467, "suburb"),
        Location("Southbank", -37.8233, 144.9633, "suburb"),
        Location("Port Melbourne", -37.8383, 144.9383, "suburb"),
        Location("Albert Park", -37.8450, 144.9567, "suburb"),
        Location("Hawthorn", -37.8217, 145.0333, "suburb"),
        Location("Toorak", -37.8433, 145.0150, "suburb"),
        Location("Camberwell", -37.8367, 145.0667, "suburb"),
        Location("Malvern", -37.8567, 145.0317, "suburb"),
        Location("Brighton", -37.9067, 145.0033, "suburb"),
        Location("Kew", -37.8050, 145.0333, "suburb"),
    ],
    "gold coast": [
        Location("Surfers Paradise", -28.0027, 153.4299, "cbd"),
        Location("Broadbeach", -28.0268, 153.4319, "suburb"),
        Location("Southport", -27.9673, 153.4054, "suburb"),
        Location("Burleigh Heads", -28.0883, 153.4456, "suburb"),
        Location("Coolangatta", -28.1669, 153.5366, "suburb"),
        Location("Main Beach", -27.9750, 153.4283, "suburb"),
        Location("Robina", -28.0783, 153.3867, "suburb"),
        Location("Nerang", -28.0000, 153.3333, "suburb"),
        Location("Mermaid Beach", -28.0417, 153.4350, "suburb"),
        Location("Currumbin", -28.1350, 153.4817, "suburb"),
        Location("Palm Beach", -28.1150, 153.4633, "suburb"),
        Location("Miami", -28.0650, 153.4417, "suburb"),
    ],
    "perth": [
        Location("Perth CBD", -31.9505, 115.8605, "cbd"),
        Location("Fremantle", -32.0569, 115.7439, "suburb"),
        Location("Subiaco", -31.9450, 115.8267, "suburb"),
        Location("Northbridge", -31.9467, 115.8583, "suburb"),
        Location("Leederville", -31.9333, 115.8417, "suburb"),
        Location("Mount Lawley", -31.9283, 115.8733, "suburb"),
        Location("Victoria Park", -31.9767, 115.8967, "suburb"),
        Location("South Perth", -31.9700, 115.8617, "suburb"),
        Location("Cottesloe", -31.9950, 115.7550, "suburb"),
        Location("Claremont", -31.9800, 115.7817, "suburb"),
        Location("Nedlands", -31.9817, 115.8050, "suburb"),
        Location("Scarborough", -31.8933, 115.7617, "suburb"),
    ],
    "adelaide": [
        Location("Adelaide CBD", -34.9285, 138.6007, "cbd"),
        Location("North Adelaide", -34.9100, 138.5967, "suburb"),
        Location("Norwood", -34.9217, 138.6317, "suburb"),
        Location("Glenelg", -34.9817, 138.5150, "suburb"),
        Location("Unley", -34.9500, 138.6067, "suburb"),
        Location("Prospect", -34.8817, 138.5967, "suburb"),
        Location("Henley Beach", -34.9183, 138.4967, "suburb"),
        Location("Burnside", -34.9367, 138.6617, "suburb"),
        Location("Walkerville", -34.8633, 138.6200, "suburb"),
        Location("Parkside", -34.9417, 138.6183, "suburb"),
    ],
    "canberra": [
        Location("Canberra City", -35.2809, 149.1300, "cbd"),
        Location("Braddon", -35.2717, 149.1333, "suburb"),
        Location("Kingston", -35.3117, 149.1400, "suburb"),
        Location("Manuka", -35.3183, 149.1367, "suburb"),
        Location("Dickson", -35.2517, 149.1417, "suburb"),
        Location("Belconnen", -35.2417, 149.0667, "suburb"),
        Location("Woden", -35.3450, 149.0867, "suburb"),
        Location("Tuggeranong", -35.4250, 149.0683, "suburb"),
    ],
    "hobart": [
        Location("Hobart CBD", -42.8821, 147.3272, "cbd"),
        Location("Sandy Bay", -42.8983, 147.3233, "suburb"),
        Location("Battery Point", -42.8900, 147.3317, "suburb"),
        Location("North Hobart", -42.8717, 147.3167, "suburb"),
        Location("Salamanca", -42.8867, 147.3350, "suburb"),
        Location("Glenorchy", -42.8317, 147.2733, "suburb"),
    ],
    "darwin": [
        Location("Darwin CBD", -12.4634, 130.8456, "cbd"),
        Location("Stuart Park", -12.4483, 130.8367, "suburb"),
        Location("Parap", -12.4317, 130.8467, "suburb"),
        Location("Nightcliff", -12.3883, 130.8417, "suburb"),
        Location("Fannie Bay", -12.4400, 130.8350, "suburb"),
    ],
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in kilometres."""
    if _native.haversine_distance is not None:
        return _native.haversine_distance(lat1, lon1, lat2, lon2)

    R = 6371  # Earth's radius in km

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = math.sin(delta_lat / 2) ** 2 + \
        math.cos(lat1_rad) * math.cos(lat2_rad) * \
        math.sin(delta_lon / 2) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def get_nearby_suburbs(
    location: str,
    radius_km: float = 10,
    max_results: int = 10,
) -> List[str]:
    """
    Get nearby suburbs for location expansion.

    Args:
        location: City/suburb name (e.g., "Brisbane", "Sydney CBD")
        radius_km: Search radius in kilometres
        max_results: Maximum suburbs to return

    Returns:
        List of suburb names for search queries
    """
    location_lower = location.lower().strip()

    # Find the base city
    base_city: Optional[str] = None
    base_location: Optional[Location] = None

    for city, suburbs in AUSTRALIAN_LOCATIONS.items():
        if city in location_lower or location_lower in city:
            base_city = city
            # Find exact suburb or use CBD
            for suburb in suburbs:
                if suburb.name.lower() == location_lower:
                    base_location = suburb
                    break
            if not base_location:
                # Use CBD as base
                base_location = suburbs[0]
            break

        # Check suburbs
        for suburb in suburbs:
            if suburb.name.lower() in location_lower or location_lower in suburb.name.lower():
                base_city = city
                base_location = suburb
                break

        if base_city:
            break

    if not base_city or not base_location:
        # Unknown location, return original
        return [location]

    # Calculate distances and filter
    suburbs = AUSTRALIAN_LOCATIONS[base_city]
    nearby: List[tuple] = []

    # Use batch Rust haversine if available
    if _native.batch_haversine is not None:
        other_suburbs = [(s, i) for i, s in enumerate(suburbs) if s.name != base_location.name]
        if other_suburbs:
            points = [(s.lat, s.lng) for s, _ in other_suburbs]
            distances = _native.batch_haversine(base_location.lat, base_location.lng, points)
            for (suburb, _), distance in zip(other_suburbs, distances):
                if distance <= radius_km:
                    nearby.append((suburb.name, distance))
    else:
        for suburb in suburbs:
            if suburb.name == base_location.name:
                continue

            distance = haversine_distance(
                base_location.lat, base_location.lng,
                suburb.lat, suburb.lng
            )

            if distance <= radius_km:
                nearby.append((suburb.name, distance))

    # Sort by distance and limit
    nearby.sort(key=lambda x: x[1])
    result = [base_location.name] + [s[0] for s in nearby[:max_results - 1]]

    return result


def expand_query_variations(
    business_type: str,
    templates: List[str],
) -> List[str]:
    """
    Generate query variations from templates.

    Args:
        business_type: Base business type (e.g., "plumber")
        templates: List of templates with {business_type} placeholder

    Returns:
        List of expanded queries
    """
    variations = [business_type]  # Always include base query

    for template in templates:
        expanded = template.format(business_type=business_type)
        if expanded not in variations:
            variations.append(expanded)

    return variations


def get_location_coordinates(location: str) -> Optional[tuple]:
    """
    Get coordinates for a location name.

    Returns:
        Tuple of (lat, lng) or None if not found
    """
    location_lower = location.lower().strip()

    for city, suburbs in AUSTRALIAN_LOCATIONS.items():
        for suburb in suburbs:
            if suburb.name.lower() == location_lower or city == location_lower:
                return (suburb.lat, suburb.lng)

    return None


# Mapping of city names to SerpAPI-compatible coordinates
CITY_COORDINATES = {
    "brisbane": "@-27.4698,153.0251,12z",
    "sydney": "@-33.8688,151.2093,12z",
    "melbourne": "@-37.8136,144.9631,12z",
    "perth": "@-31.9505,115.8605,12z",
    "adelaide": "@-34.9285,138.6007,12z",
    "gold coast": "@-28.0167,153.4000,12z",
    "canberra": "@-35.2809,149.1300,12z",
    "hobart": "@-42.8821,147.3272,12z",
    "darwin": "@-12.4634,130.8456,12z",
}


def location_to_coords(location: str) -> str:
    """Convert location name to lat/lng string for SerpAPI Maps."""
    location_lower = location.lower()
    for city, coord in CITY_COORDINATES.items():
        if city in location_lower:
            return coord

    # Default to Brisbane
    return CITY_COORDINATES["brisbane"]
