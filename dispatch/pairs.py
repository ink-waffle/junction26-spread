"""Two cars for one driver: a new car waits a little for a second one that starts where it ends, and the two go in one gig for less than two fees."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from spread.types import Action, DeliveryOption, PriceRequest

from . import notes
from .atlas import HOUR, Atlas, open_spans
from .books import Books, OrderState
from .fleet import CHARGING, NEAR_KM, Fleet

PLATES = 30  # minutes to fetch transfer plates on the way to a pickup (RULES.md)
WARNING = 3 * HOUR  # the deadline warning comes this long before the last possible pickup (RULES.md)


@dataclass
class PairsPolicy:
    hold: int = 30  # minutes a new car stays out of the app to wait for a second car; 0: every car goes alone
    fee: float = 0.7  # the fee of a two-car gig, as a multiple of the two typical fees together
    drive: int = 5 * HOUR  # the most road minutes a two-car gig may plan (the rules allow 12 h; long ones find no driver)
    patience: int = 60  # minutes from its posting that a two-car gig may be without a driver before its cars go alone
    lead: int = 3 * HOUR  # a pair must still fit a driver who reaches the first pickup this much later
    idle: int = HOUR  # the most minutes that driver may stand waiting at the stops
    board: bool = False  # also pair a new car with a car that sits in the app without a driver
    control: float = 0.0  # research: the share of such pairs that we leave as two gigs
    kept: float = 0.0  # the share of two-car gigs that a driver takes and keeps: what a likely partner takes off a car's cost when we price it


class Pairs:
    """Keeps no state of the week: who waits and which gig is shared are read from the books, so a restart changes nothing."""

    def __init__(self, policy: PairsPolicy, books: Books, fleet: Fleet, atlas: Atlas, pending: set[tuple[str, int]]):
        self.policy, self.books, self.fleet, self.atlas, self.pending = policy, books, fleet, atlas, pending
        self.near = {a: {b for b in atlas.places if atlas.crow_km(a, b) <= NEAR_KM} for a in atlas.places}
        self.log: list[dict] = []  # research: every pair we made, or left alone as a control

    def holds(self, state: OrderState) -> bool:
        """True while a new one-car order stays out of the app: a second car for its driver may still be won."""
        policy, now = self.policy, self.books.now
        return (now < state.won_at + policy.hold and not state.tried and not state.paired and not state.urgent and not state.late and not state.refusals
                and len(state.order["legs"]) == 1 and state.order["lastPickupAt"] - WARNING - now >= policy.lead)

    def waiting(self) -> list[OrderState]:
        """The orders that wait for a partner now: the desk keeps an order without a gig dirty."""
        states = [self.books.orders.get(order_id) for order_id in sorted(self.books.dirty)]
        return [state for state in states if state and self.holds(state) and (state.id, 0) not in self.pending]

    def shared(self) -> list:
        return [gig for gig in self.books.gigs.values() if gig.status == "open" and gig.shared]

    def match(self) -> list[Action]:
        """Posts two waiting cars as one gig when one driver can take them in a row; takes a two-car gig that has no driver in time out of the app."""
        books, policy, now, actions = self.books, self.policy, self.books.now, []
        for gig in self.shared():
            owners = [books.orders.get(order_id) for order_id, _ in gig.legs]
            if now >= gig.posted_at + policy.patience or any(state is None or state.urgent or state.late for state in owners):
                actions.append({"type": "withdraw", "gigId": gig.id})
                books.gig_gone(gig.id)  # its cars are dirty now: the desk posts each alone
        waiting = {state.id: state for state in self.waiting()}
        board = {}  # cars that sit in the app alone, without a driver: order id -> its gig
        for gig in books.gigs.values() if policy.board and waiting else []:
            state = books.orders.get(gig.legs[0][0]) if gig.status == "open" and len(gig.legs) == 1 else None
            if state and not state.paired and not state.urgent and not state.late and len(state.order["legs"]) == 1 and state.order["lastPickupAt"] - WARNING - now >= policy.lead:
                board[state.id] = gig
        everyone = {**waiting, **{order_id: books.orders[order_id] for order_id in board}}
        options = [(p.id not in board and q.id not in board, idle, p.id, q.id) for p in everyone.values() for q in everyone.values()
                   if p is not q and (p.id in waiting or q.id in waiting) for idle in [self.idle(p, q)] if idle is not None]
        for _, _, p_id, q_id in sorted(options):
            if p_id in everyone and q_id in everyone:
                p, q = everyone.pop(p_id), everyone.pop(q_id)
                old = next((order_id for order_id in (p_id, q_id) if order_id in board), None)
                if old:
                    alone = random.Random(f"{p_id}:{q_id}").random() < policy.control
                    self.log.append({"at": now, "old": old, "new": q_id if old == p_id else p_id, "first": p_id, "arm": "two gigs" if alone else "one gig",
                                     "oldPostedAt": board[old].posted_at, "oldFeeCents": board[old].schedule[-1]["feeCents"], "typicalCents": p.request["referenceFeeCents"] + q.request["referenceFeeCents"]})
                    if alone:  # research control: neither pairs again, the new car goes to the app now
                        p.paired = q.paired = True
                        continue
                    actions.append({"type": "withdraw", "gigId": board[old].id})
                    books.gig_gone(board[old].id)
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
            pickup, delivery = self.fleet.stops(state, [0])
            for stop, extra in ((pickup, PLATES * pickup["withPlates"]), (delivery, CHARGING * pickup["withCharging"])):
                site = state.order["legs"][0][stop["kind"]]
                window = stop.get("window") or site["window"]
                if here:
                    t += self.atlas.drive(here, site["placeId"]) + extra
                at = min((a for a, _ in open_spans(site["hours"], max(t, window["from"]), window["to"])), default=None)
                if at is None:
                    return None
                idle, t, here = idle + (at - t if here else 0), at, site["placeId"]
        return idle if idle <= policy.idle else None

    def saving(self, request: PriceRequest, option: DeliveryOption, multiple: float) -> int:
        """Cents of fee we expect to save if we win this request: a car that waits now could share its driver. `multiple` is the fee each would pay alone."""
        policy = self.policy
        if not policy.kept or len(request["legs"]) != 1 or multiple <= policy.fee:
            return 0
        leg = dict(request["legs"][0])
        for end in ("pickup", "delivery"):  # an order's windows at dealer sites end at the deadline of the option the dealer chose
            if not leg[end]["privateAddress"]:
                leg[end] = dict(leg[end], window={"from": leg[end]["window"]["from"], "to": min(leg[end]["window"]["to"], option["deadline"])})
        mine = OrderState({"id": request["id"], "legs": [leg], "deadline": option["deadline"]}, request, notes.read(request["note"], request["arrivedAt"]), request["respondBy"])
        partners = [other for other in self.waiting() if other.won_at + policy.hold > request["respondBy"]  # it still waits when the dealer answers
                    and (self.idle(other, mine) is not None or self.idle(mine, other) is not None)]
        typical = request["referenceFeeCents"] + max((other.request["referenceFeeCents"] for other in partners), default=0)
        return int(policy.kept * (multiple - policy.fee) * typical) if partners else 0

    def alarm(self) -> int:
        """The next minute to act at when no event comes first: a hold, or a two-car gig's patience, runs out."""
        times = [state.won_at + self.policy.hold for state in self.waiting()] + [gig.posted_at + self.policy.patience for gig in self.shared()]
        return min(times, default=10 ** 9)
