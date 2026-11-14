"""Direct offers: a car that sits in the app without a driver is offered to the experienced drivers whose gig of ours ends near its pickup."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from spread.types import Action

from .atlas import DAY, HOUR, Atlas
from .books import Books, GigState
from .fleet import NEAR_KM

OPEN = 10  # minutes an offer stays open (RULES.md)
PER_DRIVER, PER_GIG = 3, 3  # offers to one driver a day, and open offers on one gig (RULES.md)
READ = (7 * HOUR, 23 * HOUR - OPEN)  # no driver reads an offer from 23:00 to 07:00 (RULES.md)


@dataclass
class OffersPolicy:
    veteran: int = 150  # completed gigs from which a driver gets offers: the others read few and take one in a hundred (OFFERS2.md); 0: no offers
    wait: int = 30  # minutes a gig is in the app without a driver before it is offered: most gigs are booked sooner
    near: float = NEAR_KM  # km from the end of the driver's gig to the car's pickup


class Offers:
    """Keeps no state of its own: the offers sent are in the books, from the journal, so a restart repeats none."""

    def __init__(self, policy: OffersPolicy, books: Books, atlas: Atlas):
        self.policy, self.books, self.atlas = policy, books, atlas

    def send(self) -> list[Action]:
        """Each open gig that waited, to at most three drivers who end a gig of ours near its pickup on a day the car can be collected, at the fee the app shows."""
        books, policy, now = self.books, self.policy, self.books.now
        if not policy.veteran or not READ[0] <= now % DAY < READ[1]:
            return []
        today = Counter(driver for (_, driver), at in books.offers.items() if at // DAY == now // DAY)
        live = Counter(gig for (gig, _), at in books.offers.items() if at > now - OPEN)
        ends = self.ends()
        actions: list[Action] = []
        waiting = [gig for gig in books.gigs.values() if gig.status == "open" and now >= gig.posted_at + policy.wait and gig.legs[0][0] in books.orders]
        for gig in sorted(waiting, key=lambda gig: (books.orders[gig.legs[0][0]].order["lastPickupAt"], gig.id)):  # the car with the least time first
            state = books.orders[gig.legs[0][0]]
            if state.urgent or state.late:  # after the deadline warning no offer was ever taken
                continue
            pickup = state.order["legs"][gig.legs[0][1]]["pickup"]
            fee = max((step for step in gig.schedule if step["at"] <= now), key=lambda step: step["at"], default=gig.schedule[0])["feeCents"]
            for driver, place, day in ends:
                if live[gig.id] >= PER_GIG:
                    break
                if (today[driver] < PER_DRIVER and (gig.id, driver) not in books.offers and self.atlas.crow_km(place, pickup["placeId"]) <= policy.near
                        and pickup["window"]["from"] // DAY <= day <= state.order["lastPickupAt"] // DAY):
                    books.offers[(gig.id, driver)] = now
                    today[driver] += 1
                    live[gig.id] += 1
                    actions.append({"type": "offer", "gigId": gig.id, "driverId": driver, "feeCents": fee})
        return actions

    def ends(self) -> list[tuple[str, str, int]]:
        """The experienced drivers who hold a gig of ours: the driver, the place where it ends and the day they drive it."""
        books, out = self.books, []
        for gig in sorted(books.gigs.values(), key=lambda gig: gig.id):
            last, first = books.orders.get(gig.stops[-1]["orderId"]), books.orders.get(gig.stops[0]["orderId"])
            if gig.status in ("booked", "working") and gig.driver in books.drivers and last and first and books.drivers[gig.driver]["completedGigs"] >= self.policy.veteran:
                ready = first.order["legs"][gig.stops[0]["leg"]]["pickup"]["window"]["from"]
                out.append((gig.driver, last.order["legs"][gig.stops[-1]["leg"]]["delivery"]["placeId"], max(books.now, ready) // DAY))
        return out
