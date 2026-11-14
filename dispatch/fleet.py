"""The driver side: the gigs an order should have in the drivers' app, and their fees."""
from __future__ import annotations

import random
from dataclasses import dataclass, replace
from typing import Optional

from spread.types import Audience, DeliveryOption, FeeStep, PriceRequest, StopRef

from . import notes
from .atlas import DAY, HOUR, Atlas, open_spans
from .books import Books, OrderState
from .notes import NoteFacts

MAX_PLAN_MINUTES = 12 * HOUR  # a gig with several cars may not plan more driving (RULES.md)
CHARGING = 40  # minutes of a charging stop (RULES.md)
RETRY = 2 * HOUR  # after a failed visit whose cause no note gave: how far to move the next one


@dataclass
class FleetPolicy:
    fee: float = 1.15  # the one fee of a gig, as a multiple of the typical fee: flat, so drivers never learn to wait
    urgent_fee: float = 1.6  # after the deadline warning
    late_fee: float = 1.3  # once the car can only arrive late
    min_slack: float = 8.0  # hours from the dealer's answer to the last possible pickup, below which we do not want the car
    decline: tuple[str, ...] = ("private_pickup", "trade_in", "premium")  # kinds of request we do not want
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

    def cost(self, request: PriceRequest, option: DeliveryOption) -> Optional[int]:
        """What we expect to pay, in cents, to move this request by this option's deadline; None when we should not win it."""
        policy, leg = self.policy, request["legs"][0]
        kinds = {"private_pickup": leg["pickup"]["privateAddress"], "trade_in": len(request["legs"]) > 1, "premium": any(l["car"]["premium"] for l in request["legs"])}
        if any(kinds[kind] for kind in policy.decline):
            return None
        last = self.last_pickup(request, option)
        if last is None or last - request["respondBy"] < policy.min_slack * HOUR:
            return None
        return int(request["referenceFeeCents"] * policy.fee)

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

    def plan(self, state: OrderState, legs: list[int]) -> list[GigPlan]:
        """The gigs that should carry these legs of the order now."""
        groups = [legs] if len(legs) == 1 or self.drive_minutes(state, legs) <= MAX_PLAN_MINUTES else [[leg] for leg in legs]
        return [GigPlan(group, self.stops(state, group), self.audience(state, group), self.schedule(state, group)) for group in groups]

    def drive_minutes(self, state: OrderState, legs: list[int]) -> int:
        places = [state.order["legs"][leg][end]["placeId"] for leg in legs for end in ("pickup", "delivery")]
        return sum(self.atlas.drive(a, b) for a, b in zip(places, places[1:]))

    def fee_multiple(self, state: OrderState) -> float:
        policy = self.policy
        if state.late:
            return policy.late_fee
        if state.urgent:
            return policy.urgent_fee
        return random.Random(f"{policy.seed}:{state.id}").choice(policy.explore) if policy.explore else policy.fee

    def schedule(self, state: OrderState, legs: list[int]) -> list[FeeStep]:
        typical = state.request["referenceFeeCents"] * len(legs) / len(state.order["legs"])
        return [{"at": self.books.now, "feeCents": max(1, int(typical * self.fee_multiple(state) + 0.5))}]

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
