"""Labels notes: plays a world that wins every request and moves no car, and saves the reveal's truth of each won car.

    python -m tools.label --tag notes-label --seeds wide      # runs/notes-label/<seed>.json.gz, in the harness's format
    python -m tools.label --tag notes-val1 --seeds nv-01,nv-02

It quotes every option at half the list price and posts no gig, so a week costs ~1,050 requests and one practice slot for
half a minute. Score a reader on the result with tools/notes_eval.py."""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed

from spread.client import Client, SpreadError

from tools.harness import RUNS, SEEDS, Slot, create


def label(tag: str, seed: str, level: int, price: float) -> str:
    path = os.path.join(RUNS, tag, f"{seed}.json.gz")
    if os.path.exists(path):
        return f"{seed:<10} already labelled"
    client = Client()
    with Slot() as slot:
        world = create(client, level, seed)
        slot.hold(world.id)
        try:
            ends_at, now, actions = world.snapshot()["endsAt"], 0, []
            while now < ends_at:
                step = world.advance(until=["price_request"], max=ends_at, actions=actions)
                now = step["now"]
                actions = [{"type": "quote", "requestId": e["request"]["id"],
                            "prices": {o["kind"]: max(100, int(o["listPriceCents"] * price)) for o in e["request"]["options"]}}
                           for e in step["events"] if e["kind"] == "price_request"]
        except BaseException:
            try:
                world.delete()
            except SpreadError:
                pass
            raise
    reveal, events = world.reveal(), world.events()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with gzip.open(path + ".tmp", "wt") as file:
        json.dump({"seed": seed, "level": level, "worldId": world.id, "policy": {"label": price}, "events": events, "reveal": reveal}, file)
    os.replace(path + ".tmp", path)
    return f"{seed:<10} won {len(reveal['orders'])}/{len(reveal['requests'])} requests"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--tag", default="notes-label")
    parser.add_argument("--seeds", default="wide", help="a named set (tune, hold, wide, quick) or seeds separated by commas")
    parser.add_argument("--level", type=int, default=8)
    parser.add_argument("--price", type=float, default=0.5, help="quote, as a multiple of the list price: 0.5 won every request of 80 worlds")
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    seeds = SEEDS.get(args.seeds) or args.seeds.split(",")
    with ProcessPoolExecutor(max_workers=min(args.workers, len(seeds))) as pool:
        futures = {pool.submit(label, args.tag, seed, args.level, args.price): seed for seed in seeds}
        for future in as_completed(futures):
            try:
                print(future.result(), flush=True)
            except Exception as error:
                print(f"{futures[future]:<10} FAILED: {type(error).__name__}: {error}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
