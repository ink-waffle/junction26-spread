"""The map and the calendar: road minutes between places, and when a site is open."""
from __future__ import annotations

import math
from typing import Optional

from spread.types import OpeningHours, WorldMap

HOUR, DAY, WEEK = 60, 24 * 60, 7 * 24 * 60


def is_business_day(day: int) -> bool:
    return day % 7 < 5


def next_business_day(day: int) -> int:
    day += 1
    while not is_business_day(day):
        day += 1
    return day


def clock(minute: int) -> str:
    """A world minute as "Tue 14:05", for logs."""
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return f"{names[minute // DAY % 7]}{'+' if minute >= WEEK else ''} {minute % DAY // HOUR:02d}:{minute % HOUR:02d}"


def open_spans(hours: Optional[OpeningHours], start: int, end: int) -> list[tuple[int, int]]:
    """The parts of [start, end] in which a site with these hours is open; all of it for a private address. A site that closes at 19:00 is last open at 18:59."""
    if hours is None:
        return [(start, end)] if start <= end else []
    spans = []
    for day in range(start // DAY, end // DAY + 1):
        weekday = day % 7
        if weekday in hours["weekdays"]:
            opens, closes = hours["opens"], hours["closes"]
        elif weekday == 5 and hours.get("saturday"):
            opens, closes = hours["saturday"]["opens"], hours["saturday"]["closes"]
        else:
            continue
        a, b = max(start, day * DAY + opens), min(end, day * DAY + closes - 1)
        if a <= b:
            spans.append((a, b))
    return spans


class Atlas:
    """Road km and minutes for every pair of places, and straight-line km between them."""

    def __init__(self, world_map: WorldMap):
        self.places = {p["id"]: p for p in world_map["places"]}
        self.minutes = {(r["from"], r["to"]): r["minutes"] for r in world_map["roads"]}
        self.km = {(r["from"], r["to"]): r["km"] for r in world_map["roads"]}

    def drive(self, a: str, b: str) -> int:
        return self.minutes[(a, b)]

    def crow_km(self, a: str, b: str) -> float:
        """Straight-line km between two places: what the app and the rules measure nearness in."""
        p, q = self.places[a], self.places[b]
        lat1, lat2 = math.radians(p["lat"]), math.radians(q["lat"])
        dlat, dlon = lat2 - lat1, math.radians(q["lon"] - p["lon"])
        h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        return 2 * 6371 * math.asin(math.sqrt(h))
