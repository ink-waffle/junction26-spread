"""How a car meets its driver beyond a single gig in the app: two cars in one gig, and direct offers."""
from __future__ import annotations

import heapq
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from spread.types import Action, ActionResult, FeeStep

from .atlas import DAY, HOUR, Atlas, open_spans
from .books import Books, DriverState, GigState, OrderState
from .fleet import MAX_PLAN_MINUTES, Fleet

NEAR_KM = 30  # the radius of the app's own notification (RULES.md)
READ_FROM, READ_TO = 7 * HOUR, 23 * HOUR  # no driver reads an offer outside these hours
PER_DRIVER, PER_GIG, OPEN_MINUTES = 3, 3, 10  # offers a driver gets a day, open offers of a gig, minutes an offer stays open
NEVER = 10 ** 9


@dataclass
class OffersPolicy:
    hold: int = 0  # minutes a new car stays out of the app to wait for a second car that one driver can take with it
    pair_fee: tuple[float, ...] = (0.6,)  # fee of a gig whose second car comes back to where the first started, as a multiple of both typical fees; research: several to draw from
    chain_fee: tuple[float, ...] = ()  # the same for a second car that only starts where the first ends; empty: no such gigs
    pair_control: float = 0.0  # research: share of pairs posted as two single gigs
    pair_minutes: int = 90  # an unbooked two-car gig is split into single gigs after this long
    pair_drive: int = 12 * HOUR  # the most driving, in road minutes, a two-car gig may plan: longer ones find no driver
    pair_lead: int = 3 * HOUR  # a pair must still be feasible for a driver who sets out this much later
    offer_after: Optional[int] = None  # minutes a gig sits unbooked in the app before we offer it directly, at its app fee; None: no offers
    explore: Optional[tuple[float, ...]] = None  # research: each offer's fee multiple is drawn from these, its driver from a random class
    rounds: int = 3  # research: rounds of offers a gig gets when it opens, and again after its deadline warning
    quiet_fee: float = 0.6  # the fee a new gig opens at, as a multiple of the typical fee, for its first quiet_minutes
    quiet_minutes: int = 0  # 0: a gig opens at its full fee
    quiet_share: float = 1.0  # research: share of orders that open low
    seed: str = ""


