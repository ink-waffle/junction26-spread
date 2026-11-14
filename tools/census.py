"""Who reads a direct offer on each day of a seed's week: an attempt to find the flu day, which a saved week does not show.

    python -m tools.census halal-01,halal-02      # by day: of the drivers who read on every other working day, the share who read nothing; runs/census/<seed>.json

The seed is played without a quote. At a midnight the world is forked, and the copy wins the day's first cars at a low price, posts each at one
cent and, from 11:00, offers every driver one of them at one cent, twice, the same driver at the same minute on every day (a driver asked ten
minutes later than yesterday reads differently). Read means declined; unread means expired. Friday's copy runs on through Saturday, Sunday and
the last Monday. What it found: the drivers who read on every other working day read today too, 97 to 99 in 100, on each of the five days: the
flu, which keeps 30% of the drivers who meant to work at home, leaves no mark on who reads an offer."""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from typing import Optional

from spread.client import Client, SpreadError

from dispatch.atlas import DAY
from tools.harness import RUNS, Slot, create

FOLDER = os.path.join(RUNS, "census")
NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun", "Mon+"]
GIGS, ROUNDS, TURN = 20, 2, 60  # cars to win, offers per driver and day, offers per turn: three open offers per gig
OPENS, ASKS, STRIDE = 8 * 60, 11 * 60, 10  # when requests start, when the offers start; an offer lasts 10 minutes


def census(parent, days: list[int], drivers: list[str]) -> dict:
    """The days on one copy of the world: each driver's answers by day. The cars are won on the first of the days, with a deadline after the last."""
    queue, answers = drivers * ROUNDS, {day: defaultdict(list) for day in days}
    with Slot() as slot:
        fork = parent.fork()
        slot.hold(fork.id)
        fork._last_seq = parent._last_seq  # the copy's log starts with the parent's: read only what is new
        try:
            now, actions, gigs = fork.advance(to=days[0] * DAY + OPENS)["now"], [], []

            def turn(to: Optional[int] = None) -> None:
                nonlocal now, actions, gigs
                step = fork.advance(to=to, actions=actions) if to else fork.advance(by=STRIDE, actions=actions)
                for action, result in zip(actions, step["results"]):
                    if action["type"] == "post" and result["ok"]:
                        gigs.append(result["id"])
                    elif action["type"] == "offer" and not result["ok"]:  # the gig left the app
                        gigs = [gig for gig in gigs if gig != action["gigId"]]
                actions, now = [], step["now"]
                for event in step["events"]:
                    if event["kind"] == "price_request" and now < days[0] * DAY + ASKS:
                        request = event["request"]
                        leg, option = request["legs"][0], request["options"][-1]
                        plain = len(request["legs"]) == 1 and not leg["car"]["premium"] and not leg["pickup"]["privateAddress"] and not leg["delivery"]["privateAddress"]
                        wanted = plain and option["deadline"] > days[-1] * DAY + ASKS  # a plain car whose gig stays in the app until the last offer: at a price that wins
                        actions.append({"type": "quote", "requestId": request["id"], "prices": {option["kind"]: option["listPriceCents"] * (60 if wanted else 1000) // 100}})
                    elif event["kind"] == "order_won" and len(gigs) + sum(a["type"] == "post" for a in actions) < GIGS:
                        stops = [{"orderId": event["order"]["id"], "leg": 0, "kind": kind} for kind in ("pickup", "delivery")]
                        actions.append({"type": "post", "stops": stops, "audience": {"experienced": False, "manualLicence": False}, "schedule": [{"at": now, "feeCents": 1}]})
                    elif event["kind"] == "offer_answered":
                        answers[(event["at"] - STRIDE) // DAY][event["driverId"]].append(event["answer"])

            while now < days[0] * DAY + ASKS:
                turn()
            for day in days:
                if now < day * DAY + ASKS:
                    turn(to=day * DAY + ASKS)
                for start in range(0, len(queue), TURN):  # a turn's drivers keep their minute; with fewer gigs the last of them are not asked
                    asked = queue[start:start + TURN][:3 * len(gigs)]
                    actions += [{"type": "offer", "gigId": gigs[i // 3], "driverId": driver, "feeCents": 1} for i, driver in enumerate(asked)]
                    turn()
                turn()
        finally:
            try:
                fork.delete()
            except SpreadError:
                pass
    return {str(day): {"gigs": len(gigs), "answers": answers[day]} for day in days}


def week(seed: str) -> str:
    path = os.path.join(FOLDER, f"{seed}.json")
    if not os.path.exists(path):
        client, days = Client(), {}
        with Slot() as slot:
            parent = create(client, 8, seed)
            slot.hold(parent.id)
            try:
                drivers = sorted(driver["id"] for driver in parent.roster())
                for day in range(5):
                    parent.advance(to=day * DAY)
                    days.update(census(parent, [day] if day < 4 else [4, 5, 6, 7], drivers))
            finally:
                try:
                    parent.delete()
                except SpreadError:
                    pass
        os.makedirs(FOLDER, exist_ok=True)
        with open(path, "w") as file:
            json.dump({"seed": seed, "drivers": len(drivers), "days": days}, file)
    return f"{seed}: " + reading(seed)


def missing(seed: str) -> Optional[dict]:
    """By day of a counted seed: the readers (drivers who read an offer), and of the drivers who read on every other working day, the share who read none."""
    path = os.path.join(FOLDER, f"{seed}.json")
    if not os.path.exists(path):
        return None
    with open(path) as file:
        saved = json.load(file)
    reads = {int(day): {driver for driver, answers in found["answers"].items() if set(answers) - {"expired"}} for day, found in saved["days"].items()}
    asked = {int(day): set(found["answers"]) for day, found in saved["days"].items()}
    out = {}
    for day in sorted(reads):
        others = [other for other in range(5) if other != day and other in reads]
        regular = set.intersection(*[reads[other] for other in others]) & asked[day]
        out[day] = {"readers": len(reads[day]) / max(1, len(asked[day])), "regular": len(regular), "missing": len(regular - reads[day]) / max(1, len(regular)), "gigs": saved["days"][str(day)]["gigs"]}
    return out


def flu(seed: str) -> tuple[Optional[int], float]:
    """The flu day of a counted seed, and the share of its regular readers who read nothing: the day from Monday to Friday on which most are missing, if 1 in 7 or more."""
    found = missing(seed)
    if not found:
        return None, 0.0
    day = max((d for d in found if d < 5), key=lambda d: found[d]["missing"])
    return (day, found[day]["missing"]) if found[day]["missing"] >= 1 / 7 else (None, found[day]["missing"])


def reading(seed: str) -> str:
    found, (day, share) = missing(seed), flu(seed)
    return (f"regular readers who read nothing, by day {[f'{NAMES[d]} {f['missing']:.0%} of {f['regular']}' for d, f in found.items()]}; drivers who read {[f'{f['readers']:.1%}' for f in found.values()]}; "
            f"gigs {[f['gigs'] for f in found.values()]}; " + (f"flu day {NAMES[day]} ({share:.0%} missing)" if day is not None else "no flu day among the working days"))


if __name__ == "__main__":
    for seed in sys.argv[1].split(","):
        print(week(seed), flush=True)
