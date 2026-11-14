"""The driver side: the chance that a car arrives on time, the fee that buys that chance cheapest, and so what the car costs us."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Optional

from spread.types import Audience, DeliveryOption, FeeStep, PriceRequest, StopRef

from . import notes
from .atlas import DAY, HOUR, Atlas, next_business_day, open_spans
from .books import Books, GigState, OrderState
from .notes import NoteFacts

MAX_PLAN_MINUTES = 12 * HOUR  # a gig with several cars may not plan more driving (RULES.md)
CHARGING = 40  # minutes of a charging stop (RULES.md)
RETRY = 2 * HOUR  # after a failed visit whose cause no note gave: how far to move the next one
NEAR_KM = 30  # the app notifies drivers who live this close to the pickup (RULES.md)
# What tools/fleet_fit.py measures on our own weeks. ON_TIME: logistic weights of "the car arrives on time".
ON_TIME = {
    "one": -1.06, "fee": 1.98, "slack": 1.28, "short": -1.42, "long": -0.55, "note": -0.48, "private_pickup": 0.60, "private_delivery": -0.33, "premium": -1.08, "trade_in": -1.80,
    "drivers_pickup": 0.17, "drivers_delivery": 0.16, "backlog": -0.66,
}
WAIT = (1.08, 5.57)  # hours that a car waits for a driver while requests arrive: a base, and more per unit of its chance of being late
CROWDING = 0.034  # other orders that arrive late for each hour that a car waits: the same cars under a heavier and a lighter book


@dataclass
class FleetPolicy:
    fees: tuple[float, ...] = (0.85, 1.0, 1.15, 1.3, 1.5)  # the fees a gig may open at, as multiples of the typical fee
    urgent_fee: float = 1.6  # after the deadline warning
    late_fee: float = 1.3  # once the car can only arrive late
    on_time: float = 0.95  # the share of orders we want on time: the delivery minimum with room to spare
    late_price: float = 300.0  # euros that a late order costs us beyond its refund while we are within that share
    grip: float = 4.0  # how steeply that price rises once we expect more late orders than the share allows
    refund: float = 0.5  # what a late order pays back on average, as a share of the list price
    booked_late: float = 0.05  # the share of cars with a driver that still arrive late: drops, failed visits, slow drives
    crowding: float = 1.0  # research: how much of the measured crowding we charge
    ladder: bool = False  # give each gig windows that end at the deadline, and a late car's at the next step of the refund ladder
    buffer: float = 0.0  # the share of the drive, plus a quarter of an hour, that those windows end before the site closes
    explore: Optional[tuple[float, ...]] = None  # research: draw each order's fee multiple from these
    seed: str = ""


@dataclass
class GigPlan:
    legs: list[int]
    stops: list[StopRef]
    audience: Audience
    schedule: list[FeeStep]


class Fleet:
    def __init__(self, policy: FleetPolicy, books: Books, atlas: Atlas):
        self.policy, self.books, self.atlas = policy, books, atlas
        homes = [driver.profile["homePlaceId"] for driver in books.drivers.values()]
        self.drivers_near = {place: sum(1 for home in homes if atlas.crow_km(home, place) <= NEAR_KM) for place in atlas.places}
        self.held = lambda state: False  # the desk's pairs say which orders we keep out of the app ourselves: no driver has turned those down

    def cost(self, request: PriceRequest, option: DeliveryOption) -> Optional[int]:
        """What we expect to pay, in cents, to move this request by this option's deadline: the fee, the late car's refund, its use of the room under the delivery minimum, and the orders it makes late while it waits."""
        last = self.last_pickup(request, option)
        if last is None:
            return None
        waiting = self.waiting()
        policy, typical = self.policy, request["referenceFeeCents"]
        late_price, refund = self.late_price(waiting), policy.refund * option["listPriceCents"]
        hour = self.waiting_hour(refund)
        multiple, late = self.fee(self.signs(request, last, request["respondBy"], len(waiting)), typical, refund + late_price + WAIT[1] * hour)
        risk = late * refund + (late - (1 - policy.on_time)) * late_price + (WAIT[0] + WAIT[1] * late) * hour
        return int(typical * multiple + max(0.0, risk))

    def waiting_hour(self, refund: float) -> float:
        """What an hour of a car's waiting costs, in cents: the orders it makes late, at the price of a late order."""
        return self.policy.crowding * CROWDING * (refund + self.policy.late_price * 100)

    def late_price(self, waiting: list[OrderState], calm: int = 20) -> float:
        """The shadow price, in cents, of one late order: it rises steeply once we expect more late orders than the minimum leaves room for."""
        books, policy, late = self.books, self.policy, 0.0
        for state in books.orders.values():
            if state.undelivered():
                late += 1.0 if state.late else policy.booked_late
            else:
                late += state.id in books.refunded
        for state in waiting:  # a car without a driver: the model's chance, at its fee and with the time it has left
            late += 1 - self.on_time(self.signs(state.request, state.order["lastPickupAt"], books.now, len(waiting) - 1), self.posted(state) or 1.0) - policy.booked_late
        share = late / (calm + len(books.orders))  # the first orders of a week say little
        return policy.late_price * 100 * min(2.0, max(1.0, share / (1 - policy.on_time))) ** policy.grip

    def needs_driver(self, state: OrderState) -> bool:
        return any(leg not in state.gig_of or self.books.gigs[state.gig_of[leg]].status == "open" for leg in state.undelivered())

    def waiting(self) -> list[OrderState]:
        """The orders that wait for a driver now: what the drivers are not taking."""
        return [state for state in self.books.orders.values() if not state.late and self.needs_driver(state) and not self.held(state)]

    def signs(self, request: PriceRequest, last_pickup: int, at: int, backlog: int) -> dict[str, float]:
        """What we know at minute `at` about how easily this request finds a driver in time."""
        leg = request["legs"][0]
        pickup, delivery = leg["pickup"], leg["delivery"]
        km = self.atlas.km[(pickup["placeId"], delivery["placeId"])]
        return {
            "one": 1.0,
            "slack": math.log1p(max(0, last_pickup - at) / HOUR),
            "short": float(km < 40),
            "long": min(max(km, 250), 800) / 100 - 2.5,
            "note": float(bool(request["note"])),
            "private_pickup": float(pickup["privateAddress"]),
            "private_delivery": float(delivery["privateAddress"]),
            "premium": float(any(l["car"]["premium"] for l in request["legs"])),
            "trade_in": float(len(request["legs"]) > 1),
            "drivers_pickup": math.log1p(self.drivers_near[pickup["placeId"]]),
            "drivers_delivery": math.log1p(self.drivers_near[delivery["placeId"]]),
            "backlog": math.log1p(backlog),
        }

    def on_time(self, signs: dict[str, float], multiple: float) -> float:
        """The chance that the car arrives on time when its gig pays this multiple of the typical fee."""
        return 1 / (1 + math.exp(-sum(ON_TIME[name] * value for name, value in signs.items()) - ON_TIME["fee"] * (multiple - 1)))

    def fee(self, signs: dict[str, float], typical: float, late_cost: float, floor: float = 0.0) -> tuple[float, float]:
        """The fee multiple that minimises the fee plus the expected cost of a late car, and the chance of a late car at that fee."""
        multiple = min((m for m in self.policy.fees if m >= floor), key=lambda m: m * typical + (1 - self.on_time(signs, m)) * late_cost, default=floor)
        return multiple, 1 - self.on_time(signs, multiple)

    def last_pickup(self, request: PriceRequest, option: DeliveryOption) -> Optional[int]:
        """The last minute to collect the first car and still deliver it by the option's deadline, by road minutes and stated hours."""
        leg = request["legs"][0]
        pickup, delivery = leg["pickup"], leg["delivery"]
        drive = self.atlas.drive(pickup["placeId"], delivery["placeId"])
        due = min(option["deadline"], delivery["window"]["to"]) if delivery["privateAddress"] else option["deadline"]
        arrive = max((b for a, b in open_spans(delivery["hours"], delivery["window"]["from"], due)), default=None)
        if arrive is None:
            return None
        end = min(arrive - drive, pickup["window"]["to"])
        return max((b for a, b in open_spans(pickup["hours"], pickup["window"]["from"], end)), default=None)

    def list_price(self, state: OrderState) -> int:
        return next(option["listPriceCents"] for option in state.request["options"] if option["kind"] == state.order["option"])

    def open_gig(self, state: OrderState, leg: int) -> Optional[GigState]:
        gig = self.books.gigs.get(state.gig_of.get(leg, ""))
        return gig if gig and gig.status == "open" and not gig.shared else None  # a two-car gig's fee is not this order's own

    def posted(self, state: OrderState) -> float:
        """The multiple of its typical fee that the order's open gig shows in the app; 0 when it has none."""
        gig = self.open_gig(state, state.undelivered()[0])
        return gig.schedule[-1]["feeCents"] / state.request["referenceFeeCents"] * len(state.order["legs"]) / len(gig.legs) if gig else 0.0

    def plan(self, state: OrderState, legs: list[int]) -> list[GigPlan]:
        """The gigs that should carry these legs of the order now."""
        groups = [legs] if len(legs) == 1 or self.drive_minutes(state, legs) <= MAX_PLAN_MINUTES else [[leg] for leg in legs]
        return [GigPlan(group, self.timed(state, self.stops(state, group)), self.audience(state, group), self.schedule(state, group)) for group in groups]

    def drive_minutes(self, state: OrderState, legs: list[int]) -> int:
        places = [state.order["legs"][leg][end]["placeId"] for leg in legs for end in ("pickup", "delivery")]
        return sum(self.atlas.drive(a, b) for a, b in zip(places, places[1:]))

    def timed(self, state: OrderState, stops: list[StopRef]) -> list[StopRef]:
        """Ends a gig's windows at the next minute where arriving later costs more: the deadline, then each step of the refund ladder. Past it the world expires the gig, and we post the car for the next step."""
        policy, now = self.policy, self.books.now
        for pickup, delivery in zip(stops[::2], stops[1::2]) if policy.ladder else []:
            leg = state.order["legs"][pickup["leg"]]
            if leg["pickup"]["privateAddress"] or leg["delivery"]["privateAddress"]:
                continue
            drive = self.atlas.drive(leg["pickup"]["placeId"], leg["delivery"]["placeId"])
            spare = int(policy.buffer * drive) + 15 if policy.buffer else 0  # real drives run longer than the map, and a driver plans to the last minute
            start, due = pickup.get("window", leg["pickup"]["window"])["from"], delivery.get("window", {"to": state.order["deadline"]})["to"]
            next_day = next_business_day(due // DAY) * DAY + due % DAY
            for step in (due, due + 2 * HOUR, next_day, next_business_day(next_day // DAY) * DAY + due % DAY):  # on time, then 10%, 25%, 50% back (RULES.md)
                arrive = max((b for a, b in open_spans(leg["delivery"]["hours"], max(now, start) + drive, step)), default=None)
                collect = arrive and max((b for a, b in open_spans(leg["pickup"]["hours"], max(now, start), arrive - spare - drive)), default=None)
                if collect and collect >= now + 30:
                    pickup["window"] = {"from": start, "to": min(collect, pickup.get("window", {"to": collect})["to"])}
                    delivery["window"] = {"from": delivery.get("window", leg["delivery"]["window"])["from"], "to": arrive - spare}
                    break
        return stops

    def fee_multiple(self, state: OrderState, legs: list[int], typical: float) -> float:
        """One fee for as long as a gig waits, so drivers never learn to wait: chosen when the order needs a driver, and again only when it loses one or its deadline warning comes."""
        policy, gig = self.policy, self.open_gig(state, legs[0])
        posted = gig.schedule[-1]["feeCents"] / typical if gig else 0.0
        if state.late:
            return policy.late_fee
        if gig and gig.schedule[-1]["at"] >= state.alarm_at:
            return posted
        if state.urgent:
            return max(posted, policy.urgent_fee)
        if policy.explore and not posted:
            return random.Random(f"{policy.seed}:{state.id}").choice(policy.explore)
        waiting, refund = self.waiting(), policy.refund * self.list_price(state)
        late_cost = refund + self.late_price(waiting) + WAIT[1] * self.waiting_hour(refund)
        return self.fee(self.signs(state.request, state.order["lastPickupAt"], self.books.now, max(0, len(waiting) - 1)), typical, late_cost, floor=posted)[0]

    def schedule(self, state: OrderState, legs: list[int]) -> list[FeeStep]:
        typical = state.request["referenceFeeCents"] * len(legs) / len(state.order["legs"])
        return [{"at": self.books.now, "feeCents": max(1, int(typical * self.fee_multiple(state, legs, typical) + 0.5))}]

    def audience(self, state: OrderState, legs: list[int]) -> Audience:
        premium = any(state.order["legs"][leg]["car"]["premium"] for leg in legs)
        licence = state.facts.manual or any(state.failed.get(leg, ("", 0))[0] == "licence" for leg in legs)
        return {"experienced": premium, "manualLicence": licence}

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

    def stops(self, state: OrderState, legs: list[int]) -> list[StopRef]:
        """A pickup and a delivery for each leg. A stop gets a window of its own only where the note, a failed visit or snow narrow the order's."""
        order, books, stops = state.order, self.books, []
        for leg in legs:
            car, pickup, delivery = order["legs"][leg]["car"], order["legs"][leg]["pickup"], order["legs"][leg]["delivery"]
            ends, facts = (pickup["placeId"], delivery["placeId"]), self.facts(state, leg)
            charging = bool(car["electric"] and car["chargePercent"] is not None and car["chargePercent"] < 30 and self.atlas.km[ends] > 200)
            first: StopRef = {"orderId": order["id"], "leg": leg, "kind": "pickup", "withPlates": facts.plates, "withCharging": charging}
            second: StopRef = {"orderId": order["id"], "leg": leg, "kind": "delivery"}
            snow = [(start, end) for start, end, places in books.snow if places & set(ends)]
            windows = notes.windows(order["legs"][leg], facts, order["deadline"], self.atlas.drive(*ends) + CHARGING * charging, books.now, snow)
            for stop, window in zip((first, second), windows):
                if window and not state.refusals:  # the world refused our windows once: post without them
                    stop["window"] = window
            stops += [first, second]
        return stops
