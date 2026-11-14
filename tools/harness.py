"""Runs one policy on several seeds in parallel and prints margin, on-time share and what drove them.

    python -m tools.harness --tag flat10 --seeds tune --policy '{"fleet": {"fee": 1.0}}'

Every run is saved to runs/<tag>/<seed>.json.gz (score, policy, quotes, events, reveal, roster) for study.
Any number of harness processes can run at once: they share the team's 8 practice slots through .slots/."""
from __future__ import annotations

import argparse
import fcntl
import gzip
import json
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed

from spread.client import Client, SpreadError

from dispatch.atlas import Atlas
from dispatch.desk import Desk, Policy
from dispatch.run import play_practice

ROOT = os.environ.get("SPREAD_SHARED") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # runs/ and .slots/ are shared by all worktrees
SLOTS, RUNS = os.path.join(ROOT, ".slots"), os.path.join(ROOT, "runs")
SEEDS = {
    "tune": [f"halal-{i:02d}" for i in range(1, 9)],
    "hold": [f"halal-{i:02d}" for i in range(9, 17)],
    "wide": [f"halal-{i:02d}" for i in range(17, 33)],
    "quick": [f"halal-{i:02d}" for i in range(1, 5)],
}


class Slot:
    """One of the team's 8 unfinished practice worlds, held through a file lock that dies with the process."""

    def __enter__(self) -> "Slot":
        os.makedirs(SLOTS, exist_ok=True)
        while True:
            for i in range(8):
                file = open(os.path.join(SLOTS, f"{i}.lock"), "a+")
                try:
                    fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    self.file = file
                    return self
                except OSError:
                    file.close()
            time.sleep(0.5)

    def hold(self, world_id: str) -> None:
        self.file.seek(0)
        self.file.truncate()
        self.file.write(world_id)
        self.file.flush()

    def __exit__(self, *_) -> None:
        self.hold("")
        self.file.close()


def held_worlds() -> set[str]:
    """The worlds that a live harness process plays now."""
    held = set()
    for name in os.listdir(SLOTS) if os.path.isdir(SLOTS) else []:
        with open(os.path.join(SLOTS, name), "a+") as file:
            try:
                fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:  # locked: its owner is alive
                file.seek(0)
                held.add(file.read().strip())
    return held


def delete_orphans(client: Client) -> int:
    """Deletes unfinished practice worlds that no live harness holds. Ranking runs are never touched."""
    held, deleted = held_worlds(), 0
    for world in client.worlds():
        if not world["ended"] and world["kind"] == "practice" and world["boardRun"] is None and world["worldId"] not in held:
            client.world(world["worldId"]).delete()
            deleted += 1
    return deleted


def create(client: Client, level: int, seed: str):
    for attempt in range(20):
        try:
            return client.create(level=level, seed=seed)
        except SpreadError as error:
            if error.status != 409:
                raise
            delete_orphans(client)
            time.sleep(2 + attempt)
    raise SystemExit("no practice slot became free")


def play(tag: str, seed: str, level: int, overrides: dict, save: bool) -> dict:
    client = Client()
    with Slot() as slot:
        world = create(client, level, seed)
        slot.hold(world.id)
        started = time.time()
        try:
            roster = world.roster()
            desk = Desk(Atlas(client.map()), roster, Policy.of(overrides, seed=seed))
            play_practice(world, desk)
            score = world.score()
        except BaseException:
            try:
                world.delete()
            except SpreadError:
                pass
            raise
    events = world.events()
    summary = summarise(seed, world.id, score, desk, events, time.time() - started)
    if save:
        folder = os.path.join(RUNS, tag)
        os.makedirs(folder, exist_ok=True)
        with gzip.open(os.path.join(folder, f"{seed}.json.gz"), "wt") as file:
            json.dump({"seed": seed, "level": level, "worldId": world.id, "policy": overrides, "summary": summary, "score": score,
                       "quotes": desk.books.quotes, "roster": roster, "events": events, "gigs": world.snapshot()["gigs"], "reveal": world.reveal()}, file)
    return summary


