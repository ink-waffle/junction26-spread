"""Do drivers learn to wait for our raises? How fast a new gig of one car is booked at its opening fee, by the weekday it was posted, for each version;
and how many gigs were raised before a driver took them.

    python -m tools.waiting_study main-m10 fleet2-base-look6 fleet2-k3-daily
"""
from __future__ import annotations

import sys

import pandas as pd

from dispatch.atlas import DAY, HOUR
from tools.study import runs


def gigs(tag: str) -> pd.DataFrame:
    """One row per order whose first gig carried it alone and was posted in working hours: when it was booked, and at what fee against the first fee a driver saw."""
    rows = []
    for run in runs(tag):
        first, alone = {}, {}
        for gig in sorted(run["gigs"], key=lambda g: g["postedAt"]):
            order_id = gig["stops"][0]["orderId"]
            if order_id not in first:
                first[order_id], alone[order_id] = gig, len({stop["orderId"] for stop in gig["stops"]}) == 1
        owner = {gig["id"]: gig["stops"][0]["orderId"] for gig in run["gigs"]}
        seen, booked = {}, {}
        for view in sorted(run["reveal"]["views"], key=lambda v: v["at"]):
            seen.setdefault(owner.get(view["gigId"]), view["feeCents"])
        for event in run["events"]:
            if event["kind"] == "gig_booked":
                booked.setdefault(owner.get(event["gigId"]), event)
        for order_id, gig in first.items():
            at = gig["postedAt"]
            if alone[order_id] and at < 5 * DAY and 8 * HOUR <= at % DAY < 18 * HOUR and order_id in seen:
                booking = booked.get(order_id)
                rows.append({"seed": run["seed"], "day": at // DAY, "wait": (booking["at"] - at) / 60 if booking else 1e9,
                             "raised": bool(booking) and booking["feeCents"] > seen[order_id] * 1.01, "at_first_fee": bool(booking) and booking["feeCents"] <= seen[order_id] * 1.01})
    return pd.DataFrame(rows)


def main() -> None:
    pd.set_option("display.width", 200)
    for tag in sys.argv[1:]:
        t = gigs(tag)
        t["in15"], t["in60"], t["in360"] = (t.wait <= 15) & t.at_first_fee, (t.wait <= 60) & t.at_first_fee, (t.wait <= 360) & t.at_first_fee
        by = t.groupby("day").agg(gigs=("wait", "size"), in15=("in15", "mean"), in60=("in60", "mean"), in360=("in360", "mean"), raised=("raised", "mean"))
        by["gigs"] /= t.seed.nunique()
        print(f"{tag}: new one-car gigs posted 08-18, by weekday: a week's gigs, share booked at the first fee within 15 min / 1 h / 6 h, share booked only after a raise")
        print(by.round(3).to_string())


if __name__ == "__main__":
    main()
