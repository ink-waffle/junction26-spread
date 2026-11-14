"""Orders won by weekday, for saved runs: does a week start as fast as it ends?

    python -m tools.weekdays final-fresh skeptic-base-s14

Per tag and weekday, as a mean over the tag's weeks: requests, requests we priced to win (not declined), orders won, the share won,
the price we asked and the price we won at (multiples of the list price, cheapest option), the fee the won orders' first gigs opened at
(a multiple of the typical fee) and the share of the day's orders that arrived late.
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys
from collections import defaultdict

from tools.study import ROOT

DAY, NAMES = 1440, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def week(run: dict) -> dict[int, dict[str, float]]:
    """day -> the sums of one saved week."""
    days: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    requests = {e["request"]["id"]: e["request"] for e in run["events"] if e["kind"] == "price_request"}
    won = {e["order"]["id"]: e["order"] for e in run["events"] if e["kind"] == "order_won"}
    late = {e["line"].get("orderId") for e in run["events"] if e["kind"] == "ledger" and e["line"]["kind"] in ("late_refund", "undelivered_penalty")}
    first_fee: dict[str, float] = {}
    for gig in sorted(run["gigs"], key=lambda g: g["postedAt"]):
        owners = {stop["orderId"] for stop in gig["stops"]}
        order = min(owners)
        if len(owners) == 1 and order not in first_fee and order in requests:
            cars = sum(stop["kind"] == "pickup" for stop in gig["stops"])
            first_fee[order] = gig["schedule"][0]["feeCents"] / (requests[order]["referenceFeeCents"] * cars / len(requests[order]["legs"]))
    for rid, request in requests.items():
        day, lists = days[request["arrivedAt"] // DAY % 7], {o["kind"]: o["listPriceCents"] for o in request["options"]}
        asked = min((price / lists[kind] for kind, price in run["quotes"].get(rid, {}).items()), default=99.0)
        day["requests"] += 1
        if asked < 5:
            day["priced"] += 1
            day["asked"] += asked
        if rid in won:
            day["won"] += 1
            day["price"] += won[rid]["priceCents"] / lists[won[rid]["option"]]
            day["late"] += rid in late
            if rid in first_fee:
                day["fee"] += first_fee[rid]
                day["fees"] += 1
    return days


def table(tag: str) -> None:
    weeks = []
    for path in sorted(glob.glob(os.path.join(ROOT, "runs", tag, "*.json.gz"))):
        with gzip.open(path, "rt") as file:
            weeks.append(week(json.load(file)))
    if not weeks:
        return print(f"{tag}: no saved weeks")
    print(f"{tag}: {len(weeks)} weeks, a mean week")
    print(f"  {'day':<4} {'requests':>8} {'priced':>7} {'won':>6} {'won/req':>8} {'asked':>6} {'won at':>7} {'fee':>5} {'late':>6}")
    total = lambda key, day: sum(w[day][key] for w in weeks if day in w)
    for day in range(7):
        n, won, priced = total("requests", day), total("won", day), total("priced", day)
        if n:
            print(f"  {NAMES[day]:<4} {n / len(weeks):>8.1f} {priced / len(weeks):>7.1f} {won / len(weeks):>6.1f} {won / n:>8.1%} {total('asked', day) / max(1, priced):>6.2f} "
                  f"{total('price', day) / max(1, won):>7.2f} {total('fee', day) / max(1, total('fees', day)):>5.2f} {total('late', day) / max(1, won):>6.1%}")
    mon, wed = total("won", 0), total("won", 2)
    print(f"  Monday / Wednesday orders: {mon / max(1, wed):.2f}")


if __name__ == "__main__":
    for tag in sys.argv[1:]:
        table(tag)