class Offers:
    def __init__(self, policy: OffersPolicy, books: Books, fleet: Fleet, atlas: Atlas):
        self.policy, self.books, self.fleet, self.atlas = policy, books, fleet, atlas
        self.active = bool(policy.explore or policy.hold)
        self.near = {a: {b for b in atlas.places if atlas.crow_km(a, b) <= NEAR_KM} for a in atlas.places}
        self.homes = {a: sum(1 for d in books.drivers.values() if d.profile["homePlaceId"] in self.near[a]) for a in atlas.places}
        self.waiting: set[str] = set()  # new orders kept out of the app while they wait for a partner
        self.alone: set[str] = set()  # orders that go in a gig of their own from now on
        self.rounds: dict[str, int] = defaultdict(int)  # order -> rounds of offers sent
        self.asked: dict[str, set[str]] = defaultdict(set)  # order -> drivers who got an offer for it
        self.meta: dict[tuple[str, str], dict] = {}

    # --- two cars in one gig ---

    def holds(self, state: OrderState) -> bool:
        """True while a new car should stay out of the app: a second car for the same driver may still come."""
        if not self.policy.hold or state.posted or state.urgent or state.late or state.id in self.alone or len(state.order["legs"]) != 1:
            return False
        if self.books.now >= state.won_at + self.policy.hold:
            return False
        self.waiting.add(state.id)
        return True

    def route(self, states: list[OrderState], start: int) -> Optional[tuple[int, int]]:
        """(minute of the last delivery, minutes waited at stops) for a driver who is at the first pickup at `start`; None when a window or stated hours cannot be met."""
        t, here, waited = start, None, 0
        for state in states:
            for stop in self.fleet.stops(state, [0]):
                site = state.order["legs"][0][stop["kind"]]
                window = stop.get("window") or site["window"]
                if here:
                    t += self.atlas.drive(here, site["placeId"]) + 30 * bool(stop.get("withPlates")) + 40 * bool(stop.get("withCharging"))
                at = min((a for a, b in open_spans(site["hours"], max(t, window["from"]), window["to"])), default=None)
                if at is None:
                    return None
                waited, t, here = waited + (at - t if here else 0), at, site["placeId"]
        return t, waited

    def pairs(self) -> list[Action]:
        """Posts two waiting cars as one gig when one driver can take them in a row; splits a two-car gig that found no driver."""
        books, policy, now, actions = self.books, self.policy, self.books.now, []
        for gig in books.gigs.values():
            owners = [books.orders.get(order_id) for order_id, _ in gig.legs]
            if gig.status == "open" and gig.shared and (now >= gig.posted_at + policy.pair_minutes or any(s is None or s.urgent or s.late for s in owners)):
                self.alone.update(s.id for s in owners if s)
                actions.append({"type": "withdraw", "gigId": gig.id})
                books.gig_gone(gig.id)
        for order_id in list(self.waiting | books.dirty):
            state = books.orders.get(order_id)
            if (state is None or not self.holds(state)) and order_id in self.waiting:
                self.waiting.discard(order_id)
                books.dirty.add(order_id)
        waiting = [books.orders[order_id] for order_id in sorted(self.waiting)]
        options = []
        for p in waiting:
            for q in waiting:
                first, second = p.order["legs"][0], q.order["legs"][0]
                if p is q or second["pickup"]["placeId"] not in self.near[first["delivery"]["placeId"]]:
                    continue
                back = second["delivery"]["placeId"] in self.near[first["pickup"]["placeId"]]
                fees = policy.pair_fee if back else policy.chain_fee
                places = [first["pickup"]["placeId"], first["delivery"]["placeId"], second["pickup"]["placeId"], second["delivery"]["placeId"]]
                if not fees or sum(self.atlas.drive(a, b) for a, b in zip(places, places[1:])) > min(MAX_PLAN_MINUTES, policy.pair_drive):
                    continue
                route = self.route([p, q], max(now + policy.pair_lead, first["pickup"]["window"]["from"]))
                if route and route[1] <= HOUR:
                    options.append((not back, route[1], -self.homes[places[0]], p.id, q.id, fees))
        taken: set[str] = set()
        for not_back, waited, _, p_id, q_id, fees in sorted(options):
            if p_id in taken or q_id in taken:
                continue
            taken.update((p_id, q_id))
            self.waiting.difference_update((p_id, q_id))
            p, q = books.orders[p_id], books.orders[q_id]
            rng = random.Random(f"{policy.seed}:pair:{p_id}:{q_id}")
            multiple = None if rng.random() < policy.pair_control else rng.choice(fees)
            typical = p.request["referenceFeeCents"] + q.request["referenceFeeCents"]
            books.pairs.append({"at": now, "orders": [p_id, q_id], "kind": "chain" if not_back else "back", "multiple": multiple, "typicalCents": typical, "waited": waited})
            if multiple is None:  # research control: the two cars go alone
                self.alone.update((p_id, q_id))
                books.dirty.update((p_id, q_id))
                continue
            ap, aq = self.fleet.audience(p, [0]), self.fleet.audience(q, [0])
            actions.append({"type": "post", "stops": self.fleet.stops(p, [0]) + self.fleet.stops(q, [0]),
                            "audience": {"experienced": ap["experienced"] or aq["experienced"], "manualLicence": ap["manualLicence"] or aq["manualLicence"]},
                            "schedule": [{"at": now, "feeCents": max(1, int(typical * multiple))}]})
        return actions

    def refused(self, order_ids: list[str]) -> None:
        """The world refused a two-car gig: its cars go alone."""
        self.alone.update(order_ids)
        self.books.dirty.update(order_ids)

    def alarm(self, posting: bool) -> int:
        """The next minute to act at when no event comes first: a hold or a two-car gig runs out, or drivers start to read offers."""
        books, policy, now = self.books, self.policy, self.books.now
        times = [books.orders[order_id].won_at + policy.hold for order_id in self.waiting if order_id in books.orders]
        times += [gig.posted_at + policy.pair_minutes for gig in books.gigs.values() if gig.status == "open" and gig.shared]
        if policy.explore:
            times += [now] * posting
        if policy.offer_after is not None:
            times += [gig.posted_at + policy.offer_after for gig in books.gigs.values() if gig.status == "open" and gig.posted_at + policy.offer_after > now]
        if policy.explore or policy.offer_after is not None:
            times += [now - now % DAY + READ_FROM] * (now % DAY < READ_FROM)
        return min(times, default=NEVER)

    def offers(self) -> list[Action]:
        """Each gig the app has left unbooked gets direct offers, at its app fee, to the three drivers likeliest to say yes."""
        books, policy, now = self.books, self.policy, self.books.now
        if policy.offer_after is None or not READ_FROM <= now % DAY < READ_TO - OPEN_MINUTES:
            return []
        holding = {gig.driver for gig in books.gigs.values() if gig.status in ("booked", "working")}
        sending: dict[str, int] = defaultdict(int)
        actions: list[Action] = []
        slow = [gig for gig in books.gigs.values() if gig.status == "open" and now >= gig.posted_at + policy.offer_after and gig.legs and gig.legs[0][0] in books.orders]
        for gig in sorted(slow, key=lambda gig: books.orders[gig.legs[0][0]].order["lastPickupAt"]):
            waiting = books.open_offers[gig.id]
            for driver_id in [d for d, offer in waiting.items() if offer["at"] + OPEN_MINUTES + 5 < now]:
                del waiting[driver_id]
            if waiting:
                continue
            order_id = gig.legs[0][0]
            state, delivery = books.orders[order_id], self.place(gig.stops[-1])
            audience = self.fleet.audience(state, [leg for owner, leg in gig.legs if owner == order_id])

            def score(driver: DriverState) -> float:  # tools/offers_study.py fit: log-odds of a yes, the terms that differ between drivers
                profile = driver.profile
                return (0.74 * math.log1p(profile["completedGigs"]) + 0.95 * (profile["homePlaceId"] in self.near[delivery])
                        + 0.6 * (profile["id"] in holding) - 1.13 * (driver.last_seen < 0))

            pool = [driver for driver_id, driver in books.drivers.items()
                    if driver.offers[now // DAY] + sending[driver_id] < PER_DRIVER and driver_id not in self.asked[order_id]
                    and (driver.profile["licence"] == "manual" or not audience["manualLicence"])
                    and (driver.profile["rating"] >= 4.8 and driver.profile["completedGigs"] >= 50 or not audience["experienced"])]
            fee = self.app_fee(gig)
            for driver in heapq.nlargest(PER_GIG, pool, key=score):
                driver_id = driver.profile["id"]
                self.asked[order_id].add(driver_id)
                sending[driver_id] += 1
                self.meta[(gig.id, driver_id)] = {"at": now, "gigId": gig.id, "orderId": order_id, "driverId": driver_id, "feeCents": fee, "class": "targeted",
                                                  "arm": "targeted", "urgent": state.urgent, "late": state.late, "postedAt": gig.posted_at, "score": round(score(driver), 2), "answer": None}
                actions.append({"type": "offer", "gigId": gig.id, "driverId": driver_id, "feeCents": fee})
        return actions

    # --- direct offers (research) ---

    def arm(self, order_id: str) -> str:
        return random.Random(f"{self.policy.seed}:arm:{order_id}").choice(("control", "with", "first"))

    def opening(self, state: OrderState, schedule: list[FeeStep]) -> list[FeeStep]:
        """The fee schedule of an order's first gig: low for a short while, so the drivers for whom the car is cheap take it first."""
        policy = self.policy
        chosen = self.arm(state.id) == "first" if policy.explore else random.Random(f"{policy.seed}:quiet:{state.id}").random() < policy.quiet_share
        if not policy.quiet_minutes or not chosen or state.posted or state.urgent or state.late:
            return schedule
        quiet = max(1, int(schedule[0]["feeCents"] / self.fleet.fee_multiple(state) * policy.quiet_fee))
        return [{"at": self.books.now, "feeCents": quiet}, {"at": self.books.now + policy.quiet_minutes, "feeCents": schedule[-1]["feeCents"]}]

    def place(self, stop) -> Optional[str]:
        state = self.books.orders.get(stop["orderId"])
        return state.order["legs"][stop["leg"]][stop["kind"]]["placeId"] if state else None

    def act(self) -> list[Action]:
        """Research: each open gig outside the control arm gets rounds of three offers, to drivers of random classes at random fees."""
        books, policy, now = self.books, self.policy, self.books.now
        if not policy.explore:
            return self.offers()
        if not READ_FROM <= now % DAY < READ_TO - OPEN_MINUTES:
            return []
        today = now - now % DAY
        ends = {gig.driver: self.place(gig.stops[-1]) for gig in books.gigs.values() if gig.status in ("booked", "working") and gig.driver}
        sending: dict[str, int] = defaultdict(int)
        actions: list[Action] = []
        for gig in list(books.gigs.values()):
            waiting = books.open_offers[gig.id]
            for driver_id in [d for d, offer in waiting.items() if offer["at"] + OPEN_MINUTES + 5 < now]:
                del waiting[driver_id]
            order_id = gig.legs[0][0] if gig.legs else None
            state = books.orders.get(order_id)
            if gig.status != "open" or waiting or state is None or self.arm(order_id) == "control":
                continue
            pickup, delivery = self.place(gig.stops[0]), self.place(gig.stops[-1])
            audience = self.fleet.audience(state, [leg for _, leg in gig.legs])
            pools: dict[str, list[DriverState]] = defaultdict(list)
            for driver_id, driver in books.drivers.items():
                profile = driver.profile
                if driver.offers[now // DAY] + sending[driver_id] >= PER_DRIVER or driver_id in self.asked[order_id]:
                    continue
                if audience["manualLicence"] and profile["licence"] != "manual":
                    continue
                if audience["experienced"] and not (profile["rating"] >= 4.8 and profile["completedGigs"] >= 50):
                    continue
                end = ends.get(driver_id) or (driver.place if driver.free_at >= today else None)
                at_pickup, at_delivery = profile["homePlaceId"] in self.near[pickup], profile["homePlaceId"] in self.near[delivery]
                label = ("chain" if end in self.near[pickup] else "both" if at_pickup and at_delivery else "delivery" if at_delivery
                         else "pickup" if at_pickup else "seen" if driver.last_seen >= today else "far")
                pools[label].append(driver)
            limit = policy.rounds * (2 if state.urgent else 1)
            if self.rounds[order_id] >= limit:
                pools = {"chain": pools["chain"]} if pools.get("chain") else {}
            if not pools:
                continue
            self.rounds[order_id] += 1
            rng = random.Random(f"{policy.seed}:offer:{gig.id}:{self.rounds[order_id]}")
            typical = sum(books.orders[o].request["referenceFeeCents"] / len(books.orders[o].order["legs"]) for o, _ in gig.legs if o in books.orders)
            for _ in range(PER_GIG):
                labels = sorted(label for label, pool in pools.items() if pool)
                if not labels:
                    break
                label = rng.choice(labels)
                driver = pools[label].pop(rng.randrange(len(pools[label])))
                multiple = rng.choice(policy.explore)
                self.asked[order_id].add(driver.profile["id"])
                sending[driver.profile["id"]] += 1
                self.meta[(gig.id, driver.profile["id"])] = {
                    "at": now, "gigId": gig.id, "orderId": order_id, "driverId": driver.profile["id"], "feeCents": max(1, int(typical * multiple)),
                    "multiple": multiple, "class": label, "arm": self.arm(order_id), "round": self.rounds[order_id], "urgent": state.urgent, "late": state.late,
                    "appFeeCents": self.app_fee(gig), "postedAt": gig.posted_at, "answer": None}
                actions.append({"type": "offer", "gigId": gig.id, "driverId": driver.profile["id"], "feeCents": max(1, int(typical * multiple))})
        return actions

    def app_fee(self, gig: GigState) -> int:
        return max((step["feeCents"] for step in gig.schedule if step["at"] <= self.books.now), default=gig.schedule[0]["feeCents"])

    def sent(self, action: Action, result: ActionResult) -> None:
        offer = self.meta.pop((action["gigId"], action["driverId"]), None) or dict(action, at=self.books.now, answer=None)
        if result["ok"]:
            self.books.offer_sent(offer)
        else:
            self.books.offers.append(dict(offer, answer="refused", reason=result["reason"]))
