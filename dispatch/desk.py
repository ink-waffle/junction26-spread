"""The desk: folds each event into the books, then issues the actions that make the world match the plan."""
from __future__ import annotations

import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from typing import Optional

from spread.types import Action, ActionResult, DeskEvent, DeskSnapshot, DriverProfile, PriceRequest

from .atlas import Atlas, clock
from .books import Books
from .fleet import Fleet, FleetPolicy
from .market import Market, MarketPolicy


@dataclass
class Policy:
    market: MarketPolicy = field(default_factory=MarketPolicy)
    fleet: FleetPolicy = field(default_factory=FleetPolicy)

    @staticmethod
    def of(overrides: Optional[dict] = None, seed: str = "") -> "Policy":
        """The default policy with `{"market": {...}, "fleet": {...}}` overrides, for experiments."""
        overrides = overrides or {}
        def tuples(part: dict) -> dict:
            return {k: tuple(v) if isinstance(v, list) else v for k, v in part.items()}
        return Policy(MarketPolicy(seed=seed, **tuples(overrides.get("market", {}))), FleetPolicy(seed=seed, **tuples(overrides.get("fleet", {}))))


class Desk:
    def __init__(self, atlas: Atlas, roster: list[DriverProfile], policy: Policy, journal: Optional[str] = None, verbose: bool = False):
        self.books = Books(roster)
        self.fleet = Fleet(policy.fleet, self.books, atlas)
        self.market = Market(policy.market, self.books, self.fleet)
        self.outbox: list[Action] = []
        self.pending: set[tuple[str, int]] = set()  # legs whose post is in the outbox or on its way
        self.journal, self.verbose = journal, verbose
        self.careful = False  # the final sets it: an event that the desk cannot read is logged and passed over, not fatal

    def step(self, events: list[DeskEvent], now: int) -> None:
        """One turn, the same in practice and in the final: fold the events, move the clock, plan. The actions wait in the outbox."""
        for event in events:
            self.handle(event)
        self.books.now = max(self.books.now, now)
        self.reconcile()

    def alarm(self) -> int:
        """The minute the desk next wants a turn at when no event comes first: both loops give it one then. A plan that waits says so here."""
        return 10 ** 9

    def take(self) -> list[Action]:
        """Empties the outbox, quotes first: a dealer waits 15 minutes for a price, and no longer."""
        actions, self.outbox = sorted(self.outbox, key=lambda action: action["type"] != "quote"), []
        return actions

    def handle(self, event: DeskEvent) -> None:
        """Folds one event into the books and answers what only this event can trigger."""
        if self.fold(event) and event["kind"] == "price_request":
            self.quote(event["request"])

    def fold(self, event: DeskEvent) -> bool:
        """What an event teaches, with no answer to it: a restart replays the world's log through here. False for a repeat."""
        try:
            if not self.books.observe(event):
                return False
            if event["kind"] == "order_won":
                self.market.learn(event["order"]["id"], event["order"]["option"])
            elif event["kind"] == "order_lost":
                self.market.learn(event["requestId"], None)
        except Exception:
            if not self.careful:
                raise
            traceback.print_exc()
        return True

    def quote(self, request: PriceRequest) -> None:
        self.outbox.append({"type": "quote", "requestId": request["id"], "prices": self.market.quote(request)})

    def reconcile(self) -> None:
        """Makes each touched order's gigs match the plan: post what is missing, reprice what is off."""
        books = self.books
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
                wanted = self.fleet.schedule(state, [leg for owner, leg in gig.legs if owner == order_id])
                if [step["feeCents"] for step in wanted] != [step["feeCents"] for step in gig.schedule]:
                    gig.schedule = wanted
                    self.outbox.append({"type": "reprice", "gigId": gig.id, "schedule": wanted})
            legs = [leg for leg in state.unposted() if (order_id, leg) not in self.pending]
            if legs and state.refusals < 4:
                for plan in self.fleet.plan(state, legs):
                    self.pending.update((order_id, leg) for leg in plan.legs)
                    self.outbox.append({"type": "post", "stops": plan.stops, "audience": plan.audience, "schedule": plan.schedule})
        books.dirty -= dirty

    def sent(self, actions: list[Action], results: list[ActionResult]) -> None:
        """Reads the world's answer to each action, and keeps both in the journal: the world's log never repeats them."""
        books = self.books
        if self.journal and actions:
            try:
                with open(self.journal, "a") as file:
                    file.write(json.dumps({"seq": books.seq, "now": books.now, "actions": actions, "results": results}) + "\n")
            except OSError as error:  # a journal that cannot be written costs the next restart its memory, not this week its desk
                print(f"No journal from here on: {error}", file=sys.stderr, flush=True)
                self.journal = None
        for action, result in zip(actions, results):
            if action["type"] == "post":
                legs = [(s["orderId"], s["leg"]) for s in action["stops"] if s["kind"] == "pickup"]
                self.pending.difference_update(legs)
                if result["ok"]:
                    books.gig_posted(action, result["id"])
                    continue
                for order_id, _ in legs:
                    state = books.orders.get(order_id)
                    if state and "already in a live gig" not in result["reason"]:  # that one a driver booked before we could replace it: its booking puts it back in the books
                        state.refusals += 1
                        state.late = True  # the usual reason is a window that has ended: post without windows
                        books.dirty.add(order_id)
            if result["ok"] and action["type"] == "quote":  # a price is ours only once the world has it
                books.quotes[action["requestId"]] = action["prices"]
            elif result["ok"] and action["type"] == "withdraw":
                books.gig_gone(action["gigId"])
            elif result["ok"] and action["type"] == "reprice" and action["gigId"] in books.gigs:
                books.gigs[action["gigId"]].schedule = action["schedule"]
            if not result["ok"] and self.verbose:
                about = action.get("requestId") or action.get("gigId") or action["stops"][0]["orderId"]
                print(f"{clock(books.now)} refused {action['type']} {about}: {result['reason']}", file=sys.stderr, flush=True)

    def rejoin(self, snapshot: DeskSnapshot, history: list[DeskEvent]) -> None:
        """Rebuilds a new desk in the middle of a week: the world's log and our journal, folded in the order they happened.
        Where the journal is short the snapshot has our gigs, and what the world asked while we were away gets its answer now."""
        books = self.books
        turns = self.journaled()  # none on a new machine: our quotes are then unknown, and the market learns from the answers still to come
        answered = turns[-1]["seq"] if turns else -1  # the last event that we answered and read the world's answer to
        ours = {result["id"] for turn in turns for action, result in zip(turn["actions"], turn["results"]) if action["type"] == "post" and result["ok"]}
        unread = {gig["id"]: gig for gig in snapshot["gigs"] if gig["id"] not in ours}  # gigs whose answer the journal never saw
        changed: dict[str, int] = {}
        journal, verbose, self.journal, self.verbose = self.journal, self.verbose, None, False

        def adopt(gig) -> None:
            del unread[gig["id"]]
            books.gig_posted({"type": "post", "stops": gig["stops"], "audience": gig["audience"], "schedule": gig["schedule"]}, gig["id"], posted_at=gig["postedAt"])

        def recall(turn) -> None:
            books.now = max(books.now, turn["now"])
            self.sent(turn["actions"], turn["results"])

        for event in history:
            while turns and turns[0]["seq"] < event["seq"]:
                recall(turns.pop(0))
            for gig in [g for g in unread.values() if g["postedAt"] < event["at"] or g["id"] == event.get("gigId")]:
                adopt(gig)
            if event["kind"] == "order_changed":
                changed[event["order"]["id"]] = event["seq"]
            self.fold(event)
        for turn in turns:
            recall(turn)
        for gig in list(unread.values()):
            adopt(gig)
        self.journal, self.verbose = journal, verbose
        books.now = max(books.now, snapshot["now"])
        for gig in snapshot["gigs"]:  # an action whose answer we never read: the world's word on our gigs is final
            books.gigs[gig["id"]].schedule = gig["schedule"]
            if gig["status"] == "withdrawn" and books.gigs[gig["id"]].status != "withdrawn":
                books.gig_gone(gig["id"])
        for gig_id in set(books.gigs) - {gig["id"] for gig in snapshot["gigs"]}:  # a journal of some other week
            books.gig_gone(gig_id)
        for order_id, state in books.orders.items():
            state.changed = changed.get(order_id, -1) > answered  # a change that we answered needs no second answer
        books.dirty = {order_id for order_id, state in books.orders.items() if state.undelivered()}
        self.outbox.clear()
        self.pending.clear()
        for request in snapshot["openRequests"]:
            if request["id"] not in books.quotes:
                books.requests[request["id"]] = request
                self.quote(request)
        self.reconcile()

    def journaled(self) -> list[dict]:
        """The journal, oldest first: each batch we sent with the world's answers, and the last event folded before it."""
        turns: list[dict] = []
        if self.journal and os.path.exists(self.journal):
            with open(self.journal) as file:
                for line in file:
                    try:
                        turns.append(json.loads(line))
                    except ValueError:  # the line we were writing when we died
                        break
        return turns
