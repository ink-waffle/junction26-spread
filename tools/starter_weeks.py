"""Plays the kit's starter on our own seeds, so every result of ours has the starter's on the same weeks next to it.

    python -m tools.starter_weeks --seeds tune          # one line per week, and a line in runs/log.jsonl under the tag "starter\""""
from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

from spread import starter
from spread.client import Client

from tools.harness import RUNS, SEEDS, Slot, create, patient


def play(seed: str, level: int) -> dict:
    client = Client()
    with Slot() as slot:
        world = patient(lambda: create(client, level, seed))
        slot.hold(world.id)
        started = time.time()
        try:
            starter.play_practice(world, level)
        except BaseException:
            world.delete()
            raise
    score = patient(world.score)
    return {"seed": seed, "world": world.id, "margin": score["marginCents"] / 100, "revenue": score["revenueCents"] / 100, "onTime": score["onTimeShare"],
            "undelivered": score["undeliveredShare"], "won": score["wonOrders"], "ranked": score["ranked"], "seconds": round(time.time() - started)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seeds", default="tune")
    parser.add_argument("--level", type=int, default=8)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    seeds = SEEDS.get(args.seeds) or args.seeds.split(",")
    with ThreadPoolExecutor(args.workers) as pool:
        results = list(pool.map(lambda seed: play(seed, args.level), seeds))
    for r in results:
        print(f"{r['seed']:<10} margin €{r['margin']:>10,.0f}  on time {r['onTime']:6.1%}  undeliv {r['undelivered']:5.1%}  won {r['won']:>4}  {'RANKED' if r['ranked'] else 'not ranked'}  {r['seconds']}s")
    n = len(results)
    print(f"== starter  mean margin €{sum(r['margin'] for r in results) / n:,.0f}  mean on time {sum(r['onTime'] for r in results) / n:.1%}  ranked {sum(r['ranked'] for r in results)}/{n}")
    with open(os.path.join(RUNS, "log.jsonl"), "a") as file:
        file.write(json.dumps({"tag": f"starter-{args.seeds}", "policy": "kit starter", "level": args.level, "at": time.strftime("%m-%d %H:%M"), "results": results}) + "\n")


if __name__ == "__main__":
    main()
