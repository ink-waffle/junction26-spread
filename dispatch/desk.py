"""The desk: folds each event into the books, then issues the actions that make the world match the plan."""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

from spread.types import Action, ActionResult, DeskEvent, DeskSnapshot, DriverProfile, PriceRequest

from .atlas import Atlas, clock
from .books import LIVE, Books
from .fleet import Fleet, FleetPolicy
from .market import Market, MarketPolicy
from .offers import Offers, OffersPolicy


@dataclass
class Policy:
    market: MarketPolicy = field(default_factory=MarketPolicy)
    fleet: FleetPolicy = field(default_factory=FleetPolicy)
    offers: OffersPolicy = field(default_factory=OffersPolicy)

    @staticmethod
    def of(overrides: Optional[dict] = None, seed: str = "") -> "Policy":
        """The default policy with `{"market": {...}, "fleet": {...}}` overrides, for experiments."""
        overrides = overrides or {}
        def tuples(part: dict) -> dict:
            return {k: tuple(v) if isinstance(v, list) else v for k, v in part.items()}
        return Policy(MarketPolicy(seed=seed, **tuples(overrides.get("market", {}))), FleetPolicy(seed=seed, **tuples(overrides.get("fleet", {}))),
                      OffersPolicy(seed=seed, **tuples(overrides.get("offers", {}))))


