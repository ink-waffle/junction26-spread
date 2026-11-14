"""The driver side: the chance that a car arrives on time, the fee that buys that chance cheapest, and so what the car costs us."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Optional

from spread.types import Audience, DeliveryOption, FeeStep, Leg, PriceRequest, StopRef

from . import notes
from .atlas import DAY, HOUR, Atlas, next_business_day, open_spans
from .books import Books, GigState, OrderState
from .notes import NoteFacts, Span

MAX_PLAN_MINUTES = 12 * HOUR  # a gig with several cars may not plan more driving (RULES.md)
CHARGING = 40  # minutes of a charging stop (RULES.md)
RETRY = 2 * HOUR  # after a failed visit whose cause no note gave: how far to move the next one
NEAR_KM = 30  # the app notifies drivers who live this close to the pickup (RULES.md)
# What tools/fleet_fit.py measures on our own weeks. ON_TIME: logistic weights of "the car arrives on time".
# "fee" weighs a gig's fee against the fees of our other open gigs, "level" the fee that our open gigs pay together: drivers choose among our gigs.
ON_TIME = {"one": -0.80, "fee": 3.82, "level": 1.33, "slack": 1.11, "short": -1.50, "long": -0.54, "premium": -1.29, "trade_in": -3.21, "drivers_delivery": 0.27, "backlog": -0.45}
BOOKED_LATE = 0.035  # the share of cars with a driver that still arrive late: drops and slow drives
REFUND = 0.55  # what a late order pays back on average, as a share of its list price
DOUBT = 4.0  # how firmly we hold, before a week's own outcomes speak, that its world is the model's: the prior's weight, in outcomes
GRIP = 4  # how steeply the price of a late order rises once we expect more of them than we allow ourselves
CALM = 20  # orders: a week's first orders say little about its share of late ones


@dataclass
class FleetPolicy:
    fees: tuple[float, ...] = (0.85, 1.0, 1.15, 1.3, 1.5)  # the fees a gig may open at, as multiples of the typical fee
    urgent_fee: float = 1.6  # after the deadline warning
    on_time: float = 0.94  # the share of orders we want on time: the delivery minimum with room to spare
    late_price: float = 300.0  # euros that a late order costs us beyond its refund while we are within that share
    crowding: float = 1.0  # research: how much of the harm to the waiting cars we charge
    explore: Optional[tuple[float, ...]] = None  # research: draw each order's fee multiple from these
    seed: str = ""


@dataclass
class GigPlan:
    legs: list[int]
    stops: list[StopRef]
    audience: Audience
    schedule: list[FeeStep]


@dataclass
class Queue:
    """The orders that wait for a driver now: what the drivers are not taking."""
    backlog: int = 0  # how many they are
    going: float = 1.0  # the fee their gigs show, as a mean multiple of the typical fee
    late: float = 0.0  # how many of them we expect to arrive late
    stake: float = 0.0  # what a step of one logit in all their chances is worth, in cents

    def level(self, multiple: float) -> float:
        """The going fee once a gig at this multiple joins the queue."""
        return (self.backlog * self.going + multiple) / (self.backlog + 1)


class Fleet:
    def __init__(self, policy: FleetPolicy, books: Books, atlas: Atlas):
        self.policy, self.books, self.atlas = policy, books, atlas
        homes = [driver.profile["homePlaceId"] for driver in books.drivers.values()]
        self.drivers_near = {place: sum(1 for home in homes if atlas.crow_km(home, place) <= NEAR_KM) for place in atlas.places}
        self.forecast: dict[str, float] = {}  # order -> the model's logit when we posted it: what this week's outcomes are measured against
        self.world = 0.0  # how much easier (+) or harder than the model's this week's world has shown itself, in logits

    def cost(self, request: PriceRequest, option: DeliveryOption) -> Optional[int]:
        """What we expect to pay, in cents, to move this request by this option's deadline: the fee, the late car's refund, its use of the room under the delivery minimum, and what it does to the cars that wait for a driver."""
        spans = notes.chances(request, option, notes.read(request["note"], request["arrivedAt"]), self.road(request["legs"][0]))
        if not spans:
            return None
        queue = self.queue()
        typical, refund, late_price = request["referenceFeeCents"], REFUND * option["listPriceCents"], self.late_price(queue)
        multiple, late = self.fee(self.signs(request, spans, request["respondBy"], queue.backlog), typical, refund + late_price, queue)
        risk = late * refund + (late - (1 - self.policy.on_time)) * late_price + self.harm(multiple, queue)
        return int(typical * multiple + max(0.0, risk))

    def queue(self, but: Optional[OrderState] = None) -> Queue:
        """The orders that wait for a driver now, but for one: how many, at what fee, with what chances."""
        books, policy = self.books, self.policy
        waiting = [(state, self.posted(state) or 1.0) for state in books.orders.values() if state is not but and not state.late and self.needs_driver(state)]
        queue = Queue(len(waiting), sum(multiple for _, multiple in waiting) / max(1, len(waiting)))
        logits = {}
        for state, multiple in waiting:
            others = Queue(queue.backlog - 1, (queue.going * queue.backlog - multiple) / max(1, queue.backlog - 1))
            logits[state.id] = self.logit(self.signs(state.request, self.chances(state), books.now, others.backlog), multiple, others)
        self.world = self.learned(logits)
        for state, _ in waiting:
            on_time = 1 / (1 + math.exp(-logits[state.id] - self.world))
            queue.late += 1 - on_time
            queue.stake += on_time * (1 - on_time) * (REFUND * self.list_price(state) + policy.late_price * 100)
        return queue

    def learned(self, waiting: dict[str, float]) -> float:
        """The intercept that best explains this week's own orders against what the model said when we posted each: this world's drivers, as far as they have shown themselves.
        An order with a driver counts as almost on time, a waiting one as the model sees it now, a late or delivered one as it ended."""
        books, seen = self.books, []
        for order_id, logit in self.forecast.items():
            state = books.orders.get(order_id)
            if state is None or state.undelivered() and not state.late and self.needs_driver(state) and order_id not in waiting:
                continue
            outcome = 0.0 if state.late else 1 / (1 + math.exp(-waiting[order_id])) if order_id in waiting else 1 - BOOKED_LATE if state.undelivered() else float(order_id not in books.refunded)
            seen.append((logit, outcome))
        shift = 0.0
        for _ in range(4):  # Newton's method on one number, from a prior that the world is the model's
            chances = [1 / (1 + math.exp(-logit - shift)) for logit, _ in seen]
            shift += (sum(outcome - chance for (_, outcome), chance in zip(seen, chances)) - DOUBT * shift) / (sum(chance * (1 - chance) for chance in chances) + DOUBT)
        return max(-1.0, min(1.0, shift))

    def needs_driver(self, state: OrderState) -> bool:
        return any(leg not in state.gig_of or self.books.gigs[state.gig_of[leg]].status == "open" for leg in state.undelivered())

    def late_price(self, queue: Queue) -> float:
        """The shadow price, in cents, of one late order: it rises steeply once the books expect more late orders than we allow ourselves."""
        books, late = self.books, queue.late - BOOKED_LATE * queue.backlog
        for state in books.orders.values():
            late += (1.0 if state.late else BOOKED_LATE) if state.undelivered() else state.id in books.refunded
        share = late / (CALM + len(books.orders))
        return self.policy.late_price * 100 * min(2.0, max(1.0, share / (1 - self.policy.on_time))) ** GRIP

    def harm(self, multiple: float, queue: Queue) -> float:
        """What one more gig at this fee costs the cars that wait, in cents: it lengthens the queue, and a fee above theirs draws their drivers."""
        outbid = (ON_TIME["fee"] - ON_TIME["level"]) * math.log(queue.level(multiple) / queue.going) if queue.backlog else 0.0
        return self.policy.crowding * queue.stake * (outbid - ON_TIME["backlog"] / (1 + queue.backlog))

    def chances(self, state: OrderState) -> list[Span]:
        """When an order's first car can still be collected, from now on, and arrive on time."""
        leg, facts = state.order["legs"][0], self.facts(state, 0)
        arrive = notes.arrive_by(leg["delivery"], facts, state.order["deadline"])
        return [] if arrive is None else notes.collect_spans(leg["pickup"], facts, self.books.now, min(arrive - self.road(leg), leg["pickup"]["window"]["to"]))

    def signs(self, request: PriceRequest, spans: list[Span], at: int, backlog: int) -> dict[str, float]:
        """What we know at minute `at` about how easily this request finds a driver in time, given when its car can be collected."""
        leg = request["legs"][0]
        km = self.atlas.km[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])]
        return {
            "one": 1.0,
            "slack": math.log1p(max(0, max((b for _, b in spans), default=at) - at) / HOUR),
            "short": float(km < 40),
            "long": min(max(km, 250), 800) / 100 - 2.5,
            "premium": float(any(l["car"]["premium"] for l in request["legs"])),
            "trade_in": float(len(request["legs"]) > 1),
            "drivers_delivery": math.log1p(self.drivers_near[leg["delivery"]["placeId"]]),
            "backlog": math.log1p(backlog),
        }

    def logit(self, signs: dict[str, float], multiple: float, queue: Queue) -> float:
        """The model's log odds that the car arrives on time when its gig pays this multiple of the typical fee and the queue is this one."""
        level = queue.level(multiple)
        signs = dict(signs, fee=math.log(multiple / level), level=math.log(level))
        return sum(weight * signs[name] for name, weight in ON_TIME.items())

    def on_time(self, signs: dict[str, float], multiple: float, queue: Queue) -> float:
        """The chance that the car arrives on time: the model's, moved by what this week's world has shown."""
        return 1 / (1 + math.exp(-self.logit(signs, multiple, queue) - self.world))

    def fee(self, signs: dict[str, float], typical: float, late_cost: float, queue: Queue, floor: float = 0.0) -> tuple[float, float]:
        """The fee multiple that costs least in all: the fee, the expected cost of a late car, and the harm to the cars that wait. With it, the chance of a late car."""
        def total(multiple: float) -> float:
            return multiple * typical + (1 - self.on_time(signs, multiple, queue)) * late_cost + self.harm(multiple, queue)
        multiple = min((m for m in self.policy.fees if m >= floor), key=total, default=floor)
        return multiple, 1 - self.on_time(signs, multiple, queue)

    def road(self, leg: Leg) -> int:
        """Minutes from a leg's pickup to its delivery by the map, with the charging stop of an electric car that needs one."""
        car, ends = leg["car"], (leg["pickup"]["placeId"], leg["delivery"]["placeId"])
        return self.atlas.drive(*ends) + CHARGING * bool(car["electric"] and car["chargePercent"] is not None and car["chargePercent"] < 30 and self.atlas.km[ends] > 200)

    def list_price(self, state: OrderState) -> int:
        return next(option["listPriceCents"] for option in state.request["options"] if option["kind"] == state.order["option"])

    def open_gig(self, state: OrderState, leg: int) -> Optional[GigState]:
        gig = self.books.gigs.get(state.gig_of.get(leg, ""))
        return gig if gig and gig.status == "open" else None

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
        """Ends a gig's windows at the next minute where arriving later costs more. Past it the world expires the gig, and we post the car for the next step."""
        for pickup, delivery in zip(stops[::2], stops[1::2]) if not state.refusals else []:  # the world refused our windows once: post without them
            leg = state.order["legs"][pickup["leg"]]
            start, due = pickup.get("window", leg["pickup"]["window"])["from"], delivery.get("window", {"to": state.order["deadline"]})["to"]
            collect, arrive = self.step(leg, start, due)
            if collect and not leg["pickup"]["privateAddress"] and not leg["delivery"]["privateAddress"]:
                pickup["window"] = {"from": start, "to": min(collect, pickup.get("window", {"to": collect})["to"])}
                delivery["window"] = {"from": delivery.get("window", leg["delivery"]["window"])["from"], "to": arrive}
        return stops

    def step(self, leg: Leg, start: int, due: int) -> tuple[Optional[int], Optional[int]]:
        """The last minutes to collect and to deliver a car so that it arrives by its due minute or, once that is out of reach, by the next step of the refund ladder: 10%, 25%, 50% back (RULES.md)."""
        now, drive = self.books.now, self.road(leg)
        next_day = next_business_day(due // DAY) * DAY + due % DAY
        for step in (due, due + 2 * HOUR, next_day, next_business_day(next_day // DAY) * DAY + due % DAY):
            arrive = max((b for a, b in open_spans(leg["delivery"]["hours"], max(now, start) + drive, step)), default=None)
            collect = arrive and max((b for a, b in open_spans(leg["pickup"]["hours"], max(now, start), arrive - drive)), default=None)
            if collect and collect >= now + 30:
                return collect, arrive
        return None, None

    def fee_multiple(self, state: OrderState, legs: list[int], typical: float) -> float:
        """One fee for as long as a gig waits, so drivers never learn to wait: chosen when the order needs a driver, and again only when it loses one or its deadline warning comes."""
        policy, books, gig = self.policy, self.books, self.open_gig(state, legs[0])
        posted = gig.schedule[-1]["feeCents"] / typical if gig else 0.0
        if gig and gig.schedule[-1]["at"] >= state.alarm_at:
            return posted
        if state.urgent and not state.late:
            return max(posted, policy.urgent_fee)
        queue, leg = self.queue(but=state), state.order["legs"][0]
        if state.late:  # the same choice, with the next step of the refund ladder as the deadline: missing it takes about a quarter of the price more
            collect, _ = self.step(leg, leg["pickup"]["window"]["from"], state.order["deadline"])
            signs = self.signs(state.request, [(books.now, collect or books.now + DAY)], books.now, queue.backlog)
            return self.fee(signs, typical, 0.25 * state.order["priceCents"], queue)[0]
        late_cost, signs = REFUND * self.list_price(state) + self.late_price(queue), self.signs(state.request, self.chances(state), books.now, queue.backlog)
        multiple = random.Random(f"{policy.seed}:{state.id}").choice(policy.explore) if policy.explore and not posted else self.fee(signs, typical, late_cost, queue, floor=posted)[0]
        self.forecast.setdefault(state.id, self.logit(signs, multiple, queue))
        return multiple

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
