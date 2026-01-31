from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OpeningHoursResult:
    place_name: str
    opening_hours: str


_FAKE_DB = {
    "spa": "Spa opens at 9am on Sundays",
    "museum": "Museum opens at 10am daily",
    "aquarium": "Aquarium opens at 8am on weekends",
}


def lookup_opening_hours(place_name: str) -> OpeningHoursResult:
    key = place_name.lower().strip()
    hours = _FAKE_DB.get(key, "Hours unavailable. Please contact the venue.")
    return OpeningHoursResult(place_name=place_name, opening_hours=hours)
