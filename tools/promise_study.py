"""How good is a booking as a promise? Bookings of one-car gigs by when they were made against the day the car had to be collected at the latest:
how many are given back, when, and how the order ends. The midnight drop is a booking made a day or more ahead that its driver gives back when the day comes.

    python -m tools.promise_study fleet2-s-v2b fleet2-s-v2b-wide
"""
from __future__ import annotations

import sys

import pandas as pd

from dispatch.atlas import DAY, HOUR
from tools.study import runs


def bookings(run: dict) -> list[dict]:
    events = run["events"]
    owners = {g["id"]: list(dict.fromkeys(s["orderId"] for s in g["stops"])) for g in run["gigs"]}
    last = {e["order"]["id"]: e["order"]["lastPickupAt"] for e in events if e["kind"] in ("order_won", "order_changed")}
    ready = {e["order"]["id"]: e["order"]["legs"][0]["pickup"]["window"]["from"] for e in events if e["kind"] == "order_won"}
    refunded = {e["line"]["orderId"] for e in events if e["kind"] == "ledger" and e["line"]["kind"] in ("late_refund", "undelivered_penalty")}
    picked = {e["gigId"]: e["at"] for e in events if e["kind"] == "picked_up"}
    out, open_booking = [], {}
    for e in events:
        if e["kind"] == "gig_booked" and len(owners.get(e["gigId"], [])) == 1:
            order = owners[e["gigId"]][0]
            if order in last:
                open_booking[e["gigId"]] = row = {"seed": run["seed"], "order": order, "booked": e["at"], "last": last[order], "ready": ready.get(order, 0), "dropped": None, "late": order in refunded}
                out.append(row)
        elif e["kind"] in ("gig_dropped", "no_show") and e["gigId"] in open_booking:
            open_booking.pop(e["gigId"])["dropped"] = e["at"]
    for row in out:
        day = row["last"] // DAY  # the last day on which the car can be collected in time
        ahead = day - row["booked"] // DAY
        row["when"] = ("two days ahead or more" if ahead >= 2 else "the day before" if ahead == 1 else "that day before 09:00" if row["booked"] % DAY < 9 * HOUR else "that day, later") if ahead >= 0 else "after it"
        row["whole day"] = row["ready"] < day * DAY + 9 * HOUR  # the car could be collected from the morning of that day on
        row["gave back"] = row["dropped"] is not None
        row["night drop"] = row["gave back"] and row["dropped"] % DAY < HOUR and row["dropped"] // DAY == day
        row["left"] = (row["last"] - row["dropped"]) / HOUR if row["gave back"] else None
    return out


def main() -> None:
    pd.set_option("display.width", 220)
    weeks = [run for tag in sys.argv[1:] for run in runs(tag)]
    t = pd.DataFrame([row for run in weeks for row in bookings(run)])
    n, order = len(weeks), ["two days ahead or more", "the day before", "that day before 09:00", "that day, later", "after it"]
    print(f"{n} weeks, {len(t) / n:.0f} bookings of one-car gigs a week; by when the booking was made against the car's last day")
    by = t.groupby("when").agg(per_week=("gave back", lambda s: len(s) / n), dropped=("gave back", "mean"), dropped_that_night=("night drop", "mean"), hours_left_at_the_drop=("left", "median"),
                               order_late=("late", "mean"), late_per_week=("late", lambda s: s.sum() / n))
    print(by.reindex([w for w in order if w in by.index]).round(3).to_string())
    d = t[t["gave back"]]
    print("\nthe dropped ones: how their orders end, by when the booking had been made and by the hours then left to the last pickup")
    print(d.groupby(["when", pd.cut(d.left, [-1000, 0, 6, 12, 24, 1000])], observed=True).agg(per_week=("late", lambda s: len(s) / n), order_late=("late", "mean"), late_per_week=("late", lambda s: s.sum() / n)).round(3).to_string())
    full = t[(t.when == "the day before") & t["whole day"]]
    print(f"\nbooked the day before for a car with its whole last day ahead: {len(full) / n:.1f} a week, {full["gave back"].mean():.1%} dropped ({full['night drop'].mean():.1%} in the hour after midnight), {full.late.mean():.1%} of the orders late, {full.late.sum() / n:.1f} a week")
    same = t[t.when.isin(["that day before 09:00", "that day, later"])]
    print(f"booked on the last day itself: {len(same) / n:.1f} a week, {same["gave back"].mean():.1%} dropped, {same.late.mean():.1%} of the orders late")


if __name__ == "__main__":
    main()
