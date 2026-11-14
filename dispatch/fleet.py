"""The driver side: the chance that a car arrives on time, the fee that buys that chance cheapest, and so what the car costs us."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional

from spread.types import Audience, DeliveryOption, FeeStep, PostAction, PriceRequest, StopRef

from . import notes
from .atlas import DAY, HOUR, Atlas
from .books import Books, GigState, OrderState
from .timetable import Span, Timetable, chances

NEAR_KM = 30  # the app notifies drivers who live this close to the pickup (RULES.md)
# ON_TIME: the logistic weights of "the car arrives on time", fitted on our own weeks. `python -m tools.fleet_fit <tags>` prints the first row,
# `fleet_fit --add` the second (on weeks of the merged system, the rest held and the model's mean chance kept), `fleet_fit --add flu` the third.
# "fee" weighs a gig's fee against the fees of our other open gigs, "level" the fee that our open gigs pay together: drivers choose among our gigs.
# "supply" is the week's drivers near a place; "pay" the typical fee as a share of the list price: it has a noise of its own, and our fee is a multiple of it.
# "flu" is how much likelier than one working day in five the car's last day is the day of the week's flu (48 weeks; it also moved "one" from -5.80).
ON_TIME = {
    "one": -5.75, "fee": 3.96, "level": 0.88, "slack": 1.13, "short": -1.85, "long": -0.44, "trade_in": -3.35, "backlog": -0.58, "known": 0.25, "waited": -0.75,
    "supply_pickup": 0.75, "supply_delivery": 0.71, "private_delivery": -0.75, "premium": -0.82, "pay": 1.97,
    "flu": -2.6,
}
BOOKED_LATE = 0.030  # the share of cars with a driver that still arrive late: drops and slow drives (tools/fleet_fit.py prints it)
REFUND = 0.54  # what a late order pays back on average, as a share of its list price (tools/fleet_fit.py prints it)
SICK, WELL = 0.33, 0.03  # of the bookings held for a day, the share given back in its first hour: on the week's flu night, on any other (tools/night_study.py)
LAST_DAY = DAY  # before its last pickup: of the gigs still open then, one in four reaches the deadline warning and ends late (tools/late_study.py)
# Set by hand and tried on the tune weeks, not fitted:
DOUBT = 4.0  # how firmly we hold, before a week's own outcomes speak, that its world is the model's: the prior's weight, in outcomes
GRIP = 4  # how steeply the price of a late order rises once we expect more of them than we allow ourselves
CALM = 20  # orders: a week's first orders say little about its share of late ones
KNOWN = 100  # bookings after which the drivers know that our fees stay as posted


@dataclass
class FleetPolicy:
    fees: tuple[float, ...] = (0.85, 1.0, 1.15, 1.3, 1.5)  # the fees a gig may open at, as multiples of the typical fee
    urgent_fee: float = 1.6  # after the deadline warning
    late_fee: float = 1.3  # once the car can only arrive late: enough for the drivers who saw it at less, or it is never delivered
    on_time: float = 0.97  # the on-time share we aim at: the 90% minimum with room for a bad week (32 weeks end 0.9 points under the aim, the worst 6.3)
    late_price: float = 300.0  # euros that a late order costs us beyond its refund while we are within that share
    early_look: float = 6.0  # hours in the app after which a gig nobody took has its fee chosen again, a step up at least; 0: only on its last day


@dataclass
class GigPlan:
    """A gig to post: the legs it carries, its stops, who may take it, its one fee."""
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

    def without(self, multiple: float) -> "Queue":
        """The queue as one of its own gigs, at this multiple, meets it: the others."""
        return Queue(self.backlog - 1, (self.going * self.backlog - multiple) / max(1, self.backlog - 1), self.known)


class Fleet:
    """What a car costs us and how its gig is posted. The market calls `cost`; the desk `plan`, `schedule`, `due`, `gig_posted`; the pairs `stops`, `audience`.
    Below them: the rule for when a fee is chosen, the on-time model that chooses it, the queue and what the week has taught.
    When a car can be collected, and the stops of its gig, the timetable knows."""

    def __init__(self, policy: FleetPolicy, books: Books, atlas: Atlas, held: Optional[Callable[[OrderState], bool]] = None):
        self.policy, self.books, self.atlas = policy, books, atlas
        self.timetable = Timetable(books, atlas)  # when a car can be collected, and the stops of its gig
        self.held = held or (lambda state: False)  # the orders that the desk's pairs keep out of the app: no driver has turned those down
        homes = [driver["homePlaceId"] for driver in books.drivers.values()]
        near = lambda place: sum((1 + atlas.crow_km(home, place) / NEAR_KM) ** -2 for home in homes)  # each driver by how near they live: a quarter at 30 km
        self.supply = {place: math.log1p(near(place)) for place in atlas.places}  # the week's drivers near each place
        self.forecast: dict[str, float] = {}  # order -> the model's logit when the world took its gig: what this week's outcomes are measured against

    def cost(self, request: PriceRequest, option: DeliveryOption) -> Optional[int]:
        """What we expect to pay, in cents, to move this request by this option's deadline; None when the car cannot be collected in time.
        The fee, the late car's refund, its use of the room under the delivery minimum, and what it does to the cars that wait for a driver."""
        spans = chances(request, option, notes.read(request["note"], request["arrivedAt"]), self.timetable.road(request["legs"][0]))
        if not spans:
            return None
        queue = self.queue()
        typical, refund, late_price = request["referenceFeeCents"], REFUND * option["listPriceCents"], self.late_price(queue)
        multiple, late = self.cheapest_fee(self.car(request, spans, request["respondBy"]), typical, refund, late_price, queue)
        risk = late * refund + (late - (1 - self.policy.on_time)) * late_price + self.harm(multiple, queue, late_price)
        return int(typical * multiple + max(0.0, risk))

    def plan(self, state: OrderState, legs: list[int]) -> list[GigPlan]:
        """The gigs that should carry these legs of the order now: the timetable's stops, who may take them, one fee."""
        return [GigPlan(group, stops, self.audience(state, group), self.schedule(state, group)) for group, stops in self.timetable.gigs(state, legs)]

    def schedule(self, state: OrderState, legs: list[int]) -> list[FeeStep]:
        """A gig's fee schedule: one step, at the fee that the rule gives now."""
        typical = state.request["referenceFeeCents"] * len(legs) / len(state.order["legs"])
        return [{"at": self.books.now, "feeCents": max(1, int(typical * self.fee_now(state, legs, typical) + 0.5))}]

    def due(self) -> set[str]:
        """The orders whose gig has waited past a moment of the rule at the fee it had: their fee is chosen again."""
        return {state.id for state in self.books.orders.values() if state.undelivered() and not state.urgent and not state.late
                and (gig := self.open_gig(state, state.undelivered()[0])) and not self.looked(state, gig)}

    def gig_posted(self, action: PostAction) -> None:
        """The world took a gig of ours. For an order's first gig of its own we keep what the model says of it at this minute: the week is measured against it.
        The desk calls this where it reads the world's answer, so a restart that replays the journal rebuilds the same memory."""
        owners = {stop["orderId"] for stop in action["stops"]}
        state = self.books.orders.get(min(owners)) if len(owners) == 1 else None
        if state is None or state.id in self.forecast or state.late or state.urgent:
            return
        cars = sum(1 for stop in action["stops"] if stop["kind"] == "pickup")
        paid = action["schedule"][0]["feeCents"] / (state.request["referenceFeeCents"] * cars / len(state.order["legs"]))
        multiple = min(self.policy.fees, key=lambda m: abs(m - paid))  # the fee as we chose it, before it became whole cents
        car = self.car(state.request, self.timetable.chances_left(state), self.books.now, state.won_at)
        self.forecast[state.id] = self.logit(car, multiple, self.queue(but=state))

    def stops(self, state: OrderState, legs: list[int]) -> list[StopRef]:
        """A pickup and a delivery for each leg, with the windows the timetable gives them: what the pairs build a two-car gig from."""
        return self.timetable.stops(state, legs)

    def audience(self, state: OrderState, legs: list[int]) -> Audience:
        """Who may take the gig: experienced drivers for a premium car, a manual licence where the note or a failed visit asks for one."""
        premium = any(state.order["legs"][leg]["car"]["premium"] for leg in legs)
        licence = state.facts.manual or any(state.failed.get(leg, ("", 0))[0] == "licence" for leg in legs)
        return {"experienced": premium, "manualLicence": licence}

    # The rule: one fee while a gig waits, chosen again at few moments.

    def fee_now(self, state: OrderState, legs: list[int], typical: float) -> float:
        """The fee multiple that the order's gig should show now. One fee while a gig waits, and few changes of it, so drivers do not learn to wait:
        the model chooses it when the order needs a driver, and again only at a moment of `looked`, then at least one step up.
        After the deadline warning, and for a car that can only arrive late, the policy names the fee."""
        policy, books, gig = self.policy, self.books, self.open_gig(state, legs[0])
        posted = gig.schedule[-1]["feeCents"] / typical if gig else 0.0
        if state.late:
            return policy.late_fee
        if gig and self.looked(state, gig):
            return posted
        if state.urgent:
            return max(posted, policy.urgent_fee)
        queue = self.queue(but=state)
        step_up = min((m for m in policy.fees if m > posted), default=posted)  # a gig that waited that long did not pay the drivers who saw it
        floor = posted if not gig or gig.schedule[-1]["at"] < state.alarm_at else step_up
        car = self.car(state.request, self.timetable.chances_left(state), books.now, state.won_at)
        return self.cheapest_fee(car, typical, REFUND * self.list_price(state), self.late_price(queue), queue, floor)[0]

    def looked(self, state: OrderState, gig: GigState) -> bool:
        """True when the gig's fee was chosen after every moment that asks for a new choice:
        a lost driver, the deadline warning, its hours in the app if we look early, the last day before its last pickup."""
        early = gig.posted_at + int(self.policy.early_look * HOUR) if self.policy.early_look else 0
        marks = (state.alarm_at, early, state.order["lastPickupAt"] - LAST_DAY)
        return gig.schedule[-1]["at"] >= max(mark for mark in marks if mark <= max(self.books.now, state.alarm_at))

    def open_gig(self, state: OrderState, leg: int) -> Optional[GigState]:
        """The order's own gig for this leg while no driver has it; a two-car gig's fee is not this order's own."""
        gig = self.books.gigs.get(state.gig_of.get(leg, ""))
        return gig if gig and gig.status == "open" and not gig.shared else None

    def posted(self, state: OrderState) -> float:
        """The multiple of its typical fee that the order's open gig shows in the app; 0 when it has none."""
        gig = self.open_gig(state, state.undelivered()[0])
        return gig.schedule[-1]["feeCents"] / state.request["referenceFeeCents"] * len(state.order["legs"]) / len(gig.legs) if gig else 0.0

    def list_price(self, state: OrderState) -> int:
        """The list price of the option that the dealer bought."""
        return next(option["listPriceCents"] for option in state.request["options"] if option["kind"] == state.order["option"])

    # The on-time model: the chance that a car arrives on time, and the fee that costs least given that chance.

    def cheapest_fee(self, car: dict[str, float], typical: float, refund: float, late_price: float, queue: Queue, floor: float = 0.0) -> tuple[float, float]:
        """The model's choice: the fee multiple that costs least in all (the fee, the expected cost of a late car, the harm to the cars that wait).
        With it, the chance of a late car."""
        def total(multiple: float) -> float:
            return multiple * typical + (1 - self.chance(car, multiple, queue)) * (refund + late_price) + self.harm(multiple, queue, late_price)
        multiple = min((m for m in self.policy.fees if m >= floor), key=total, default=floor)
        return multiple, 1 - self.chance(car, multiple, queue)

    def chance(self, car: dict[str, float], multiple: float, queue: Queue) -> float:
        """The chance that the car arrives on time: the model's, moved by what this week's world has shown."""
        return 1 / (1 + math.exp(-self.logit(car, multiple, queue) - queue.world))

    def logit(self, car: dict[str, float], multiple: float, queue: Queue) -> float:
        """The model's log odds that the car arrives on time when its gig pays this multiple of the typical fee and the queue is this one."""
        signs = self.signs(car, multiple, queue)
        return sum(weight * signs[name] for name, weight in ON_TIME.items())

    def signs(self, car: dict[str, float], multiple: float, queue: Queue) -> dict[str, float]:
        """The car's signs with those of its fee and of the queue it joins: drivers choose among our open gigs."""
        level = queue.level(multiple)
        return dict(car, fee=math.log(multiple / level), level=math.log(level), backlog=math.log1p(queue.backlog), known=math.log1p(min(queue.known, KNOWN)))

    def car(self, request: PriceRequest, spans: list[Span], at: int, since: Optional[int] = None) -> dict[str, float]:
        """The signs of a request at minute `at`: how easily it finds a driver in time, given when its car can be collected and since when it has waited."""
        leg = request["legs"][0]
        km = self.atlas.km[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])]
        last = max((b for _, b in spans), default=at)
        slack = math.log1p(max(0, last - at) / HOUR)
        return {
            "one": 1.0,
            "flu": self.flu(last // DAY),  # on the car's last day: a booking for it comes back that night, and the day has fewer drivers
            "slack": slack,
            "short": float(km < 40),
            "long": min(max(km, 100), 800) / 100 - 1,
            "premium": float(any(l["car"]["premium"] for l in request["legs"])),  # one driver in fourteen may take it
            "trade_in": float(len(request["legs"]) > 1),
            "supply_pickup": self.supply[leg["pickup"]["placeId"]],  # the shortage differs from town to town; the app tells the drivers near the pickup
            "supply_delivery": self.supply[leg["delivery"]["placeId"]],  # a driver who lives where the car goes is home when it is delivered
            "private_delivery": float(leg["delivery"]["privateAddress"]),  # a booked hour to meet, not a day
            "pay": math.log(request["referenceFeeCents"] / len(request["legs"]) / request["options"][0]["listPriceCents"]),
            "waited": min(1.0, max(0, at - (at if since is None else since)) / HOUR),  # a gig that is an hour in the app did not pay the drivers who saw it
        }

    def flu(self, day: int) -> float:
        """How much likelier than one working day in five this day is the day of the week's flu, when a third of the drivers stay at home.
        It shows in a day's first hour, when they give back what they held for it: each night seen so far weighs every day it could be. Monday has no night."""
        def weight(d: int) -> float:
            held, back = self.books.nights.get(d, (0, 0))
            return math.exp(back * math.log(SICK / WELL) + (held - back) * math.log((1 - SICK) / (1 - WELL)))
        return max(0.0, weight(day) / sum(weight(d) for d in range(5)) - 0.2) if 0 <= day < 5 else 0.0

    # The queue of cars without a driver, what the week has taught, and the price of a late order.

    def queue(self, but: Optional[OrderState] = None) -> Queue:
        """The orders that wait for a driver now, but for one: how many, at what fee, with what chances."""
        books = self.books
        waiting = [state for state in books.orders.values() if state is not but and self.waits(state)]
        fees = [self.posted(state) or 1.0 for state in waiting]  # an order without a gig of its own counts at the typical fee
        queue = Queue(len(waiting), sum(fees) / max(1, len(waiting)), sum(1 for gig in books.gigs.values() if gig.driver))
        logits = {}
        for state, multiple in zip(waiting, fees):
            car = self.car(state.request, self.timetable.chances_left(state), books.now, state.won_at)
            logits[state.id] = self.logit(car, multiple, queue.without(multiple))
        queue.world = self.learned(logits)
        for state in waiting:
            chance = 1 / (1 + math.exp(-logits[state.id] - queue.world))
            queue.late += 1 - chance
            queue.swing += chance * (1 - chance)
            queue.refunds += chance * (1 - chance) * REFUND * self.list_price(state)
        return queue

    def waits(self, state: OrderState) -> bool:
        """True for an order that the drivers can see and have not taken: not held back by us for a partner, not in a two-car gig, not late."""
        gigs = [self.books.gigs[gig_id] for gig_id in state.gig_of.values()]
        return not state.late and not self.held(state) and self.needs_driver(state) and not any(gig.shared and gig.status == "open" for gig in gigs)

    def needs_driver(self, state: OrderState) -> bool:
        """True while a car of the order has no gig, or a gig that no driver has taken."""
        return any(leg not in state.gig_of or self.books.gigs[state.gig_of[leg]].status == "open" for leg in state.undelivered())

    def learned(self, waiting: dict[str, float]) -> float:
        """The intercept that best explains this week's own orders against what the model said when we posted each: this world's drivers,
        as far as they have shown themselves. A week moves the model by one logit at most."""
        seen = [(logit, outcome) for order_id, logit in self.forecast.items() for outcome in [self.outcome(order_id, waiting)] if outcome is not None]
        shift = 0.0
        for _ in range(4):  # Newton's method on one number, from a prior that the world is the model's
            chances = [1 / (1 + math.exp(-logit - shift)) for logit, _ in seen]
            surprise = sum(outcome - chance for (_, outcome), chance in zip(seen, chances)) - DOUBT * shift
            shift += surprise / (sum(chance * (1 - chance) for chance in chances) + DOUBT)
        return max(-1.0, min(1.0, shift))

    def outcome(self, order_id: str, waiting: dict[str, float]) -> Optional[float]:
        """How an order of the week stands, as a chance of on time: late 0, delivered 1 unless it paid a refund, with a driver almost 1,
        waiting as the model sees it now. None while it says nothing: we hold it back, or it is in a two-car gig."""
        state = self.books.orders.get(order_id)
        if state is None:
            return None
        if state.late:
            return 0.0
        if order_id in waiting:
            return 1 / (1 + math.exp(-waiting[order_id]))
        if not state.undelivered():
            return float(order_id not in self.books.refunded)
        return None if self.needs_driver(state) else 1 - BOOKED_LATE

    def late_price(self, queue: Queue) -> float:
        """The shadow price, in cents, of one late order: next to nothing while the books expect far fewer late orders than we allow ourselves,
        steep as they come near that share and past it."""
        books, allowed, late = self.books, 1 - self.policy.on_time, queue.late - BOOKED_LATE * queue.backlog
        for state in books.orders.values():
            late += (1.0 if state.late else BOOKED_LATE) if state.undelivered() else state.id in books.refunded
        used = late / (CALM + len(books.orders)) / allowed
        # capped at twice the allowed share (EUR 4,800 a late order): past it even the safest car would be refused, and a week does not mend by winning nothing
        return self.policy.late_price * 100 * min(2.0, used) ** GRIP

    def harm(self, multiple: float, queue: Queue, late_price: float) -> float:
        """What one more gig at this fee costs the cars that wait, in cents: it lengthens the queue, and a fee above theirs draws their drivers."""
        outbid = (ON_TIME["fee"] - ON_TIME["level"]) * math.log(queue.level(multiple) / queue.going) if queue.backlog else 0.0
        return (queue.refunds + queue.swing * late_price) * (outbid - ON_TIME["backlog"] / (1 + queue.backlog))
