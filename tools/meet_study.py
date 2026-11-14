"""The randomised test of "meet the drivers on the day": in weeks played with `{"fleet": {"meet": H, "meet_parity": P}}` the one-car orders won the day
before the last day their car can be collected, with H hours of that day from 07:00, stay out of the app until that morning when their number has
parity P; the others are posted when won. Same worlds, same drivers: how the two halves end. The knob lived in commit c5ac391 only: the kept half
ended late 11.1% against 7.0% (30% against 15% in a week's night of the flu), so it is not a policy.

    python -m tools.meet_study fleet3-meet6-par        # the test
    python -m tools.meet_study surprise-weighs --room 6 # the same orders in weeks without it (the two halves must agree)
"""
from __future__ import annotations

import argparse
from collections import defaultdict

import pandas as pd

from dispatch.atlas import DAY, HOUR
from tools.study import runs

MORNING = 7 * HOUR  # no driver reads a notification before it (HANDBOOK.md)

def week(run: dict, room: float, parity: int) -> list[dict]:
    events = run["events"]
    owners = {g["id"]: list(dict.fromkeys(s["orderId"] for s in g["stops"])) for g in run["gigs"]}
    cars = {g["id"]: sum(1 for s in g["stops"] if s["kind"] == "pickup") for g in run["gigs"]}
    posted: dict[str, int] = {}
    for g in run["gigs"]:
        for order in owners[g["id"]]:
            posted[order] = min(posted.get(order, 10 ** 9), g["postedAt"])
    refunded = {e["line"]["orderId"] for e in events if e["kind"] == "ledger" and e["line"]["kind"] in ("late_refund", "undelivered_penalty")}
    paid = {e["line"]["orderId"] for e in events if e["kind"] == "ledger" and e["line"]["kind"] == "revenue"}
    typical = {r["request"]["id"]: r["request"]["referenceFeeCents"] for r in run["reveal"]["requests"]}
    log: dict[str, list[dict]] = defaultdict(list)
    night: dict[int, int] = defaultdict(int)
    for e in events:
        if e["kind"] in ("gig_booked", "gig_dropped", "no_show"):
            for order in owners.get(e["gigId"], []):
                log[order].append(e)
        if e["kind"] == "gig_dropped" and e["at"] % DAY < HOUR:
            night[e["at"] // DAY] += 1
    out = []
    for e in events:
        if e["kind"] != "order_won" or len(e["order"]["legs"]) != 1:
            continue
        order, last = e["order"]["id"], e["order"]["lastPickupAt"]
        morning = last // DAY * DAY + MORNING
        if not morning - DAY <= e["at"] < morning <= last - room * HOUR:
            continue
        booked = [x for x in log[order] if x["kind"] == "gig_booked"]
        drops = [x for x in log[order] if x["kind"] != "gig_booked"]
        fee = booked[-1]["feeCents"] / cars[booked[-1]["gigId"]] / typical[order] if booked else None
        out.append({"seed": run["seed"], "half": "kept for the morning" if int(order[1:]) % 2 == parity else "posted when won", "flu night": night[last // DAY] >= 10,
                    "late": order in refunded or order not in paid, "fee": fee, "gave back": bool(drops), "that night": any(x["at"] // DAY == last // DAY and x["at"] % DAY < HOUR for x in drops),
                    "in the app before the morning": posted.get(order, 10 ** 9) < morning, "with a driver at 09:00": any(x["at"] < morning + 2 * HOUR for x in booked) and not any(morning - 7 * HOUR <= x["at"] < morning + 2 * HOUR for x in drops) or
                    (bool(booked) and booked[-1]["at"] < morning + 2 * HOUR), "never booked": not booked})
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tags", nargs="+")
    parser.add_argument("--room", type=float, default=None, help="hours of the last day from 07:00 (default: what the run's policy says)")
    parser.add_argument("--parity", type=int, default=None)
    args = parser.parse_args()
    pd.set_option("display.width", 220)
    weeks = [run for tag in args.tags for run in runs(tag)]
    rows = []
    for run in weeks:
        fleet = (run["policy"] or {}).get("fleet", {}) if isinstance(run["policy"], dict) else {}
        room = args.room if args.room is not None else fleet.get("meet", 6)
        parity = args.parity if args.parity is not None else fleet.get("meet_parity", 0) or 0
        rows += week(run, room, parity)
    t, n = pd.DataFrame(rows), len(weeks)
    cols = dict(per_week=("late", lambda s: len(s) / n), late=("late", "mean"), late_per_week=("late", lambda s: s.sum() / n), fee=("fee", "mean"), gave_back=("gave back", "mean"), that_night=("that night", "mean"),
                in_app_before=("in the app before the morning", "mean"), driver_at_9=("with a driver at 09:00", "mean"), never_booked=("never booked", "mean"))
    print(f"{n} weeks; one-car orders won the day before the last day of their car")
    print(t.groupby("half").agg(**cols).round(3).to_string())
    print(t.groupby(["flu night", "half"]).agg(**cols).round(3).to_string())
    flu = t[t["flu night"]]
    if len(flu):
        print("\nthe weeks with such a night: late orders of each half")
        print(flu.groupby(["seed", "half"]).agg(orders=("late", "size"), late=("late", "sum"), gave_back=("gave back", "sum")).unstack().to_string())


if __name__ == "__main__":
    main()
