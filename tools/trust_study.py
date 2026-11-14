"""Dealers' trust through a saved week: how fast the dealers that send most requests reach the 25 orders on time that the rules count,
and what a request is worth to us by the trust its dealer has when it arrives.

    python -m tools.trust_study final-fresh simple-T-s14
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict

from tools.study import runs

DAY, CAP = 1440, 25


def week(run: dict, ranks: dict, bands: dict) -> None:
    """Adds one week: the trust of its three largest dealers at the end of each day, and requests, orders and prices by the dealer's trust."""
    requests, trust, refunded = {}, defaultdict(int), set()
    won = {e["order"]["id"]: e["order"] for e in run["events"] if e["kind"] == "order_won"}
    sizes = Counter(e["request"]["dealerId"] for e in run["events"] if e["kind"] == "price_request")
    largest = [dealer for dealer, _ in sizes.most_common(3)]
    day = 0
    for e in sorted(run["events"], key=lambda e: e["seq"]):
        while e["at"] >= (day + 1) * DAY and day < 5:
            for rank, dealer in enumerate(largest):
                ranks[(rank, day)].append(trust[dealer])
            day += 1
        if e["kind"] == "price_request":
            request = requests[e["request"]["id"]] = e["request"]
            band = bands[min(trust[request["dealerId"]], CAP) // 5 * 5]
            band["requests"] += 1
            if request["id"] in won:
                order = won[request["id"]]
                band["orders"] += 1
                band["price"] += order["priceCents"] / next(o["listPriceCents"] for o in request["options"] if o["kind"] == order["option"])
        elif e["kind"] == "ledger" and e["line"].get("orderId") in requests:  # the count as dispatch/books.py keeps it
            line, dealer = e["line"], requests[e["line"]["orderId"]]["dealerId"]
            if line["kind"] in ("late_refund", "undelivered_penalty") and line["orderId"] not in refunded:
                refunded.add(line["orderId"])
                trust[dealer] = (trust[dealer] - 1) // 2 if line["kind"] == "late_refund" else trust[dealer] // 2
            elif line["kind"] == "revenue":
                trust[dealer] = min(CAP, trust[dealer] + 1)


def main() -> None:
    for tag in sys.argv[1:]:
        ranks, bands = defaultdict(list), defaultdict(lambda: defaultdict(float))
        saved = runs(tag)
        for run in saved:
            week(run, ranks, bands)
        mean = lambda xs: sum(xs) / max(1, len(xs))
        print(f"{tag}: {len(saved)} weeks")
        for rank in range(3):
            print(f"  dealer no. {rank + 1} by requests: trust at the end of Mon..Fri " + "  ".join(f"{mean(ranks[(rank, day)]):4.1f}" for day in range(5))
                  + f"   at 25 by Tuesday night in {mean([t >= CAP for t in ranks[(rank, 1)]]):.0%} of weeks, by Wednesday night {mean([t >= CAP for t in ranks[(rank, 2)]]):.0%}")
        total = sum(band["requests"] for band in bands.values())
        for low in sorted(bands):
            band = bands[low]
            print(f"  trust {low:>2}{'+' if low < CAP else ' '}: {band['requests'] / total:5.1%} of requests, won {band['orders'] / band['requests']:5.1%} at {band['price'] / max(1, band['orders']):.2f} x list")


if __name__ == "__main__":
    main()
