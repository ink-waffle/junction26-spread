"""Two cars for one driver: a new car waits a little for a second one that starts where it ends, and the two go in one gig for less than two fees."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from spread.types import Action

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


class Pairs:
    """Keeps no state of the week: who waits and which gig is shared are read from the books, so a restart changes nothing."""

    def __init__(self, policy: PairsPolicy, books: Books, fleet: Fleet, atlas: Atlas, pending: set[tuple[str, int]]):
        self.policy, self.books, self.fleet, self.atlas, self.pending = policy, books, fleet, atlas, pending
        self.near = {a: {b for b in atlas.places if atlas.crow_km(a, b) <= NEAR_KM} for a in atlas.places}

    def holds(self, state: OrderState) -> bool:
        """True while a new one-car order stays out of the app: a second car for its driver may still be won."""
        policy, now = self.policy, self.books.now
        return (now < state.won_at + policy.hold and not state.tried and not state.urgent and not state.late and not state.refusals
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
        options = [(idle, p.id, q.id) for p in waiting.values() for q in waiting.values() if p is not q for idle in [self.idle(p, q)] if idle is not None]
        for _, p_id, q_id in sorted(options):
            if p_id in waiting and q_id in waiting:
                p, q = waiting.pop(p_id), waiting.pop(q_id)
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

    def alarm(self) -> int:
        """The next minute to act at when no event comes first: a hold, or a two-car gig's patience, runs out."""
        times = [state.won_at + self.policy.hold for state in self.waiting()] + [gig.posted_at + self.policy.patience for gig in self.shared()]
        return min(times, default=10 ** 9)
