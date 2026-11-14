"""Restart = replay, checked. Plays a seed with the practice loop; at chosen minutes it throws the desk away,
builds a new one with `Desk.rejoin`, and compares every object of the new desk with the one that died:
books, market, fleet, the outbox. The week then goes on with the new desk, and its margin must equal the
margin of a week without restarts, to the cent.

    python -m tools.restart_test --seed halal-01 --restarts 12              # a restart on the same machine: the journal is there
    python -m tools.restart_test --seed halal-01 --restarts 12 --no-journal # a new machine: the world's log and snapshot only
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import random
import sys
import time
from collections import defaultdict
from typing import Any

from spread.client import Client, SpreadError

from dispatch.atlas import DAY, HOUR, Atlas, clock
from dispatch.desk import Desk, Policy
from dispatch.run import play_practice
from tools.harness import RUNS, Slot, create

STATIC = ("Atlas", "Random", "Pattern", "TextIOWrapper")  # objects that hold no state of the week
OURS = ("journal", "verbose", "careful")  # how a desk was started, not what it knows


def tree(thing: Any, seen: set[int], name: str = "") -> Any:
    """Any object as plain data, so that two desks can be compared without knowing what their parts hold."""
    if isinstance(thing, (str, int, float, bool, type(None))):
        return thing
    if isinstance(thing, (set, frozenset)) or name == "alarms":
        return sorted((tree(item, seen) for item in thing), key=repr)
    if isinstance(thing, (list, tuple)):
        return [tree(item, seen) for item in thing]
    if isinstance(thing, dict):
        items = {str(key): tree(value, seen, str(key)) for key, value in thing.items()}
        return {k: v for k, v in items.items() if v not in (0, None, [], {}, False)} if isinstance(thing, defaultdict) else items  # a read leaves an empty entry
    if type(thing).__name__ in STATIC or not hasattr(thing, "__dict__"):
        return f"<{type(thing).__name__}>"
    if id(thing) in seen:
        return f"<{type(thing).__name__} again>"
    seen.add(id(thing))
    return {key: tree(value, seen, key) for key, value in vars(thing).items() if key not in OURS}


def differences(a: Any, b: Any, path: str = "desk") -> list[str]:
    if isinstance(a, dict) and isinstance(b, dict):
        return [line for key in sorted(set(a) | set(b)) for line in differences(a.get(key, "<absent>"), b.get(key, "<absent>"), f"{path}.{key}")]
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [line for i, (x, y) in enumerate(zip(a, b)) for line in differences(x, y, f"{path}[{i}]")]
    return [] if a == b else [f"{path}: was {json.dumps(a)[:160]}  rebuilt {json.dumps(b)[:160]}"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seed", default="halal-01")
    parser.add_argument("--level", type=int, default=8)
    parser.add_argument("--policy", default="{}")
    parser.add_argument("--restarts", type=int, default=12, help="restarts at random minutes of the working week")
    parser.add_argument("--at", default="", help="or the minutes to restart at, separated by commas")
    parser.add_argument("--no-journal", action="store_true", help="rebuild from the world alone, as on a new machine")
    parser.add_argument("--baseline", default="live-practice", help="the tag of a practice-loop run of this seed without restarts")
    parser.add_argument("--show", type=int, default=6, help="differences to print per restart")
    args = parser.parse_args()
    overrides, client = json.loads(args.policy), Client()
    rng = random.Random(f"restart:{args.seed}")
    minutes = sorted(int(m) for m in args.at.split(",")) if args.at else sorted(rng.randrange(8 * HOUR, 5 * DAY) for _ in range(args.restarts))
    journal = None if args.no_journal else os.path.join(RUNS, f"journal-restart-{args.seed}-{int(time.time())}.jsonl")
    atlas = Atlas(client.map())
    make = lambda roster: Desk(atlas, roster, Policy.of(overrides, seed=args.seed), journal=journal)
    exact = 0
    with Slot() as slot:
        world = create(client, args.level, args.seed)
        slot.hold(world.id)
        try:
            roster = world.roster()
            desk = make(roster)
            for minute in minutes:
                play_practice(world, desk, until=minute)
                rebuilt = make(roster)
                rebuilt.rejoin(world.snapshot(), world.events())
                found = differences(tree(desk, set()), tree(rebuilt, set()))
                exact += not found
                print(f"{clock(desk.books.now)}  restart: {len(desk.books.orders)} orders, {len(desk.books.gigs)} gigs, {len(desk.outbox)} actions unsent  ->  "
                      f"{'the same desk' if not found else f'{len(found)} differences'}", flush=True)
                for item in found[:args.show]:
                    print(f"    {item}", flush=True)
                desk = rebuilt
            play_practice(world, desk)
            score = world.score()
        except BaseException:
            try:
                world.delete()
            except SpreadError:
                pass
            raise
    path = os.path.join(RUNS, args.baseline, f"{args.seed}.json.gz")
    print(f"== {args.seed}: {exact}/{len(minutes)} restarts rebuilt the same desk{' (no journal)' if args.no_journal else ''}")
    print(f"== with restarts:    margin €{score['marginCents'] / 100:,.2f}  on time {score['onTimeShare']:.1%}  won {score['wonOrders']}")
    if os.path.exists(path):
        with gzip.open(path, "rt") as file:
            base = json.load(file)["score"]
        print(f"== without restarts: margin €{base['marginCents'] / 100:,.2f}  on time {base['onTimeShare']:.1%}  won {base['wonOrders']}"
              f"  ->  {'THE SAME WEEK' if base == score else 'a different week'}")
        sys.exit(0 if base == score and (exact == len(minutes) or args.no_journal) else 1)
    print(f"== no run of {args.seed} under runs/{args.baseline}: play it with tools.harness --tag {args.baseline} to compare")


if __name__ == "__main__":
    main()
