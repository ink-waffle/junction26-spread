"""Probes the dealers of a seed's Monday: for every request and each of its options, the price at which its dealer stops buying.

    python -m tools.probe --seeds tune,wide --passes 16     # bisects; resumes from runs/bisect/<seed>.json
    python -m tools.probe --seeds tune --menus 3            # then: two options at once, each a random step under its threshold: which one is bought?

A practice world is deterministic, and on Monday nothing we do feeds back: the competitor moves each morning, trust needs deliveries,
dissatisfaction a missed deadline. So a pass plays only Monday, quotes every request on one option at the middle of that option's bracket,
posts no gig and deletes the world; the dealer's answer halves the bracket. A request's options take turns, the least known first."""
from __future__ import annotations

import argparse
import json
import math
import os
import random
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from spread.client import Client, SpreadError
from spread.types import PriceRequest

from tools.harness import RUNS, SEEDS, Slot, create

FOLDER = os.path.join(RUNS, "bisect")
START, STEP, FINE = math.log(1.35), 0.16, 0.006  # the first guess (log multiple of list; 0.085 less per slower option), the first stride, and when a bracket is narrow enough
LOWEST, HIGHEST, DECLINE = math.log(0.5), math.log(4.0), 10.0
FIRST, LAST, STRIDE = 7 * 60 + 50, 23 * 60, 14  # Monday's requests come from 08:00 into the evening; a dealer waits 15 minutes
UNDER = (0.02, 0.05, 0.10, 0.18)  # menus: how far under its threshold an option is offered


def monday(seed: str, quote: Callable[[PriceRequest], dict[str, int]], level: int = 8) -> dict[str, Optional[str]]:
    """Plays Monday of the seed with these quotes and no gigs, then deletes the world: the option each dealer bought, or None."""
    client, answers = Client(), {}
    with Slot() as slot:
        world = create(client, level, seed)
        slot.hold(world.id)
        try:
            actions, now = [], world.advance(to=FIRST)["now"]
            while now < LAST:  # strides one minute shorter than a dealer's patience: every request is answered in the next call
                step = world.advance(by=STRIDE, actions=actions)
                actions, now = [], step["now"]
                for event in step["events"]:
                    if event["kind"] == "price_request":
                        actions.append({"type": "quote", "requestId": event["request"]["id"], "prices": quote(event["request"])})
                    elif event["kind"] == "order_won":
                        answers[event["order"]["id"]] = event["order"]["option"]
                    elif event["kind"] == "order_lost":
                        answers[event["requestId"]] = None
        finally:
            try:
                world.delete()
            except SpreadError:
                pass
    return answers


def guess(bracket: dict, index: int) -> Optional[float]:
    """The next log multiple to try for an option: its guess, then strides that double until both sides are known, then the middle. None when narrow enough."""
    lo, hi = bracket.get("lo"), bracket.get("hi")
    if lo is None and hi is None:
        return START - 0.085 * index
    if lo is not None and hi is not None:
        return None if hi - lo <= FINE else (lo + hi) / 2
    stride = STEP * 2 ** (bracket["tries"] - 1)
    x = lo + stride if hi is None else hi - stride
    return None if (hi is None and lo >= HIGHEST) or (lo is None and hi <= LOWEST) else min(HIGHEST, max(LOWEST, x))


def halve(seed: str, state: dict) -> None:
    """One bisection pass: every request quoted on its least known option at that option's next guess."""
    asked: dict[str, tuple[str, float]] = {}

    def quote(request: PriceRequest) -> dict[str, int]:
        state["requests"][request["id"]] = request
        brackets = state["brackets"].setdefault(request["id"], {option["kind"]: {"tries": 0} for option in request["options"]})
        unknown = [(brackets[o["kind"]]["tries"], i, o) for i, o in enumerate(request["options"]) if guess(brackets[o["kind"]], i) is not None]
        if not unknown:
            return {request["options"][0]["kind"]: int(request["options"][0]["listPriceCents"] * DECLINE)}
        _, index, option = min(unknown, key=lambda item: item[:2])
        price = int(option["listPriceCents"] * math.exp(guess(brackets[option["kind"]], index)) + 0.5)
        asked[request["id"]] = (option["kind"], math.log(price / option["listPriceCents"]))
        return {option["kind"]: price}

    for request_id, bought in monday(seed, quote).items():
        if request_id in asked:
            kind, x = asked[request_id]
            bracket = state["brackets"][request_id][kind]
            bracket["tries"] += 1
            if bought:
                bracket["lo"] = max(x, bracket.get("lo", x))
            else:
                bracket["hi"] = min(x, bracket.get("hi", x))
    state["passes"] += 1


def menu(seed: str, state: dict, turn: int) -> list[dict]:
    """One menu pass: each request with two bracketed options is offered both, each a random step under its own threshold."""
    offered = {}

    def quote(request: PriceRequest) -> dict[str, int]:
        brackets = state["brackets"].get(request["id"], {})
        known = [o for o in request["options"] if {"lo", "hi"} <= set(brackets.get(o["kind"], {})) and brackets[o["kind"]]["hi"] - brackets[o["kind"]]["lo"] <= 3 * FINE]
        if len(known) < 2:
            return {request["options"][0]["kind"]: int(request["options"][0]["listPriceCents"] * DECLINE)}
        rng = random.Random(f"{seed}:{request['id']}:{turn}")
        pair = rng.sample(known, 2) if len(known) > 2 else known
        under = {o["kind"]: rng.choice(UNDER) for o in pair}
        prices = {o["kind"]: int(o["listPriceCents"] * math.exp(brackets[o["kind"]]["lo"]) * (1 - under[o["kind"]])) for o in pair}
        offered[request["id"]] = {"id": request["id"], "under": under, "prices": prices}
        return prices

    answers = monday(seed, quote)
    return [{**row, "bought": answers.get(row["id"])} for row in offered.values()]


def probe(seed: str, passes: int, menus: int) -> str:
    path = os.path.join(FOLDER, f"{seed}.json")
    state = {"seed": seed, "passes": 0, "requests": {}, "brackets": {}, "menus": []}
    if os.path.exists(path):
        with open(path) as file:
            state = {"menus": [], **json.load(file)}
    while state["passes"] < passes or len(state["menus"]) < menus:
        if state["passes"] < passes:
            halve(seed, state)
        else:
            state["menus"].append(menu(seed, state, len(state["menus"])))
        with open(path + ".tmp", "w") as file:
            json.dump(state, file)
        os.replace(path + ".tmp", path)
    options = [b for request in state["brackets"].values() for b in request.values()]
    known = [b for b in options if "lo" in b and "hi" in b]
    narrow = sum(1 for b in known if b["hi"] - b["lo"] <= 2 * FINE)
    return f"{seed}: {state['passes']} passes, {len(state['requests'])} requests, {len(options)} options, both sides known {len(known)}, within {2 * FINE:.1%}: {narrow}, menu passes {len(state['menus'])}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--seeds", default="tune", help="named sets (tune, wide, quick) or seeds, separated by commas; never hold")
    parser.add_argument("--passes", type=int, default=16)
    parser.add_argument("--menus", type=int, default=0)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    seeds = [seed for name in args.seeds.split(",") for seed in SEEDS.get(name, [name])]
    os.makedirs(FOLDER, exist_ok=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for line in pool.map(lambda seed: probe(seed, args.passes, args.menus), seeds):
            print(line, flush=True)


if __name__ == "__main__":
    main()
