"""Plays our ranking runs of the current round at a level, one after another, and logs each to runs/board.jsonl.

    python -m tools.board               the round's remaining runs at level 8
    python -m tools.board --resume ID   picks up a ranking run whose desk died: it rejoins from the log and its journal

A ranking run counts whatever happens, so the desk keeps a journal and is never deleted here."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time

from spread.client import Client, SpreadError, World

from dispatch.atlas import Atlas
from dispatch.desk import Desk, Policy
from tools.harness import RUNS, Slot, patient, play_through


def play(client: Client, world: World, level: int, overrides: dict, rejoin: bool) -> dict:
    atlas, roster, journal = Atlas(patient(client.map)), patient(world.roster), os.path.join(RUNS, f"journal-{world.id}.jsonl")
    new_desk = lambda: Desk(atlas, roster, Policy.of(overrides, seed=world.id), journal=journal, verbose=True)
    play_through(world, new_desk, away=rejoin)
    score = patient(world.score)
    commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    row = {"at": time.strftime("%m-%d %H:%M"), "world": world.id, "level": level, "commit": commit, "policy": overrides, "margin": score["marginCents"] / 100,
           "onTime": score["onTimeShare"], "won": score["wonOrders"], "ranked": score["ranked"]}
    with open(os.path.join(RUNS, "board.jsonl"), "a") as file:
        file.write(json.dumps(row) + "\n")
    print(f"{world.id}  margin €{row['margin']:>10,.0f}  on time {row['onTime']:6.1%}  won {row['won']:>4}  {'RANKED' if row['ranked'] else 'not ranked'}", flush=True)
    return row


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--level", type=int, default=8)
    parser.add_argument("--policy", default="{}")
    parser.add_argument("--resume", help="the id of a ranking run that has not ended")
    args = parser.parse_args()
    client, overrides, rows = Client(), json.loads(args.policy), []
    for _ in range(5):
        with Slot() as slot:
            try:
                world = client.world(args.resume) if args.resume else client.create(level=args.level, board=True)
            except SpreadError as error:
                print(f"no further ranking run: {error}")
                break
            slot.hold(world.id)
            print(f"ranking run {world.id}", flush=True)
            rows.append(play(client, world, args.level, overrides, rejoin=bool(args.resume)))
            args.resume = None
    if rows:
        print(f"== {len(rows)} runs  total €{sum(r['margin'] for r in rows):,.0f}  on time {min(r['onTime'] for r in rows):.1%} worst  ranked {sum(r['ranked'] for r in rows)}/{len(rows)}")


if __name__ == "__main__":
    main()