def summarise(seed: str, world_id: str, score: dict, desk: Desk, events: list, seconds: float) -> dict:
    books, ledger = desk.books, defaultdict(int)
    for event in events:
        if event["kind"] == "ledger":
            ledger[event["line"]["kind"]] += event["line"]["cents"]
    won = [e["order"] for e in events if e["kind"] == "order_won"]
    list_price = {r["id"]: {o["kind"]: o["listPriceCents"] for o in r["options"]} for r in books.requests.values()}
    price_multiple = [o["priceCents"] / list_price[o["id"]][o["option"]] for o in won if o["id"] in list_price]
    booked = [e for e in events if e["kind"] == "gig_booked"]
    typical = {g.id: sum(books.requests[o]["referenceFeeCents"] / len(books.requests[o]["legs"]) for o, _ in g.legs if o in books.requests) for g in books.gigs.values()}
    fee_multiple = [e["feeCents"] / typical[e["gigId"]] for e in booked if typical.get(e["gigId"])]
    mean = lambda xs: sum(xs) / len(xs) if xs else 0.0
    return {
        "seed": seed, "world": world_id, "margin": score["marginCents"] / 100, "revenue": score["revenueCents"] / 100, "onTime": score["onTimeShare"],
        "undelivered": score["undeliveredShare"], "won": score["wonOrders"], "requests": len(books.requests), "ranked": score["ranked"],
        "price": mean(price_multiple), "fee": mean(fee_multiple), "fees": ledger["driver_fee"] / 100, "refunds": (ledger["late_refund"] + ledger["undelivered_penalty"]) / 100,
        "other": (ledger["failed_visit"] + ledger["release_fee"] + ledger["waiting"] + ledger["fine"]) / 100,
        "drops": sum(1 for e in events if e["kind"] == "gig_dropped"), "failed": sum(1 for e in events if e["kind"] == "visit_failed"), "seconds": round(seconds),
    }


def line(s: dict) -> str:
    return (f"{s['seed']:<10} margin €{s['margin']:>10,.0f}  on time {s['onTime']:6.1%}  undeliv {s['undelivered']:5.1%}  won {s['won']:>4}/{s['requests']:<4}  "
            f"price x{s['price']:.2f}  fee x{s['fee']:.2f}  fees €{-s['fees']:>8,.0f}  refunds €{-s['refunds']:>7,.0f}  other €{-s['other']:>5,.0f}  "
            f"drops {s['drops']:>3}  failed {s['failed']:>3}  {'RANKED' if s['ranked'] else 'not ranked'}  {s['seconds']}s")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--tag", required=True, help="a name for this version; runs are saved under runs/<tag>/")
    parser.add_argument("--seeds", default="tune", help="a named set (tune, hold, wide, quick) or seeds separated by commas")
    parser.add_argument("--level", type=int, default=8)
    parser.add_argument("--policy", default="{}", help="JSON overrides of the default policy")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--clean", action="store_true", help="only delete orphaned practice worlds")
    args = parser.parse_args()
    if args.clean:
        print(f"deleted {delete_orphans(Client())} orphaned worlds")
        return
    seeds = SEEDS.get(args.seeds) or args.seeds.split(",")
    overrides = json.loads(args.policy)
    results = []
    with ProcessPoolExecutor(max_workers=min(args.workers, len(seeds))) as pool:
        futures = {pool.submit(play, args.tag, seed, args.level, overrides, not args.no_save): seed for seed in seeds}
        for future in as_completed(futures):
            try:
                results.append(future.result())
                print(line(results[-1]), flush=True)
            except Exception as error:
                print(f"{futures[future]:<10} FAILED: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
    if results:
        n = len(results)
        print(f"== {args.tag}  {args.policy}\n== mean margin €{sum(r['margin'] for r in results) / n:,.0f}  min on time {min(r['onTime'] for r in results):.1%}  "
              f"mean on time {sum(r['onTime'] for r in results) / n:.1%}  ranked {sum(r['ranked'] for r in results)}/{n}  "
              f"ranked-only mean €{sum(r['margin'] for r in results if r['ranked']) / max(1, sum(r['ranked'] for r in results)):,.0f}", flush=True)
        with open(os.path.join(RUNS, "log.jsonl"), "a") as file:
            file.write(json.dumps({"tag": args.tag, "policy": overrides, "level": args.level, "at": time.strftime("%m-%d %H:%M"), "results": results}) + "\n")


if __name__ == "__main__":
    main()
