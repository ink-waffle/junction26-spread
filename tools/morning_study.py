"""What reaches the drivers at 07:00? One-car orders that begin the last day on which their car can be collected in time without a driver:
those whose driver gave the gig back in the night (a returned gig notifies again), those that sat in the app since the day before, and those
first posted that morning. For each: who looks in the first hour, how soon a driver books, how the order ends. And the bookings of the day before:
when they are made, on which day the car is then collected, how many are given back.

    python -m tools.morning_study surprise-weighs surprise-weighs-wide
"""
from __future__ import annotations

import sys
from collections import defaultdict

import pandas as pd

from dispatch.atlas import DAY, HOUR
from tools.study import runs

MORNING = 7 * HOUR  # no driver reads a notification before it (HANDBOOK.md)


def week(run: dict) -> tuple[list[dict], list[dict]]:
    events = run["events"]
    owners = {g["id"]: list(dict.fromkeys(s["orderId"] for s in g["stops"])) for g in run["gigs"]}
    posted = {g["id"]: g["postedAt"] for g in run["gigs"]}
    won = {e["order"]["id"]: e for e in events if e["kind"] == "order_won"}
    refunded = {e["line"]["orderId"] for e in events if e["kind"] == "ledger" and e["line"]["kind"] in ("late_refund", "undelivered_penalty")}
    paid = {e["line"]["orderId"] for e in events if e["kind"] == "ledger" and e["line"]["kind"] == "revenue"}
    log: dict[str, list[tuple[int, str]]] = defaultdict(list)  # order -> (minute, what happened to its driver)
    for e in events:
        if e["kind"] in ("gig_booked", "gig_dropped", "no_show", "picked_up"):
            for order in owners.get(e["gigId"], []) if e["kind"] != "picked_up" else [e["orderId"]]:
                log[order].append((e["at"], e["kind"]))
    views: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for v in run["reveal"]["views"]:
        for order in owners.get(v["gigId"], []):
            views[order].append((v["at"], v["driverId"]))
    first_post: dict[str, int] = {}
    for gig, orders in owners.items():
        for order in orders:
            first_post[order] = min(first_post.get(order, 10 ** 9), posted[gig])
    night = defaultdict(int)  # day -> drops in its first hour
    for e in events:
        if e["kind"] == "gig_dropped" and e["at"] % DAY < HOUR:
            night[e["at"] // DAY] += 1
    mornings, bookings = [], []
    for order, e in won.items():
        if len(e["order"]["legs"]) != 1:
            continue
        last, late = e["order"]["lastPickupAt"], order in refunded or order not in paid
        day, seven = last // DAY, last // DAY * DAY + MORNING
        happened = sorted(log[order])
        before = [(at, kind) for at, kind in happened if at < seven]
        for at, kind in happened:
            if kind == "gig_booked" and at // DAY == day - 1:
                after = [(a, k) for a, k in happened if a > at]
                gave = bool(after) and after[0][1] in ("gig_dropped", "no_show")
                picked = next((a for a, k in after if k == "picked_up"), None) if not gave else None
                bookings.append({"hour": "before 12" if at % DAY < 12 * HOUR else "12 to 18" if at % DAY < 18 * HOUR else "18 on", "gave back": gave,
                                 "that night": gave and after[0][0] // DAY == day and after[0][0] % DAY < HOUR, "collected the same day": picked is not None and picked // DAY == day - 1,
                                 "collected on the last day": picked is not None and picked // DAY == day, "late": late, "flu night": night[day] >= 10})
        if e["at"] >= seven or last - seven < 4 * HOUR or (before and before[-1][1] in ("gig_booked", "picked_up")):
            continue  # won that day, no morning to speak of, or it has its driver at 07:00
        kind = "returned in the night" if before and before[-1][0] >= seven - 8 * HOUR else "sat since the day before" if first_post.get(order, 10 ** 9) < seven - 8 * HOUR else "first posted in the night"
        booked = next((at for at, k in happened if k == "gig_booked" and at >= seven), None)
        lookers = {driver for at, driver in views[order] if seven <= at < seven + HOUR}
        early = {driver for at, driver in views[order] if seven <= at < seven + 10}
        mornings.append({"kind": kind, "flu night": night[day] >= 10, "viewers 07:00-07:10": len(early), "viewers 07:00-08:00": len(lookers),
                         "booked by 08:00": booked is not None and booked < seven + HOUR, "booked by 10:00": booked is not None and booked < seven + 3 * HOUR,
                         "hours left": (last - seven) / HOUR, "late": late})
    return mornings, bookings


def main() -> None:
    pd.set_option("display.width", 220)
    weeks = [week(run) for tag in sys.argv[1:] for run in runs(tag)]
    n = len(weeks)
    m, b = pd.DataFrame([row for mornings, _ in weeks for row in mornings]), pd.DataFrame([row for _, bookings in weeks for row in bookings])
    print(f"{n} weeks. One-car orders without a driver at 07:00 of the last day their car can be collected in time (at least 4 h of it left):")
    print(m.groupby(["kind", "flu night"]).agg(per_week=("late", lambda s: len(s) / n), viewers_10min=("viewers 07:00-07:10", "mean"), viewers_1h=("viewers 07:00-08:00", "mean"),
                                               booked_by_8=("booked by 08:00", "mean"), booked_by_10=("booked by 10:00", "mean"), hours_left=("hours left", "median"), late=("late", "mean")).round(3).to_string())
    print("\nBookings made the day before that last day, by the hour they were made:")
    print(b.groupby(["flu night", "hour"]).agg(per_week=("late", lambda s: len(s) / n), gave_back=("gave back", "mean"), that_night=("that night", "mean"), collected_same_day=("collected the same day", "mean"),
                                               collected_last_day=("collected on the last day", "mean"), late=("late", "mean")).round(3).to_string())


if __name__ == "__main__":
    main()
