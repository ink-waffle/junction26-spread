"""Every working day of a seed's week under our own history: the price at which each dealer stops buying, by bisection on copies.

    python -m tools.probe_week halal-01,halal-02 9      # then: python -m tools.surprises money

Our desk plays the week as the harness does (stride 14). At each midnight the world is forked, and the copies play the day once per pass:
every request quoted on its fastest option at the middle of its bracket, starting from what the market believed that night. Saved per seed,
with our own quotes and answers, the fleet's cost of each option and the market's level at the minute of each quote: runs/bisect/week-<seed>.json."""
from __future__ import annotations

import json
import math
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from spread.client import Client, SpreadError

from dispatch.atlas import DAY, Atlas
from dispatch.desk import Desk, Policy
from dispatch.run import play_practice
from tools.harness import RUNS, Slot, create
from tools.probe import DECLINE, FIRST, HIGHEST, LOWEST
from tools.probe_tuesday import decline, stride

FOLDER = os.path.join(RUNS, "bisect")
LAST, STEP, FINE = 18 * 60 + 30, 0.10, 0.008  # the last answers of a day come at 18:15; the first stride away from the guess; a bracket this narrow is known


def copy(parent):
    """A fork of the world, as soon as the team has room for one: the eight practice worlds are shared with every other run."""
    for attempt in range(120):
        try:
            return parent.fork()
        except SpreadError as error:
            if error.status != 409 or attempt == 119:
                raise
            time.sleep(3)


def guess(bracket: dict) -> Optional[float]:
    """The next log multiple to try: the start, then strides that double until both sides are known, then the middle. None when narrow enough."""
    lo, hi = bracket.get("lo"), bracket.get("hi")
    if lo is None and hi is None:
        return bracket["start"]
    if lo is not None and hi is not None:
        return None if hi - lo <= FINE else (lo + hi) / 2
    x = lo + STEP * 2 ** (bracket["tries"] - 1) if hi is None else hi - STEP * 2 ** (bracket["tries"] - 1)
    return None if (hi is None and lo >= HIGHEST) or (lo is None and hi <= LOWEST) else min(HIGHEST, max(LOWEST, x))


def bisect(parent, desk: Desk, state: dict, day: int, passes: int) -> None:
    """Halves the bracket of every request of the day, once per copy of the world."""
    for _ in range(passes):
        asked = {}

        def quote(request):
            option = request["options"][0]
            bracket = state["brackets"].setdefault(request["id"], {"tries": 0, "start": desk.market.level(request, option)[0]})
            x = guess(bracket)
            if x is None:
                return decline(request)
            price = int(option["listPriceCents"] * math.exp(x) + 0.5)
            asked[request["id"]] = math.log(price / option["listPriceCents"])
            return {option["kind"]: price}

        answers = {}
        for attempt in range(4):  # another harness that finds no free slot deletes worlds nobody holds, and can catch a copy before we hold it
            with Slot() as slot:
                fork = copy(parent)
                slot.hold(fork.id)
                fork._last_seq = parent._last_seq  # the copy's log starts with the parent's: read only what is new
                try:
                    answers = stride(fork, quote, day * DAY + FIRST, day * DAY + LAST)
                    break
                except SpreadError as error:
                    if error.status != 404 or attempt == 3:
                        raise
                    asked.clear()
                finally:
                    try:
                        fork.delete()
                    except SpreadError:
                        pass
        for request_id, bought in answers.items():
            if request_id in asked:
                bracket, x = state["brackets"][request_id], asked[request_id]
                bracket["tries"] += 1
                if bought:
                    bracket["lo"] = max(x, bracket.get("lo", x))
                else:
                    bracket["hi"] = min(x, bracket.get("hi", x))


def week(seed: str, passes: int, overrides: dict) -> str:
    path = os.path.join(FOLDER, f"week-{seed}.json")
    if os.path.exists(path):
        return f"{seed}: already there"
    client = Client()
    state = {"seed": seed, "policy": overrides, "requests": {}, "brackets": {}, "asked": {}}
    with Slot() as slot:
        parent = create(client, 8, seed)
        slot.hold(parent.id)
        try:
            desk = Desk(Atlas(client.map()), parent.roster(), Policy.of(overrides, seed=seed))
            quote = desk.quote

            def recording(request):  # what the desk knew at the minute of its quote
                options = request["options"]
                state["asked"][request["id"]] = {"cost": [desk.fleet.cost(request, o) for o in options], "level": [desk.market.level(request, o) for o in options],
                                                 "trust": desk.books.on_time[request["dealerId"]]}
                quote(request)

            desk.quote = recording
            for day in range(5):
                play_practice(parent, desk, until=day * DAY, stride=14)
                bisect(parent, desk, state, day, passes)
            play_practice(parent, desk, until=5 * DAY, stride=14)
            books = desk.books
            state.update(requests=books.requests, quotes=books.quotes, outcomes=books.outcomes)
        finally:
            try:
                parent.delete()
            except SpreadError:
                pass
    os.makedirs(FOLDER, exist_ok=True)
    with open(path + ".tmp", "w") as file:
        json.dump(state, file)
    os.replace(path + ".tmp", path)
    known = sum(1 for b in state["brackets"].values() if "lo" in b and "hi" in b and b["hi"] - b["lo"] < 0.02)
    return f"{seed}: {len(state['brackets'])} requests probed, {known} thresholds within 2%"


def patient(seed: str, passes: int, overrides: dict) -> str:
    for attempt in range(3):
        try:
            return week(seed, passes, overrides)
        except Exception as error:  # the server was slow or away: the worlds are gone, start the seed again
            print(f"{seed}: {type(error).__name__}: {error}", flush=True)
    return f"{seed}: gave up"


if __name__ == "__main__":
    seeds, passes = sys.argv[1].split(","), int(sys.argv[2]) if len(sys.argv) > 2 else 9
    workers, overrides = int(sys.argv[3]) if len(sys.argv) > 3 else 2, json.loads(sys.argv[4]) if len(sys.argv) > 4 else {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for line in pool.map(lambda seed: patient(seed, passes, overrides), seeds):
            print(line, flush=True)
