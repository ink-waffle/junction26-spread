"""Two cars for one driver: a new car waits a little for a second one that starts where it ends, and the two go in one gig for less than two fees."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from spread.types import Action, DeliveryOption, PriceRequest

from . import notes
from .atlas import HOUR, Atlas, open_spans
from .books import Books, OrderState
from .fleet import Fleet

NEAR_KM = 30  # "where it ends": the radius the drivers' app itself calls near (RULES.md)
WARNING = 3 * HOUR  # the deadline warning comes this long before the last possible pickup (RULES.md)
NEVER = 10 ** 9


@dataclass
class PairsPolicy:
    hold: int = 30  # minutes a new car stays out of the app to wait for a second car; 0: every car goes alone
    fee: float = 0.7  # the fee of a two-car gig, as a multiple of the two typical fees together
    drive: int = 5 * HOUR  # the most road minutes a two-car gig may plan (the rules allow 12 h; long ones find no driver)
    patience: int = 60  # minutes an unbooked two-car gig stays in the app before its cars go alone
    lead: int = 3 * HOUR  # a pair must still fit a driver who reaches the first pickup this much later
    idle: int = HOUR  # the most minutes that driver may stand waiting at the stops


class Pairs:
    def __init__(self, policy: PairsPolicy, books: Books, fleet: Fleet, atlas: Atlas):
        self.policy, self.books, self.fleet, self.atlas = policy, books, fleet, atlas
        self.near = {a: {b for b in atlas.places if atlas.crow_km(a, b) <= NEAR_KM} for a in atlas.places}
        self.waiting: set[str] = set()  # new orders kept out of the app
        self.paired: set[str] = set()  # orders we have put in a two-car gig: they do not wait again
        self.until: dict[str, int] = {}  # waiting order -> the minute of the dealer's answer to a quote that counts on it

    def holds(self, state: OrderState) -> bool:
        """True while a new one-car order stays out of the app: a second car for its driver may still be won."""
        policy, now = self.policy, self.books.now
        return (now < self.release(state) and not state.posted and not state.urgent and not state.late and state.id not in self.paired
                and len(state.order["legs"]) == 1 and state.order["lastPickupAt"] - WARNING - now >= policy.lead)

    def release(self, state: OrderState) -> int:
        """The minute a waiting order goes to the app alone."""
        return max(state.won_at + self.policy.hold, self.until.get(state.id, 0))

    def match(self) -> list[Action]:
        """Posts two waiting cars as one gig when one driver can take them in a row; takes a two-car gig that found no driver out of the app."""
        books, policy, now, actions = self.books, self.policy, self.books.now, []
        for gig in books.gigs.values():
            if gig.status == "open" and gig.shared:
                owners = [books.orders.get(order_id) for order_id, _ in gig.legs]
                if now >= gig.posted_at + policy.patience or any(state is None or state.urgent or state.late for state in owners):
                    actions.append({"type": "withdraw", "gigId": gig.id})
                    books.gig_gone(gig.id)
        for order_id in sorted(self.waiting | books.dirty):
            state = books.orders.get(order_id)
            if state and self.holds(state):
                self.waiting.add(order_id)
            elif order_id in self.waiting:  # its hold is over: the desk posts it alone
                self.waiting.discard(order_id)
                books.dirty.add(order_id)
        waiting = [books.orders[order_id] for order_id in sorted(self.waiting)]
        options = [(idle, p.id, q.id) for p in waiting for q in waiting if p is not q for idle in [self.idle(p, q)] if idle is not None]
        for _, p_id, q_id in sorted(options):
            if p_id in self.waiting and q_id in self.waiting:
                self.waiting -= {p_id, q_id}
                self.paired |= {p_id, q_id}
                p, q = books.orders[p_id], books.orders[q_id]
                first, second = self.fleet.audience(p, [0]), self.fleet.audience(q, [0])
                typical = p.request["referenceFeeCents"] + q.request["referenceFeeCents"]
                actions.append({"type": "post", "stops": self.fleet.stops(p, [0]) + self.fleet.stops(q, [0]),
                                "audience": {key: first[key] or second[key] for key in first},
                                "schedule": [{"at": now, "feeCents": max(1, int(typical * policy.fee + 0.5))}]})
        return actions

    def idle(self, p: OrderState, q: OrderState) -> Optional[int]:
        """Minutes a driver waits at stops when they take q's car right after p's; None when the two do not make a gig."""
        policy, now = self.policy, self.books.now
        legs = [p.order["legs"][0], q.order["legs"][0]]
        places = [leg[end]["placeId"] for leg in legs for end in ("pickup", "delivery")]
        if places[2] not in self.near[places[1]] or sum(self.atlas.drive(a, b) for a, b in zip(places, places[1:])) > policy.drive:
            return None
        t, here, idle = max(now + policy.lead, legs[0]["pickup"]["window"]["from"]), None, 0
        for state in (p, q):
            for stop in self.fleet.stops(state, [0]):
                site = state.order["legs"][0][stop["kind"]]
                window = stop.get("window") or site["window"]
                if here:
                    t += self.atlas.drive(here, site["placeId"]) + 30 * bool(stop.get("withPlates")) + 40 * bool(stop.get("withCharging"))
                at = min((a for a, _ in open_spans(site["hours"], max(t, window["from"]), window["to"])), default=None)
                if at is None:
                    return None
                idle, t, here = idle + (at - t if here else 0), at, site["placeId"]
        return idle if idle <= policy.idle else None

    def partner(self, request: PriceRequest, option: DeliveryOption) -> Optional[str]:
        """The waiting order whose driver could also take this request's car, if we win it with this option; None when there is none."""
        if len(request["legs"]) != 1:
            return None
        leg = dict(request["legs"][0])
        for end in ("pickup", "delivery"):  # an order's windows at dealer sites end at the deadline of the option the dealer chose
            if not leg[end]["privateAddress"]:
                leg[end] = dict(leg[end], window={"from": leg[end]["window"]["from"], "to": min(leg[end]["window"]["to"], option["deadline"])})
        state = OrderState({"id": request["id"], "legs": [leg], "deadline": option["deadline"]}, request, notes.read(request["note"], request["arrivedAt"]), request["respondBy"])
        for order_id in sorted(self.waiting):
            other = self.books.orders.get(order_id)
            if other and (self.idle(other, state) is not None or self.idle(state, other) is not None):
                self.until[order_id] = max(self.until.get(order_id, 0), request["respondBy"] + 1)  # it waits for the dealer's answer
                return order_id
        return None

    def alarm(self) -> int:
        """The next minute to act at when no event comes first: a hold, or a two-car gig's patience, runs out."""
        books, policy = self.books, self.policy
        times = [self.release(books.orders[order_id]) for order_id in self.waiting if order_id in books.orders]
        times += [gig.posted_at + policy.patience for gig in books.gigs.values() if gig.status == "open" and gig.shared]
        return min(times, default=NEVER)
