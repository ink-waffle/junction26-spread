"""Writes an ended practice world and its reveal to CSV files, one for each table. See HANDBOOK.md, Research.
    spread-reveal-csv <world id>                    a practice world that has ended, for example one your system played
    spread-reveal-csv [--seed <text>] [--level 1-8]   a new practice world, run to its end with no actions: its requests only
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys

from spread.client import Client, SpreadError


def flat(value: dict, prefix: str = "", row: dict | None = None) -> dict:
    """One row: a nested object gives columns with dotted names, and a list gives one column of JSON."""
    row = {} if row is None else row
    for key, item in value.items():
        if isinstance(item, dict):
            flat(item, f"{prefix}{key}.", row)
        else:
            row[prefix + key] = json.dumps(item, separators=(",", ":"), ensure_ascii=False) if isinstance(item, (list, bool)) else item
    return row


def write(folder: str, name: str, rows: list[dict]) -> None:
    names = list(dict.fromkeys(key for row in rows for key in row))
    # A null object, such as no change of plan, leaves its dotted columns empty and needs no column of its own.
    columns = [column for column in names if not any(other.startswith(f"{column}.") for other in names)]
    with open(os.path.join(folder, f"{name}.csv"), "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{file.name}: {len(rows)} rows")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("world", nargs="?", help="a practice world that has ended; without it, a new one, run to its end with no actions")
    parser.add_argument("--seed", help="the seed of the new world")
    parser.add_argument("--level", type=int, choices=range(1, 9), default=8, help="the level of the new world (default 8)")
    parser.add_argument("--out", help="the folder for the files (default reveal-<world id>)")
    args = parser.parse_args()
    try:
        client = Client()
        world = client.world(args.world) if args.world else client.create(level=args.level, seed=args.seed)
        if not args.world:
            world.advance(to=world.snapshot()["endsAt"])
            print(f"Practice world {world.id}, level {args.level}, ran to its end with no actions.")
        reveal, events, gigs, roster, places = world.reveal(), world.events(), world.snapshot()["gigs"], world.roster(), client.map()
    except SpreadError as error:
        sys.exit(f"spread: {error}")
    folder = args.out or f"reveal-{world.id}"
    os.makedirs(folder, exist_ok=True)
    truth = {(order["orderId"], i): leg for order in reveal["orders"] for i, leg in enumerate(order["legs"])}
    requests = []
    for revealed in reveal["requests"]:
        request, quote = dict(revealed["request"]), revealed["quote"] or {}
        legs, options, note = request.pop("legs"), request.pop("options"), request.pop("note")
        row = {**request, "outcome": revealed["outcome"], "option": revealed["option"], "legs": len(legs), "note": note and note["text"], "language": note and note["language"]}
        for option in options:
            row.update({f"{option['kind']}.{key}": value for key, value in option.items() if key != "kind"}, **{f"{option['kind']}.quoteCents": quote.get(option["kind"])})
        requests.append(row)
    write(folder, "requests", requests)
    write(folder, "legs", [{"requestId": r["request"]["id"], "leg": i, **flat(leg), **flat(truth.get((r["request"]["id"], i), {}), "truth.")} for r in reveal["requests"] for i, leg in enumerate(r["request"]["legs"])])
    write(folder, "drivers", [flat(driver) for driver in roster])
    write(folder, "views", [flat(view) for view in reveal["views"]])
    write(folder, "gigs", [{**flat(gig), "orders": " ".join(dict.fromkeys(stop["orderId"] for stop in gig["stops"]))} for gig in gigs])
    write(folder, "events", [flat(event) for event in events if event["kind"] != "price_request"])
    write(folder, "places", [flat(place) for place in places["places"]])
    write(folder, "roads", places["roads"])


if __name__ == "__main__":
    main()
