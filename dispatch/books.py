"""The books: everything the desk knows, as a fold over the world's events. Nothing here decides."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from spread.types import DeskEvent, DriverProfile, FeeStep, Order, PostAction, PriceRequest, StopRef

from . import notes
from .atlas import DAY

LIVE = ("open", "booked", "working")


@dataclass
class GigState:
    id: str
    stops: list[StopRef]
    schedule: list[FeeStep]
    posted_at: int
    status: str = "open"
    driver: Optional[str] = None
    fee: Optional[int] = None

    @property
    def legs(self) -> list[tuple[str, int]]:
        return [(s["orderId"], s["leg"]) for s in self.stops if s["kind"] == "pickup"]

    @property
    def shared(self) -> bool:
        """The gig carries cars of more than one order."""
        return len({s["orderId"] for s in self.stops}) > 1


@dataclass
class OrderState:
    order: Order
    request: PriceRequest
    facts: notes.NoteFacts
    won_at: int
    gig_of: dict[int, str] = field(default_factory=dict)  # leg -> the live gig that carries it
    failed: dict[int, tuple[str, int]] = field(default_factory=dict)  # leg -> (reason, minute) of its last failed visit
    released: dict[int, int] = field(default_factory=dict)  # leg -> minute the dealer released the car
    urgent: bool = False  # the deadline warning came and no driver holds the order
    late: bool = False  # a gig expired or a window ended: the car can only go late, without windows
    changed: bool = False  # the dealer changed the order after we posted it
    posted: bool = False  # the order has had a gig in the app
    refusals: int = 0

    @property
    def id(self) -> str:
        return self.order["id"]

    def undelivered(self) -> list[int]:
        return [i for i, at in enumerate(self.order["deliveredAt"]) if at is None]

    def unposted(self) -> list[int]:
        return [leg for leg in self.undelivered() if leg not in self.gig_of]


@dataclass
class DriverState:
    profile: DriverProfile
    last_seen: int = -1  # last minute the driver viewed, booked or answered
    place: Optional[str] = None  # where our gig last left them
    free_at: int = 0
    gigs: int = 0
    offers: dict[int, int] = field(default_factory=lambda: defaultdict(int))  # day -> offers sent


class Books:
    """State is a pure function of the event log, the gigs we posted and the quotes we sent."""

    def __init__(self, roster: list[DriverProfile]):
        self.now = 0
        self.requests: dict[str, PriceRequest] = {}
        self.quotes: dict[str, dict[str, int]] = {}
        self.outcomes: dict[str, Optional[str]] = {}  # request id -> the option won, None when lost
        self.orders: dict[str, OrderState] = {}
        self.gigs: dict[str, GigState] = {}
        self.drivers: dict[str, DriverState] = {d["id"]: DriverState(d) for d in roster}
        self.on_time: dict[str, int] = defaultdict(int)  # dealer id -> its trust count (RULES.md, level 8)
        self.ledger: dict[str, int] = defaultdict(int)
        self.refunded: set[str] = set()
        self.snow: list[tuple[int, int, set[str]]] = []
        self.dirty: set[str] = set()  # orders whose gigs may no longer match the plan

    def gig_posted(self, action: PostAction, gig_id: str, schedule: Optional[list[FeeStep]] = None, status: str = "open", posted_at: Optional[int] = None) -> GigState:
        gig = GigState(gig_id, action["stops"], schedule or action["schedule"], self.now if posted_at is None else posted_at, status)
        self.gigs[gig_id] = gig
        for order_id, leg in gig.legs:
            if order_id in self.orders:
                self.orders[order_id].gig_of[leg] = gig_id
                self.orders[order_id].posted = True
        return gig

    def gig_gone(self, gig_id: str) -> None:
        """A gig left the app without a driver: its cars need a new gig."""
        gig = self.gigs.get(gig_id)
        if gig is None:
            return
        gig.status, gig.driver = "withdrawn", None
        for order_id, leg in gig.legs:
            state = self.orders.get(order_id)
            if state and state.gig_of.get(leg) == gig_id:
                del state.gig_of[leg]
                self.dirty.add(order_id)

    def observe(self, event: DeskEvent) -> None:
        self.now = max(self.now, event["at"])
        handler = getattr(self, f"_{event['kind']}", None)
        if handler:
            handler(event)

    def _price_request(self, e) -> None:
        self.requests[e["request"]["id"]] = e["request"]

    def _order_won(self, e) -> None:
        order = e["order"]
        request = self.requests.get(order["id"])
        if request is None or order["id"] in self.orders:
            return
        self.outcomes[order["id"]] = order["option"]
        self.orders[order["id"]] = OrderState(order, request, notes.read(request["note"], request["arrivedAt"]), e["at"])
        self.dirty.add(order["id"])

    def _order_lost(self, e) -> None:
        self.outcomes[e["requestId"]] = None

    def _order_changed(self, e) -> None:
        state = self.orders.get(e["order"]["id"])
        if state:
            state.order, state.changed = e["order"], True
            self.dirty.add(state.id)

    def _order_cancelled(self, e) -> None:
        state = self.orders.pop(e["orderId"], None)
        for item in e["gigs"]:
            gig = self.gigs.get(item["gigId"])
            if gig is None:
                continue
            if item["outcome"] in ("withdrawn", "released"):
                self.gig_gone(gig.id)
            elif item["outcome"] == "shortened":
                gig.stops = [s for s in gig.stops if s["orderId"] != e["orderId"]]
        self.dirty.discard(e["orderId"])

    def _gig_viewed(self, e) -> None:
        self._seen(e["driverId"], e["at"])

    def _gig_booked(self, e) -> None:
        gig = self.gigs.get(e["gigId"])
        self._seen(e["driverId"], e["at"])
        if gig is None:
            return
        gig.status, gig.driver, gig.fee = "booked", e["driverId"], e["feeCents"]
        for order_id, leg in gig.legs:  # also heals a gig we wrongly thought withdrawn
            if order_id in self.orders:
                self.orders[order_id].gig_of[leg] = gig.id

    def _gig_dropped(self, e) -> None:
        gig = self.gigs.get(e["gigId"])
        if gig:
            gig.status, gig.driver, gig.fee = "open", None, None
            self.dirty.update(order_id for order_id, _ in gig.legs)

    _no_show = _gig_dropped

    def _gig_started(self, e) -> None:
        gig = self.gigs.get(e["gigId"])
        if gig:
            gig.status = "working"

    def _gig_expired(self, e) -> None:
        gig = self.gigs.get(e["gigId"])
        if gig:
            for order_id, _ in gig.legs:
                if order_id in self.orders:
                    self.orders[order_id].late = True
            self.gig_gone(gig.id)

    def _deadline_close(self, e) -> None:
        state = self.orders.get(e["orderId"])
        if state:
            state.urgent = True
            state.order["lastPickupAt"] = e["lastPickupAt"]
            self.dirty.add(state.id)

    def _release(self, e) -> None:
        state = self.orders.get(e["orderId"])
        if state:
            state.released[e["leg"]] = e["at"]

    def _picked_up(self, e) -> None:
        self._at_place(e["gigId"], e["placeId"])

    def _visit_failed(self, e) -> None:
        state = self.orders.get(e["orderId"])
        if state:
            state.gig_of.pop(e["leg"], None)
            state.failed[e["leg"]] = (e["reason"], e["at"])
            self.dirty.add(state.id)

    def _delivered(self, e) -> None:
        self._at_place(e["gigId"], e["placeId"])
        state = self.orders.get(e["orderId"])
        if state:
            state.order["deliveredAt"][e["leg"]] = e["at"]
            state.gig_of.pop(e["leg"], None)
        gig = self.gigs.get(e["gigId"])
        if gig and all(self._leg_done(order_id, leg) for order_id, leg in gig.legs):
            gig.status = "done"
            if gig.driver in self.drivers:
                self.drivers[gig.driver].free_at = e["at"]
                self.drivers[gig.driver].gigs += 1

    def _forecast(self, e) -> None:
        self.snow.append((e["from"], e["to"], set(e["placeIds"])))

    def _ledger(self, e) -> None:
        line = e["line"]
        self.ledger[line["kind"]] += line["cents"]
        order_id = line.get("orderId")
        dealer = self.requests[order_id]["dealerId"] if order_id in self.requests else None
        if line["kind"] in ("late_refund", "undelivered_penalty") and dealer and order_id not in self.refunded:
            self.refunded.add(order_id)
            self.on_time[dealer] = (self.on_time[dealer] - 1) // 2 if line["kind"] == "late_refund" else self.on_time[dealer] // 2
        elif line["kind"] == "revenue" and dealer:
            self.on_time[dealer] = min(25, self.on_time[dealer] + 1)

    def _offer_answered(self, e) -> None:
        if e["answer"] != "expired":
            self._seen(e["driverId"], e["at"])

    def _seen(self, driver_id: str, at: int) -> None:
        if driver_id in self.drivers:
            self.drivers[driver_id].last_seen = at

    def _at_place(self, gig_id: str, place: str) -> None:
        gig = self.gigs.get(gig_id)
        if gig and gig.driver in self.drivers:
            self.drivers[gig.driver].place = place

    def _leg_done(self, order_id: str, leg: int) -> bool:
        state = self.orders.get(order_id)
        return state is None or state.order["deliveredAt"][leg] is not None or leg not in state.gig_of

    def margin(self) -> int:
        return sum(self.ledger.values())

    def day(self) -> int:
        return self.now // DAY
