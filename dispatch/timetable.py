"""When a car can be collected and by when it must arrive: the hours a site and a note leave, the chances an order has left, its gig's stops and windows."""
from __future__ import annotations

from dataclasses import replace
from typing import Iterable, Optional

from spread.types import DeliveryOption, Leg, OpeningHours, PriceRequest, StopPlace, StopRef, TimeWindow

from .atlas import DAY, HOUR, Atlas, next_business_day, open_spans
from .books import Books, OrderState
from .notes import NoteFacts

MAX_PLAN_MINUTES = 12 * HOUR  # a gig with several cars may not plan more driving (RULES.md)
CHARGING = 40  # minutes of a charging stop (RULES.md)
RETRY = 2 * HOUR  # after a failed visit whose cause no note gave: how far to move the next one (set by hand)
END = 9 * DAY + 22 * HOUR  # the world ends on the second Wednesday at 22:00
MIN_SPAN = HOUR  # a chance shorter than this finds no driver: take the next one
SLOW_DRIVE = 15  # percent by which a real drive exceeds the map's minutes one time in twenty (tools/drive_times.py)

Span = tuple[int, int]


def real(hours: Optional[OpeningHours], opens: Optional[int], closes: Optional[int]) -> Optional[OpeningHours]:
    """A site's stated hours cut to the real weekday hours of a note; drivers plan by the stated ones."""
    if hours is None:
        return None
    return {**hours, "opens": max(hours["opens"], opens or 0), "closes": min(hours["closes"], DAY if closes is None else closes)}


def arrive_by(delivery: StopPlace, facts: NoteFacts, deadline: int) -> Optional[int]:
    """The last minute at which the car arrives on time: by the note's deadline, with the delivery site really open."""
    due = deadline if facts.deadline is None else min(deadline, facts.deadline)
    return max((b for _, b in open_spans(real(delivery["hours"], facts.delivery_opens, facts.delivery_closes), delivery["window"]["from"], due)), default=None)


def collect_spans(pickup: StopPlace, facts: NoteFacts, start: int, end: int, snow: Iterable[Span] = ()) -> list[Span]:
    """The parts of [start, end] in which the car can be collected: ready, released, the site really open, no snow on summer tyres."""
    start = max(start, pickup["window"]["from"], facts.ready_at or 0, facts.released_at or 0)
    spans = open_spans(real(pickup["hours"], facts.pickup_opens, facts.pickup_closes), start, end)
    for snow_from, snow_to in snow if facts.summer_tyres else ():
        spans = [(a, b) for lo, hi in spans for a, b in ((lo, min(hi, snow_from - 1)), (max(lo, snow_to), hi)) if a <= b]
    return spans


