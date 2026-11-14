"""The driver side: the chance that a car arrives on time, the fee that buys that chance cheapest, and so what the car costs us."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, replace
from typing import Optional

from spread.types import Audience, DeliveryOption, FeeStep, Leg, PostAction, PriceRequest, StopRef

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
ON_TIME = {"one": -1.21, "fee": 3.96, "level": 0.88, "slack": 1.13, "short": -1.85, "long": -0.44, "premium": -0.92, "trade_in": -3.35,
           "drivers_delivery": 0.28, "backlog": -0.58, "known": 0.25, "waited": -0.75,
           "drivers_pickup": 0.0, "private_pickup": 0.0, "private_delivery": 0.0}
BOOKED_LATE = 0.030  # the share of cars with a driver that still arrive late: drops and slow drives
REFUND = 0.54  # what a late order pays back on average, as a share of its list price
DOUBT = 4.0  # how firmly we hold, before a week's own outcomes speak, that its world is the model's: the prior's weight, in outcomes
GRIP = 4  # how steeply the price of a late order rises once we expect more of them than we allow ourselves
CALM = 20  # orders: a week's first orders say little about its share of late ones
LAST_DAY = DAY  # before its last pickup: a gig still open then ends in a deadline warning two times in three (AUDIT.md)
KNOWN = 100  # bookings after which the drivers know that our fees stay as posted


@dataclass
class FleetPolicy:
    fees: tuple[float, ...] = (0.85, 1.0, 1.15, 1.3, 1.5)  # the fees a gig may open at, as multiples of the typical fee
    urgent_fee: float = 1.6  # after the deadline warning
    late_fee: float = 1.3  # once the car can only arrive late: enough for the drivers who saw it at less, or it is never delivered
    on_time: float = 0.96  # the share of orders we want on time: the delivery minimum with room for a bad week (unseen weeks end up to 5 points under it)
    late_price: float = 300.0  # euros that a late order costs us beyond its refund while we are within that share
    crowding: float = 1.0  # research: how much of the harm to the waiting cars we charge
    early_look: float = 6.0  # hours in the app after which a gig without a taker gets its fee chosen again, one step up at least; 0: only on its last day
    explore: Optional[tuple[float, ...]] = None  # research: draw each order's fee multiple from these
    spare: float = 0.0  # research: the share of the drive by which a gig's pickup window ends before the last minute
    redrop: bool = False  # research: a gig that lost its driver gets one fee step more at least
    look_every: float = 0.0  # research: hours between further looks at a gig without a taker, after the early one
    start: float = 0.0  # research: the share of its allowed late orders that a week starts at
    trade_ins: bool = True  # research: False declines every trade-in
    doubt: float = DOUBT  # research: the weight of the prior that the world is the model's
    weights: Optional[dict] = None  # research: weights of ON_TIME to replace
    last_fee: float = 0.0  # research: the least fee of a gig that begins its last day without a taker
    raises: tuple[float, ...] = ()  # research: further fees that only a gig whose fee is chosen again may get
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
    known: int = 0  # the bookings of the week so far: what the drivers have seen of us
    world: float = 0.0  # how much easier (+) or harder than the model's this week's world has shown itself, in logits
    late: float = 0.0  # how many of them we expect to arrive late
    swing: float = 0.0  # how many more of them arrive on time when all their chances rise by one logit
    refunds: float = 0.0  # the cents of refund that this saves

    def level(self, multiple: float) -> float:
        """The going fee once a gig at this multiple joins the queue."""
        return (self.backlog * self.going + multiple) / (self.backlog + 1)


class Fleet:
    def __init__(self, policy: FleetPolicy, books: Books, atlas: Atlas):
        self.policy, self.books, self.atlas = policy, books, atlas
        homes = [driver.profile["homePlaceId"] for driver in books.drivers.values()]
        self.drivers_near = {place: sum(1 for home in homes if atlas.crow_km(home, place) <= NEAR_KM) for place in atlas.places}
        self.weights = {**ON_TIME, **(policy.weights or {})}
        self.forecast: dict[str, float] = {}  # order -> the model's logit when the world took its gig: what this week's outcomes are measured against
        self.held = lambda state: False  # the desk's pairs say which orders we keep out of the app ourselves: no driver has turned those down

    def cost(self, request: PriceRequest, option: DeliveryOption) -> Optional[int]:
        """What we expect to pay, in cents, to move this request by this option's deadline: the fee, the late car's refund, its use of the room under the delivery minimum, and what it does to the cars that wait for a driver."""
        spans = notes.chances(request, option, notes.read(request["note"], request["arrivedAt"]), self.road(request["legs"][0]))
        if not spans or len(request["legs"]) > 1 and not self.policy.trade_ins:
            return None
        queue = self.queue()
        typical, refund, late_price = request["referenceFeeCents"], REFUND * option["listPriceCents"], self.late_price(queue)
        multiple, late = self.fee(self.car(request, spans, request["respondBy"]), typical, refund, late_price, queue)
        risk = late * refund + (late - (1 - self.policy.on_time)) * late_price + self.harm(multiple, queue, late_price)
        return int(typical * multiple + max(0.0, risk))

    def queue(self, but: Optional[OrderState] = None) -> Queue:
        """The orders that wait for a driver now, but for one: how many, at what fee, with what chances."""
        books, policy = self.books, self.policy
        waiting = [(state, self.posted(state) or 1.0, self.car(state.request, self.chances(state), books.now, state.won_at)) for state in books.orders.values() if state is not but and self.waits(state)]
        queue = Queue(len(waiting), sum(multiple for _, multiple, _ in waiting) / max(1, len(waiting)), sum(1 for gig in books.gigs.values() if gig.driver))
        logits = {}
        for state, multiple, car in waiting:
            others = Queue(queue.backlog - 1, (queue.going * queue.backlog - multiple) / max(1, queue.backlog - 1), queue.known)
            logits[state.id] = self.logit(car, multiple, others)
        queue.world = self.learned(logits)
        for state, _, _ in waiting:
            on_time = 1 / (1 + math.exp(-logits[state.id] - queue.world))
            queue.late += 1 - on_time
            queue.swing += on_time * (1 - on_time)
            queue.refunds += on_time * (1 - on_time) * REFUND * self.list_price(state)
        return queue

    def waits(self, state: OrderState) -> bool:
        """True for an order that the drivers can see and have not taken: not held back by us for a partner, not in a two-car gig, not late."""
        gigs = [self.books.gigs[gig_id] for gig_id in state.gig_of.values()]
        return not state.late and not self.held(state) and self.needs_driver(state) and not any(gig.shared and gig.status == "open" for gig in gigs)

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
            shift += (sum(outcome - chance for (_, outcome), chance in zip(seen, chances)) - self.policy.doubt * shift) / (sum(chance * (1 - chance) for chance in chances) + self.policy.doubt)
        return max(-1.0, min(1.0, shift))

    def needs_driver(self, state: OrderState) -> bool:
        return any(leg not in state.gig_of or self.books.gigs[state.gig_of[leg]].status == "open" for leg in state.undelivered())

    def late_price(self, queue: Queue) -> float:
        """The shadow price, in cents, of one late order: next to nothing while the books expect far fewer late orders than we allow ourselves, steep as they come near that share and past it."""
        books, allowed = self.books, 1 - self.policy.on_time
        late = queue.late - BOOKED_LATE * queue.backlog + self.policy.start * allowed * CALM
        for state in books.orders.values():
            late += (1.0 if state.late else BOOKED_LATE) if state.undelivered() else state.id in books.refunded
        used = late / (CALM + len(books.orders)) / allowed
        return self.policy.late_price * 100 * min(2.0, used) ** GRIP

    def harm(self, multiple: float, queue: Queue, late_price: float) -> float:
        """What one more gig at this fee costs the cars that wait, in cents: it lengthens the queue, and a fee above theirs draws their drivers."""
        outbid = (ON_TIME["fee"] - ON_TIME["level"]) * math.log(queue.level(multiple) / queue.going) if queue.backlog else 0.0
        return self.policy.crowding * (queue.refunds + queue.swing * late_price) * (outbid - ON_TIME["backlog"] / (1 + queue.backlog))

    def chances(self, state: OrderState) -> list[Span]:
        """When an order's first car can still be collected, from now on, and arrive on time."""
        leg, facts = state.order["legs"][0], self.facts(state, 0)
        arrive = notes.arrive_by(leg["delivery"], facts, state.order["deadline"])
        return [] if arrive is None else notes.collect_spans(leg["pickup"], facts, self.books.now, min(arrive - self.road(leg), leg["pickup"]["window"]["to"]))

    def car(self, request: PriceRequest, spans: list[Span], at: int, since: Optional[int] = None) -> dict[str, float]:
        """What we know at minute `at` about how easily this request finds a driver in time, given when its car can be collected and since when it has waited."""
        leg = request["legs"][0]
        km = self.atlas.km[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])]
        slack = math.log1p(max(0, max((b for _, b in spans), default=at) - at) / HOUR)
        return {
            "one": 1.0,
            "slack": slack,
            "short": float(km < 40),
            "long": min(max(km, 100), 800) / 100 - 1,
            "premium": any(l["car"]["premium"] for l in request["legs"]) * max(0.0, math.log1p(3 * DAY / HOUR) - slack),  # one driver in fourteen may take it: it needs room
            "trade_in": float(len(request["legs"]) > 1),
            "drivers_delivery": math.log1p(self.drivers_near[leg["delivery"]["placeId"]]),
            "drivers_pickup": math.log1p(self.drivers_near[leg["pickup"]["placeId"]]),
            "private_pickup": float(leg["pickup"]["privateAddress"]),
            "private_delivery": float(leg["delivery"]["privateAddress"]),
            "waited": min(1.0, max(0, at - (at if since is None else since)) / HOUR),  # a gig that is an hour in the app did not pay the drivers who saw it
        }

    def signs(self, car: dict[str, float], multiple: float, queue: Queue) -> dict[str, float]:
        """The car's signs with those of its fee and of the queue it joins: drivers choose among our open gigs."""
        level = queue.level(multiple)
        return dict(car, fee=math.log(multiple / level), level=math.log(level), backlog=math.log1p(queue.backlog), known=math.log1p(min(queue.known, KNOWN)))

    def logit(self, car: dict[str, float], multiple: float, queue: Queue) -> float:
        """The model's log odds that the car arrives on time when its gig pays this multiple of the typical fee and the queue is this one."""
        signs = self.signs(car, multiple, queue)
        return sum(weight * signs[name] for name, weight in self.weights.items())

    def on_time(self, car: dict[str, float], multiple: float, queue: Queue) -> float:
        """The chance that the car arrives on time: the model's, moved by what this week's world has shown."""
        return 1 / (1 + math.exp(-self.logit(car, multiple, queue) - queue.world))

    def fee(self, car: dict[str, float], typical: float, refund: float, late_price: float, queue: Queue, floor: float = 0.0, more: tuple[float, ...] = ()) -> tuple[float, float]:
        """The fee multiple that costs least in all: the fee, the expected cost of a late car, and the harm to the cars that wait. With it, the chance of a late car."""
        def total(multiple: float) -> float:
            return multiple * typical + (1 - self.on_time(car, multiple, queue)) * (refund + late_price) + self.harm(multiple, queue, late_price)
        multiple = min((m for m in self.policy.fees + more if m >= floor), key=total, default=floor)
        return multiple, 1 - self.on_time(car, multiple, queue)

    def road(self, leg: Leg) -> int:
        """Minutes from a leg's pickup to its delivery by the map, with the charging stop of an electric car that needs one."""
        car, ends = leg["car"], (leg["pickup"]["placeId"], leg["delivery"]["placeId"])
        return self.atlas.drive(*ends) + CHARGING * bool(car["electric"] and car["chargePercent"] is not None and car["chargePercent"] < 30 and self.atlas.km[ends] > 200)

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
            collect = arrive and max((b for a, b in open_spans(leg["pickup"]["hours"], max(now, start), arrive - drive - int(drive * self.policy.spare))), default=None)
            if collect and collect >= now + 30:
                return collect, arrive
        return None, None

    def fee_multiple(self, state: OrderState, legs: list[int], typical: float) -> float:
        """One fee while a gig waits, and few changes of it, so drivers do not learn to wait. It is chosen when the order needs a driver, and again only when it loses one,
        when its deadline warning comes, and when the gig has sat long (some hours in the app if we look early, the last day before its last pickup): then at least one step up."""
        policy, books, gig = self.policy, self.books, self.open_gig(state, legs[0])
        posted = gig.schedule[-1]["feeCents"] / typical if gig else 0.0
        if state.late:
            return policy.late_fee
        if gig and self.looked(state, gig):
            return posted
        if state.urgent:
            return max(posted, policy.urgent_fee)
        queue = self.queue(but=state)
        more = policy.raises if gig else ()
        floor = posted if not gig or gig.schedule[-1]["at"] < state.alarm_at and not policy.redrop else min((m for m in policy.fees + more if m > posted), default=posted)  # a gig that waited that long did not pay the drivers who saw it
        if gig and books.now >= state.order["lastPickupAt"] - LAST_DAY:
            floor = max(floor, policy.last_fee)
        car = self.car(state.request, self.chances(state), books.now, state.won_at)
        chosen = self.fee(car, typical, REFUND * self.list_price(state), self.late_price(queue), queue, floor, more)[0]
        return random.Random(f"{policy.seed}:{state.id}").choice(policy.explore) if policy.explore and not posted else chosen

    def gig_posted(self, action: PostAction) -> None:
        """The world took a gig of ours. For an order's first gig of its own we keep what the model says of it at this minute: the week's world is measured against it.
        The desk calls this where it reads the world's answer, so a restart that replays the journal rebuilds the same memory."""
        owners = {stop["orderId"] for stop in action["stops"]}
        state = self.books.orders.get(min(owners)) if len(owners) == 1 else None
        if state is None or state.id in self.forecast or state.late or state.urgent:
            return
        cars = sum(1 for stop in action["stops"] if stop["kind"] == "pickup")
        paid = action["schedule"][0]["feeCents"] / (state.request["referenceFeeCents"] * cars / len(state.order["legs"]))
        multiple = min(self.policy.fees + (self.policy.explore or ()), key=lambda m: abs(m - paid))  # the fee as we chose it, before it became whole cents
        car = self.car(state.request, self.chances(state), self.books.now, state.won_at)
        self.forecast[state.id] = self.logit(car, multiple, self.queue(but=state))

    def looked(self, state: OrderState, gig: GigState) -> bool:
        """True when the gig's fee was chosen after everything that asks for a new choice: a lost driver, the deadline warning, its hours in the app if we look early, the last day before its last pickup."""
        early = gig.posted_at + int(self.policy.early_look * HOUR) if self.policy.early_look else 0
        if early and self.policy.look_every and self.books.now > early:
            early += int((self.books.now - early) // (self.policy.look_every * HOUR) * self.policy.look_every * HOUR)
        marks = (state.alarm_at, early, state.order["lastPickupAt"] - LAST_DAY)
        return gig.schedule[-1]["at"] >= max(mark for mark in marks if mark <= max(self.books.now, state.alarm_at))

    def due(self) -> set[str]:
        """The orders whose gig has waited past such a moment at the fee it had: their fee is chosen again."""
        return {state.id for state in self.books.orders.values() if state.undelivered() and not state.urgent and not state.late
                and (gig := self.open_gig(state, state.undelivered()[0])) and not self.looked(state, gig)}

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
