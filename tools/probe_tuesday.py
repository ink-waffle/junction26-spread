"""Tuesday under two Mondays: what our Monday does to a dealer's Tuesday thresholds (trust, and the competitor's answer to our wins).

    python -m tools.probe_tuesday halal-01,halal-02 8      # then: python -m tools.probe_read

The seed is played to Tuesday 00:00 once with our desk (wins, gigs, deliveries) and once declining everything; each parent world is then
forked, and Tuesday's requests are bisected on the forks, fastest option only. The same request has two thresholds: their difference is our Monday."""
from __future__ import annotations

import collections
import copy
import json
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from spread.client import Client, SpreadError
from dispatch.atlas import DAY, Atlas
from dispatch.desk import Desk, Policy
from dispatch.run import play_practice
from tools.harness import RUNS, Slot, create
from tools.probe import guess, DECLINE, STRIDE, FIRST, LAST

FOLDER = os.path.join(RUNS, "bisect")


def decline(request):
    return {request["options"][0]["kind"]: int(request["options"][0]["listPriceCents"] * DECLINE)}


def stride(world, quote, start, end, watch=None):
    """Quotes every request between two minutes in strides; returns the answers."""
    answers, actions, now = {}, [], world.advance(to=start)["now"]
    while now < end:
        step = world.advance(by=STRIDE, actions=actions)
        actions, now = [], step["now"]
        for event in step["events"]:
            if watch:
                watch(event)
            if event["at"] < start:
                continue
            if event["kind"] == "price_request":
                actions.append({"type": "quote", "requestId": event["request"]["id"], "prices": quote(event["request"])})
            elif event["kind"] == "order_won":
                answers[event["order"]["id"]] = event["order"]["option"]
            elif event["kind"] == "order_lost":
                answers[event["requestId"]] = None
    return answers


def tuesday(seed, kind, passes):
    path = os.path.join(FOLDER, f"tuesday-{kind}-{seed}.json")
    if os.path.exists(path):
        return f"{seed} {kind}: already there"
    client = Client()
    state = {"seed": seed, "parent": kind, "requests": {}, "brackets": {}, "trust": {}, "monday": {}}
    with Slot() as parent_slot:
        parent = create(client, 8, seed)
        parent_slot.hold(parent.id)
        try:
            if kind == "desk":
                desk = Desk(Atlas(client.map()), parent.roster(), Policy.of({}, seed=seed))
                play_practice(parent, desk, until=DAY)
                books = desk.books
                asked, won = collections.Counter(), collections.Counter()
                for rid, request in books.requests.items():
                    asked[request["dealerId"]] += 1
                    won[request["dealerId"]] += bool(books.outcomes.get(rid))
                state["monday"] = {d: {"requests": asked[d], "won": won[d], "trust": books.on_time[d]} for d in asked}
            else:
                books = None
                stride(parent, decline, FIRST, LAST)
                parent.advance(to=DAY)
            for turn in range(passes):
                asked = {}

                def quote(request):
                    state["requests"][request["id"]] = request
                    if request["legs"][0]["delivery"]["privateAddress"]:
                        return decline(request)
                    option = request["options"][0]
                    bracket = state["brackets"].setdefault(request["id"], {"tries": 0})
                    x = guess(bracket, 0)
                    if x is None:
                        return decline(request)
                    price = int(option["listPriceCents"] * math.exp(x) + 0.5)
                    asked[request["id"]] = math.log(price / option["listPriceCents"])
                    return {option["kind"]: price}

                shadow = copy.deepcopy(books) if books is not None and turn == 0 else None

                def watch(event):
                    if shadow is not None:
                        if event["kind"] == "ledger":
                            shadow.observe(event)
                        elif event["kind"] == "price_request":
                            state["trust"][event["request"]["id"]] = shadow.on_time[event["request"]["dealerId"]]

                with Slot() as slot:
                    fork = parent.fork()
                    slot.hold(fork.id)
                    fork._last_seq = parent._last_seq  # the copy's log starts with the parent's: read only what is new
                    try:
                        answers = stride(fork, quote, DAY + FIRST, DAY + LAST, watch)
                    finally:
                        try:
                            fork.delete()
                        except SpreadError:
                            pass
                for rid, bought in answers.items():
                    if rid in asked:
                        b = state["brackets"][rid]
                        b["tries"] += 1
                        if bought:
                            b["lo"] = max(asked[rid], b.get("lo", asked[rid]))
                        else:
                            b["hi"] = min(asked[rid], b.get("hi", asked[rid]))
        finally:
            try:
                parent.delete()
            except SpreadError:
                pass
    with open(path, "w") as file:
        json.dump(state, file)
    known = sum(1 for b in state["brackets"].values() if "lo" in b and "hi" in b and b["hi"] - b["lo"] < 0.02)
    return f"{seed} {kind}: {len(state['requests'])} Tuesday requests, {known} thresholds within 2%"


if __name__ == "__main__":
    seeds, passes = sys.argv[1].split(","), int(sys.argv[2]) if len(sys.argv) > 2 else 8
    jobs = [(seed, kind) for seed in seeds for kind in ("desk", "none")]
    with ThreadPoolExecutor(max_workers=1) as pool:
        def patient(job):
            for attempt in range(4):
                try:
                    return tuesday(job[0], job[1], passes)
                except Exception as error:  # the server was slow or away: the world is gone, start the job again
                    print(f"{job}: {type(error).__name__}: {error}", flush=True)
            return f"{job}: gave up"
        for line in pool.map(patient, jobs):
            print(line, flush=True)
