"""Two cars for one driver: a new car waits a little for a second one, or joins a car that sits in the app without a driver, and the two go in one gig."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from spread.types import Action

from .atlas import HOUR, Atlas, open_spans
from .books import Books, GigState, OrderState
from .fleet import CHARGING, NEAR_KM, Fleet

PLATES = 30  # minutes to fetch transfer plates on the way to a pickup (RULES.md)
WARNING = 3 * HOUR  # the deadline warning comes this long before the last possible pickup (RULES.md)


@dataclass
class PairsPolicy:
    hold: int = 30  # minutes a new car stays out of the app to wait for a second car; 0: every car goes alone
    fee: float = 0.7  # the fee of a gig of two new cars, as a multiple of the two typical fees together
    board: float = 0.85  # the same when one of the two already sits in the app without a driver: a car nobody took needs more; 0: only new cars pair
    drive: int = 5 * HOUR  # the most road minutes a two-car gig may plan (the rules allow 12 h; long ones find no driver)
    patience: int = 60  # minutes from its posting that a two-car gig may be without a driver before its cars go alone
    lead: int = 3 * HOUR  # a pair must still fit a driver who reaches the first pickup this much later
    idle: int = HOUR  # the most minutes that driver may stand waiting at the stops


class Pairs:
    """Keeps no state of the week: who waits and which gig is shared are read from the books, so a restart changes nothing."""

    def __init__(self, policy: PairsPolicy, books: Books, fleet: Fleet, atlas: Atlas, pending: set[tuple[str, int]]):
        self.policy, self.books, self.fleet, self.atlas, self.pending = policy, books, fleet, atlas, pending
        self.near = {a: {b for b in atlas.places if atlas.crow_km(a, b) <= NEAR_KM} for a in atlas.places}

    def match(self) -> list[Action]:
        """Posts a waiting car and another car without a driver as one gig, when one driver can take them in a row. First the two-car gigs that ran out of time go."""
        books, actions = self.books, self.dissolve()
        waiting = {state.id: state for state in self.waiting()}
        sitting = self.sitting() if waiting else {}
        cars = {**waiting, **{order_id: books.orders[order_id] for order_id in sitting}}
        pairs = [(p.id not in sitting and q.id not in sitting, idle, p.id, q.id) for p in cars.values() for q in cars.values()
                 if p is not q and (p.id in waiting or q.id in waiting) for idle in [self.idle(p, q)] if idle is not None]
        for fresh, _, p_id, q_id in sorted(pairs):  # a car that sits first, then the pair whose driver waits least
            if p_id in cars and q_id in cars:
                p, q = cars.pop(p_id), cars.pop(q_id)
                for order_id in (p_id, q_id):
                    if order_id in sitting:  # its own gig makes room for the pair
                        actions.append({"type": "withdraw", "gigId": sitting[order_id].id})
                        books.gig_gone(sitting[order_id].id)
                actions.append(self.gig(p, q, self.policy.fee if fresh else self.policy.board))
        return actions

    def holds(self, state: OrderState) -> bool:
        """True while a new one-car order stays out of the app: a second car for its driver may still be won."""
        policy, now = self.policy, self.books.now
        return (now < state.won_at + policy.hold and not state.tried and not state.urgent and not state.late and not state.refusals
                and len(state.order["legs"]) == 1 and state.order["lastPickupAt"] - WARNING - now >= policy.lead)

    def alarm(self) -> int:
        """The next minute to act at when no event comes first: a hold, or a two-car gig's patience, runs out."""
        times = [state.won_at + self.policy.hold for state in self.waiting()] + [gig.posted_at + self.policy.patience for gig in self.shared()]
        return min(times, default=10 ** 9)

    def waiting(self) -> list[OrderState]:
        """The orders that wait for a partner now: the desk keeps an order without a gig dirty."""
        states = [self.books.orders.get(order_id) for order_id in sorted(self.books.dirty)]
        return [state for state in states if state and self.holds(state) and (state.id, 0) not in self.pending]

    def sitting(self) -> dict[str, GigState]:
        """The cars that sit in the app alone, without a driver, and may still join a pair: order id -> its gig."""
        books, now, gigs = self.books, self.books.now, {}
        for gig in books.gigs.values() if self.policy.board else []:
            state = books.orders.get(gig.legs[0][0]) if gig.status == "open" and len(gig.legs) == 1 else None
            if (state and len(state.order["legs"]) == 1 and not (state.paired or state.urgent or state.late or state.refusals)
                    and state.order["lastPickupAt"] - WARNING - now >= self.policy.lead):
                gigs[state.id] = gig
        return gigs

    def shared(self) -> list[GigState]:
        """The two-car gigs that no driver has taken yet."""
        return [gig for gig in self.books.gigs.values() if gig.status == "open" and gig.shared]

    def dissolve(self) -> list[Action]:
        """Takes a two-car gig out of the app when it has no driver in time, or a car of it got its deadline warning or can only go late."""
        books, now, actions = self.books, self.books.now, []
        for gig in self.shared():
            owners = [books.orders.get(order_id) for order_id, _ in gig.legs]
            if now >= gig.posted_at + self.policy.patience or any(state is None or state.urgent or state.late for state in owners):
                actions.append({"type": "withdraw", "gigId": gig.id})
                books.gig_gone(gig.id)  # its cars are dirty now: the desk posts each alone
        return actions

    def gig(self, p: OrderState, q: OrderState, multiple: float) -> Action:
        """One gig that takes q's car right after p's, for drivers who may take both, at this multiple of the two typical fees together."""
        first, second = self.fleet.audience(p, [0]), self.fleet.audience(q, [0])
        typical = p.request["referenceFeeCents"] + q.request["referenceFeeCents"]
        return {"type": "post", "stops": self.fleet.stops(p, [0]) + self.fleet.stops(q, [0]),
                "audience": {key: first[key] or second[key] for key in first},
                "schedule": [{"at": self.books.now, "feeCents": max(1, int(typical * multiple + 0.5))}]}

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
