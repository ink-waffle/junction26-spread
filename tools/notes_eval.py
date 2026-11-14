"""Scores the note reader against the reveal's truth of every won car in saved runs.

    python -m tools.notes_eval                              # the labelled worlds outside hold (runs/notes-label)
    python -m tools.notes_eval --tag notes-label-hold       # the hold worlds: only to confirm a finished reader
    python -m tools.notes_eval --misread 30 --fact ready    # list misread notes

A fact is claimed when the reader changes what the request states, and true when the world did. Precision = right claims / claims,
recall = right claims / true changes. A car is right when all eight facts are."""
from __future__ import annotations

import argparse
import glob
import gzip
import json
import os
from collections import Counter

from dispatch import notes
from dispatch.atlas import clock

ROOT = os.environ.get("SPREAD_SHARED") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACTS = ["ready", "released", "pickupHours", "deliveryHours", "manual", "plates", "tyres", "deadline"]


def cars(tags: list[str]) -> list[dict]:
    """One row per won car: the request, the leg, and the reveal's truth. A request seen in several runs of a seed counts once."""
    rows, seen = [], set()
    for tag in tags:
        for path in sorted(glob.glob(os.path.join(ROOT, "runs", tag, "*.json.gz"))):
            if not os.path.getsize(path):
                continue
            with gzip.open(path, "rt") as file:
                run = json.load(file)
            truth = {order["orderId"]: order["legs"] for order in run["reveal"]["orders"]}
            for item in run["reveal"]["requests"]:
                request = item["request"]
                if request["id"] in truth and (run["seed"], request["id"]) not in seen:
                    seen.add((run["seed"], request["id"]))
                    rows += [{"seed": run["seed"], "request": request, "leg": i, "truth": leg} for i, leg in enumerate(truth[request["id"]])]
    return rows


def hours(site_hours) -> tuple:
    return (site_hours["opens"], site_hours["closes"]) if site_hours else None


def stated(request: dict, leg: int) -> dict:
    pickup, delivery = request["legs"][leg]["pickup"], request["legs"][leg]["delivery"]
    return {"ready": pickup["window"]["from"], "released": None, "pickupHours": hours(pickup["hours"]), "deliveryHours": hours(delivery["hours"]),
            "manual": False, "plates": False, "tyres": False, "deadline": None}


def revealed(truth: dict) -> dict:
    return {"ready": truth["readyAt"], "released": truth["releasedAt"], "pickupHours": hours(truth["pickupHours"]), "deliveryHours": hours(truth["deliveryHours"]),
            "manual": truth["manualGearbox"], "plates": truth["needsPlates"], "tyres": truth["summerTyres"], "deadline": truth["noteDeadline"]}


def claimed(request: dict, leg: int) -> dict:
    """What the reader says the world will act on for this car. A note speaks of the first car only."""
    out = stated(request, leg)
    if leg:
        return out
    facts = notes.read(request["note"], request["arrivedAt"])
    out["ready"] = max(out["ready"], facts.ready_at or 0)
    out["released"] = facts.released_at
    for key, opens, closes in (("pickupHours", facts.pickup_opens, facts.pickup_closes), ("deliveryHours", facts.delivery_opens, facts.delivery_closes)):
        if out[key]:
            out[key] = (out[key][0] if opens is None else opens, out[key][1] if closes is None else closes)
    out["manual"], out["plates"], out["tyres"] = facts.manual, facts.plates, facts.summer_tyres
    if facts.deadline is not None and facts.deadline < max(option["deadline"] for option in request["options"]):
        out["deadline"] = facts.deadline  # a deadline no tighter than the request's is no fact
    return out


def show(key: str, value) -> str:
    if value is None or isinstance(value, bool):
        return str(value)
    return clock(value) if isinstance(value, int) else f"{value[0] / 60:g}-{value[1] / 60:g}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--tag", default="notes-label", help="runs to score, separated by commas")
    parser.add_argument("--misread", type=int, default=0, help="list this many misread notes")
    parser.add_argument("--fact", help="list only misreads of this fact")
    args = parser.parse_args()
    rows = cars(args.tag.split(","))
    true, claims, right, wrong = Counter(), Counter(), Counter(), []
    cars_right = notes_right = with_note = 0
    for row in rows:
        request, leg = row["request"], row["leg"]
        base, truth, mine = stated(request, leg), revealed(row["truth"]), claimed(request, leg)
        bad = [key for key in FACTS if mine[key] != truth[key]]
        for key in FACTS:
            true[key] += truth[key] != base[key]
            claims[key] += mine[key] != base[key]
            right[key] += mine[key] != base[key] and mine[key] == truth[key]
        cars_right += not bad
        if request["note"] and not leg:
            with_note += 1
            notes_right += not bad
            if bad:
                wrong.append((bad, row, base, truth, mine))
    print(f"{args.tag}: {len(rows)} cars in {len({row['seed'] for row in rows})} worlds, {with_note} with a note")
    print(f"{'fact':<14}{'true':>6}{'claimed':>9}{'right':>7}{'precision':>11}{'recall':>8}")
    for key in FACTS:
        print(f"{key:<14}{true[key]:>6}{claims[key]:>9}{right[key]:>7}{right[key] / max(1, claims[key]):>11.1%}{right[key] / max(1, true[key]):>8.1%}")
    total = lambda counter: sum(counter.values())
    print(f"{'all':<14}{total(true):>6}{total(claims):>9}{total(right):>7}{total(right) / max(1, total(claims)):>11.1%}{total(right) / max(1, total(true)):>8.1%}")
    print(f"cars right {cars_right / max(1, len(rows)):.2%}   notes right {notes_right}/{with_note} = {notes_right / max(1, with_note):.2%}   misread {len(wrong)}")
    listed = [w for w in wrong if not args.fact or args.fact in w[0]][:args.misread]
    for bad, row, base, truth, mine in listed:
        request = row["request"]
        print(f"\n[{row['seed']} {request['id']} {request['note']['language']}] arrived {clock(request['arrivedAt'])}: {request['note']['text']}")
        for key in bad:
            print(f"    {key}: stated {show(key, base[key])}, true {show(key, truth[key])}, read {show(key, mine[key])}")


if __name__ == "__main__":
    main()