def chances(request: PriceRequest, option: DeliveryOption, facts: NoteFacts, drive: int) -> list[Span]:
    """When a request's first car can really be collected and still arrive on time for this option. The last minute of the last
    span is the true `lastPickupAt`: a late ready time, a note deadline or an early closing shrink the slack the request shows."""
    leg = request["legs"][0]
    moved = DAY * max(0, (facts.ready_at or 0) // DAY - leg["pickup"]["window"]["from"] // DAY)  # a car ready days later moves its deadline by the same days
    arrive = arrive_by(leg["delivery"], facts, option["deadline"] + moved)
    return [] if arrive is None else collect_spans(leg["pickup"], facts, request["respondBy"], min(arrive - drive, leg["pickup"]["window"]["to"] + moved))


def windows(leg: Leg, facts: NoteFacts, deadline: int, drive: int, now: int, snow: Iterable[Span] = ()) -> tuple[Optional[TimeWindow], Optional[TimeWindow]]:
    """The windows that a gig's pickup and delivery need so that the driver meets the car ready, both sites really open and
    the note's deadline; None where the order's own window already says so. A stop has one window and real hours repeat daily,
    so a pickup with shorter real hours gets one day's chance: when it passes unbooked the gig expires, and the next post takes the next."""
    pickup, delivery = leg["pickup"], leg["delivery"]
    arrive, first, second, spans = arrive_by(delivery, facts, deadline), None, None, []
    earlier = arrive is not None and not delivery["privateAddress"] and arrive < arrive_by(delivery, NoteFacts(), deadline)
    for spare in () if arrive is None else (drive * SLOW_DRIVE // 100, 0) if earlier else (0,):
        last = min(arrive - spare - drive, pickup["window"]["to"])  # the last minute to collect the car and be on time
        spans = collect_spans(pickup, facts, now, last, snow)
        if spans and earlier:  # the note ends the delivery before the order's window does: our window says so, with room for a slow drive if there is any
            second = {"from": delivery["window"]["from"], "to": arrive - spare}
        if spans:
            break
    if not spans:  # the car can only arrive late: collect it at the first real chance, deliver without a window
        last = END
        spans = collect_spans(pickup, facts, now, last, snow)
    # fewer chances than the stated hours show:
    if spans and not pickup["privateAddress"] and spans != open_spans(pickup["hours"], max(now, pickup["window"]["from"]), last):
        if spans != open_spans(pickup["hours"], spans[0][0], last):  # and gaps that no driver can see: one chance of a useful length
            spans = [next((span for span in spans if span[1] - span[0] >= MIN_SPAN), max(spans, key=lambda span: span[1] - span[0]))]
        first = {"from": spans[0][0], "to": spans[-1][1]}
    return first, second


class Timetable:
    """The cars of our orders against those hours: the stops of a gig with their windows, and when an order's car can still be collected."""

    def __init__(self, books: Books, atlas: Atlas):
        self.books, self.atlas = books, atlas

    def gigs(self, state: OrderState, legs: list[int]) -> list[tuple[list[int], list[StopRef]]]:
        """These legs of an order as gigs, each with its stops: one gig, or one for each car when together they would plan more driving than a gig may."""
        groups = [legs] if len(legs) == 1 or self.drive_minutes(state, legs) <= MAX_PLAN_MINUTES else [[leg] for leg in legs]
        return [(group, self.timed(state, self.stops(state, group))) for group in groups]

    def stops(self, state: OrderState, legs: list[int]) -> list[StopRef]:
        """A pickup and a delivery for each leg. A stop gets a window of its own only where the note, a failed visit or snow narrow the order's."""
        order, stops = state.order, []
        for number in legs:
            leg, facts = order["legs"][number], self.facts(state, number)
            pickup: StopRef = {"orderId": order["id"], "leg": number, "kind": "pickup", "withPlates": facts.plates, "withCharging": self.charges(leg)}
            delivery: StopRef = {"orderId": order["id"], "leg": number, "kind": "delivery"}
            snow = [(start, end) for start, end, places in self.books.snow if places & {leg["pickup"]["placeId"], leg["delivery"]["placeId"]}]
            narrowed = windows(leg, facts, order["deadline"], self.road(leg), self.books.now, snow)
            for stop, window in zip((pickup, delivery), narrowed):
                if window and not state.refusals:  # the world refused our windows once: post without them
                    stop["window"] = window
            stops += [pickup, delivery]
        return stops

    def timed(self, state: OrderState, stops: list[StopRef]) -> list[StopRef]:
        """Ends a gig's windows at the next minute where arriving later costs more. Past it the world expires the gig, and we post the car for the next step."""
        if state.refusals:  # the world refused our windows once: post without them
            return stops
        for pickup, delivery in zip(stops[::2], stops[1::2]):
            leg = state.order["legs"][pickup["leg"]]
            start, due = pickup.get("window", leg["pickup"]["window"])["from"], delivery.get("window", {"to": state.order["deadline"]})["to"]
            collect, arrive = self.rung(leg, start, due)
            if collect and not leg["pickup"]["privateAddress"] and not leg["delivery"]["privateAddress"]:
                pickup["window"] = {"from": start, "to": min(collect, pickup.get("window", {"to": collect})["to"])}
                delivery["window"] = {"from": delivery.get("window", leg["delivery"]["window"])["from"], "to": arrive}
        return stops

    def rung(self, leg: Leg, start: int, due: int) -> tuple[Optional[int], Optional[int]]:
        """The last minutes to collect and to deliver a car so that it arrives by its due minute or, once that is out of reach,
        by the next rung of the refund ladder: 10%, 25%, 50% back (RULES.md)."""
        now, drive = self.books.now, self.road(leg)
        next_day = next_business_day(due // DAY) * DAY + due % DAY
        for by in (due, due + 2 * HOUR, next_day, next_business_day(next_day // DAY) * DAY + due % DAY):
            arrive = max((b for a, b in open_spans(leg["delivery"]["hours"], max(now, start) + drive, by)), default=None)
            collect = arrive and max((b for a, b in open_spans(leg["pickup"]["hours"], max(now, start), arrive - drive)), default=None)
            if collect and collect >= now + 30:  # a rung still in reach: its last minute to collect is half an hour away or more
                return collect, arrive
        return None, None

    def chances_left(self, state: OrderState) -> list[Span]:
        """When an order's first car can still be collected, from now on, and arrive on time: `chances` asks the same of a request before it is won."""
        leg, facts = state.order["legs"][0], self.facts(state, 0)
        arrive = arrive_by(leg["delivery"], facts, state.order["deadline"])
        return [] if arrive is None else collect_spans(leg["pickup"], facts, self.books.now, min(arrive - self.road(leg), leg["pickup"]["window"]["to"]))

    def facts(self, state: OrderState, leg: int) -> NoteFacts:
        """What we know of a car: the note's facts (a note speaks of the first car), then what the world has told us since."""
        facts = replace(state.facts) if leg == 0 else NoteFacts()
        reason, at = state.failed.get(leg, ("", 0))
        if leg in state.released:  # the dealer has been paid
            facts.released_at = state.released[leg]
        if reason == "not_ready":
            facts.ready_at = max(facts.ready_at or 0, at + RETRY)
        elif reason == "closed" and at % DAY < 12 * HOUR:  # closed in the morning: it opens later than we thought
            facts.pickup_opens = at % DAY + RETRY
        elif reason == "closed":  # closed in the afternoon: it closes earlier
            facts.pickup_closes = at % DAY - RETRY
        facts.plates, facts.manual = facts.plates or reason == "no_plates", facts.manual or reason == "licence"
        return facts

    def road(self, leg: Leg) -> int:
        """Minutes from a leg's pickup to its delivery by the map, with the charging stop of a car that needs one."""
        return self.atlas.drive(leg["pickup"]["placeId"], leg["delivery"]["placeId"]) + CHARGING * self.charges(leg)

    def charges(self, leg: Leg) -> bool:
        """True for an electric car that needs a charging stop on its way: under 30% charge on a route over 200 km (RULES.md)."""
        car, ends = leg["car"], (leg["pickup"]["placeId"], leg["delivery"]["placeId"])
        return bool(car["electric"] and car["chargePercent"] is not None and car["chargePercent"] < 30 and self.atlas.km[ends] > 200)

    def drive_minutes(self, state: OrderState, legs: list[int]) -> int:
        """The road minutes of one gig for these legs in a row, as the rules count a gig's driving."""
        places = [state.order["legs"][leg][end]["placeId"] for leg in legs for end in ("pickup", "delivery")]
        return sum(self.atlas.drive(a, b) for a, b in zip(places, places[1:]))
