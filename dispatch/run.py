"""Plays a world with the desk: a practice world step by step, or the final from the live stream."""
from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Callable, Optional

from spread.client import Client, SpreadError, Unreachable, World
from spread.types import DeskEventKind, Score

from .atlas import DAY, Atlas
from .desk import Desk, Policy

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# The events that can need an action. Everything else arrives with the next of these.
WAKE_ON: list[DeskEventKind] = ["price_request", "order_won", "order_changed", "order_cancelled", "visit_failed", "gig_expired", "deadline_close"]


def play_practice(world: World, desk: Desk, on_day: Optional[Callable[[int, Score], None]] = None) -> None:
    """One request a step: the advance carries the outbox, then moves the clock to the next event that can need an action."""
    snapshot = world.snapshot()
    desk.books.now, ends_at = snapshot["now"], snapshot["endsAt"]
    while desk.books.now < ends_at:
        day = desk.books.now // DAY
        actions, desk.outbox = desk.outbox, []
        step = world.advance(until=WAKE_ON, max=min(ends_at, (day + 1) * DAY, max(desk.alarm(), desk.books.now)), actions=actions)
        desk.sent(actions, step["results"])
        for event in step["events"]:
            desk.handle(event)
        desk.books.now = step["now"]
        desk.reconcile()
        if on_day and desk.books.now // DAY > day:
            on_day(day, world.score())


def report(label: str, score: Score) -> None:
    orders = f"{score['wonOrders']:>4} orders  {score['onTimeShare']:6.1%} on time  {score['undeliveredShare']:5.1%} not delivered"
    print(f"{label:<9}  margin €{score['marginCents'] / 100:>11,.2f}  revenue €{score['revenueCents'] / 100:>11,.2f}  {orders}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plays a Spread world with the desk. Set SPREAD_URL and SPREAD_KEY first.")
    parser.add_argument("--level", type=int, choices=range(1, 9), default=8)
    parser.add_argument("--seed")
    parser.add_argument("--board", action="store_true", help="play the next ranking run at the level")
    parser.add_argument("--policy", default="{}", help='JSON overrides, for example {"market": {"price": 1.4}}')
    args = parser.parse_args()
    client = Client()
    world = client.create(level=args.level, seed=args.seed, board=args.board)
    print(f"World {world.id}, level {args.level}.", flush=True)
    desk = Desk(Atlas(client.map()), world.roster(), Policy.of(json.loads(args.policy), seed=args.seed or ""), verbose=True)
    try:
        play_practice(world, desk, lambda day, score: report(WEEKDAYS[day % 7], score))
    except BaseException:
        if not args.board:
            world.delete()
        raise
    score = world.score()
    report("End", score)
    print("Ranked." if score["ranked"] else "Not ranked.")


if __name__ == "__main__":
    main()