class Desk:
    def __init__(self, atlas: Atlas, roster: list[DriverProfile], policy: Policy, journal: Optional[str] = None, verbose: bool = False):
        self.books = Books(roster)
        self.fleet = Fleet(policy.fleet, self.books, atlas)
        self.market = Market(policy.market, self.books, self.fleet)
        self.offers = Offers(policy.offers, self.books, self.fleet, atlas)
        self.outbox: list[Action] = []
        self.pending: set[tuple[str, int]] = set()  # legs whose post is in the outbox or on its way
        self.journal, self.verbose = journal, verbose

    def handle(self, event: DeskEvent) -> None:
        """Folds one event into the books and answers what only this event can trigger."""
        self.books.observe(event)
        if event["kind"] == "price_request":
            self.quote(event["request"])
        elif event["kind"] == "order_won":
            self.market.learn(event["order"]["id"], event["order"]["option"])
        elif event["kind"] == "order_lost":
            self.market.learn(event["requestId"], None)

    def quote(self, request: PriceRequest) -> None:
        prices = self.market.quote(request)
        self.books.quotes[request["id"]] = prices
        self.outbox.append({"type": "quote", "requestId": request["id"], "prices": prices})
        if self.journal:
            with open(self.journal, "a") as file:
                file.write(json.dumps({"requestId": request["id"], "prices": prices}) + "\n")

    def reconcile(self) -> None:
        """Makes each touched order's gigs match the plan: post what is missing, reprice what is off."""
        books = self.books
        for action in self.offers.pairs():
            self.pending.update((s["orderId"], s["leg"]) for s in action.get("stops", []))
            self.outbox.append(action)
        dirty, books.dirty = books.dirty, set()
        for order_id in sorted(dirty):
            state = books.orders.get(order_id)
            if state is None:
                continue
            open_gigs = [books.gigs[g] for g in dict.fromkeys(state.gig_of.values()) if books.gigs[g].status == "open"]
            if state.changed:  # the dealer moved the car or its hours: an open gig carries the old windows
                state.changed = False
                for gig in open_gigs:
                    self.outbox.append({"type": "withdraw", "gigId": gig.id})
                    books.gig_gone(gig.id)
                open_gigs = []
            for gig in open_gigs:
                if gig.shared:  # its fee belongs to the pair, not to this order
                    continue
                wanted = self.fleet.schedule(state, [leg for owner, leg in gig.legs if owner == order_id])
                if wanted[-1]["feeCents"] != gig.schedule[-1]["feeCents"]:
                    gig.schedule = wanted
                    self.outbox.append({"type": "reprice", "gigId": gig.id, "schedule": wanted})
            legs = [leg for leg in state.unposted() if (order_id, leg) not in self.pending]
            if legs and state.refusals < 4 and not self.offers.holds(state):
                for plan in self.fleet.plan(state, legs):
                    self.pending.update((order_id, leg) for leg in plan.legs)
                    self.outbox.append({"type": "post", "stops": plan.stops, "audience": plan.audience, "schedule": self.offers.opening(state, plan.schedule)})
        books.dirty -= dirty
        self.outbox += self.offers.act()

    def alarm(self) -> int:
        """The minute the desk next wants to act at when no event comes first."""
        return self.offers.alarm(posting=bool(self.pending))

    def sent(self, actions: list[Action], results: list[ActionResult]) -> None:
        """Reads the world's answer to each action: the id of a new gig, or why it refused."""
        for action, result in zip(actions, results):
            if action["type"] == "post":
                legs = [(s["orderId"], s["leg"]) for s in action["stops"] if s["kind"] == "pickup"]
                self.pending.difference_update(legs)
                if result["ok"]:
                    self.books.gig_posted(action, result["id"])
                    continue
                if len({order_id for order_id, _ in legs}) > 1:
                    self.offers.refused([order_id for order_id, _ in legs])
                    legs = []
                for order_id, _ in legs:
                    state = self.books.orders.get(order_id)
                    if state:
                        state.refusals += 1
                        state.late = True  # the usual reason is a window that has ended: post without windows
                        self.books.dirty.add(order_id)
            if action["type"] == "offer":
                self.offers.sent(action, result)
            if not result["ok"] and self.verbose:
                print(f"{clock(self.books.now)} refused {action['type']}: {result['reason']}", file=sys.stderr, flush=True)

    def rejoin(self, snapshot: DeskSnapshot, history: list[DeskEvent]) -> None:
        """Rebuilds the books after a restart: replays the log through the same fold, with our gigs from the snapshot and our quotes from the journal."""
        books = self.books
        if self.journal and os.path.exists(self.journal):
            with open(self.journal) as file:
                books.quotes = {row["requestId"]: row["prices"] for row in map(json.loads, file)}
        waiting = {gig["id"]: gig for gig in snapshot["gigs"]}

        def register(gig) -> None:
            del waiting[gig["id"]]
            books.gig_posted({"type": "post", "stops": gig["stops"], "audience": gig["audience"], "schedule": gig["schedule"]}, gig["id"], posted_at=gig["postedAt"])

        for event in history:
            for gig in [g for g in waiting.values() if g["postedAt"] < event["at"] or g["id"] == event.get("gigId")]:
                register(gig)
            books.observe(event)
            if event["kind"] == "order_won":
                self.market.learn(event["order"]["id"], event["order"]["option"])
            elif event["kind"] == "order_lost":
                self.market.learn(event["requestId"], None)
        for gig in list(waiting.values()):
            register(gig)
        books.now = snapshot["now"]
        for order in snapshot["orders"]:  # the snapshot is the truth where the replay and the world could differ
            if order["id"] in books.orders:
                books.orders[order["id"]].order = order
        for gig in snapshot["gigs"]:
            mine = books.gigs[gig["id"]]
            mine.status, mine.driver, mine.schedule = gig["status"], gig["driverId"], gig["schedule"]
            for order_id, leg in mine.legs:
                state = books.orders.get(order_id)
                if state is None:
                    continue
                if gig["status"] in LIVE and state.order["deliveredAt"][leg] is None:
                    state.gig_of[leg] = gig["id"]
                elif state.gig_of.get(leg) == gig["id"]:
                    del state.gig_of[leg]
        books.dirty = {order_id for order_id, state in books.orders.items() if state.undelivered()}
        self.outbox.clear()
        for request in snapshot["openRequests"]:
            if request["id"] not in books.quotes:
                books.requests[request["id"]] = request
                self.quote(request)
        self.reconcile()
