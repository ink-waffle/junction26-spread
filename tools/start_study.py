"""The price of a late order through the week, hour by hour, in saved weeks: is the week's start priced as its middle is?
Each week is replayed through the books and the fleet (tools.control_study); per weekday, and per hour of Monday, it prints the orders so far, the cars without a driver,
the late orders the books expect, the week's learned intercept, and the price of a late order: its mean, and the share of working hours at EUR 1,500 or more
(there a car with one chance in ten of arriving late is quoted EUR 150 dearer: mostly a refusal). The last columns give the same price had the
barrier's count of orders started at another number of orders (`CALM`), on the same history.

    python -m tools.start_study final-fresh [weeks]
"""
from __future__ import annotations

import sys
from collections import defaultdict

from dispatch.atlas import DAY, HOUR
from dispatch.fleet import CALM, GRIP, FleetPolicy
from tools.control_study import trace
from tools.study import runs

NAMES, OTHERS = ["Mon", "Tue", "Wed", "Thu", "Fri"], (60, 100)


def main() -> None:
    tag, weeks = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 99
    policy = FleetPolicy()
    price = lambda row, calm: policy.late_price * min(2.0, row["expected"] / (calm + row["orders"]) / (1 - policy.on_time)) ** GRIP
    days: dict[int, list[dict]] = defaultdict(list)
    for run in runs(tag)[:weeks]:
        for row in trace(run, policy, every=HOUR):
            if 9 * HOUR <= row["minute"] % DAY < 18 * HOUR and row["minute"] // DAY < 5:
                days[row["minute"] // DAY].append(row)
                if row["minute"] // DAY == 0:
                    days[100 + row["minute"] % DAY // HOUR].append(row)
    name = lambda day: NAMES[day] if day < 5 else f"{day - 100}h"
    mean = lambda rows, f: sum(f(row) for row in rows) / len(rows)
    print(f"{tag}: working hours 09-18 of {weeks if weeks < 99 else 'all'} weeks")
    print(f"  {'day':<4} {'orders':>7} {'no driver':>9} {'expected late':>13} {'learned':>8} {'late price':>10} {'>= 1,500':>9}" + "".join(f" {'CALM ' + str(c):>10} {'>= 1,500':>9}" for c in OTHERS))
    for day, rows in sorted(days.items()):
        print(f"  {name(day):<4} {mean(rows, lambda r: r['orders']):>7.0f} {mean(rows, lambda r: r['backlog']):>9.1f} {mean(rows, lambda r: r['expected']):>13.1f} {mean(rows, lambda r: r['world']):>8.2f} "
              f"{mean(rows, lambda r: price(r, CALM)):>10,.0f} {mean(rows, lambda r: price(r, CALM) >= 1500):>9.0%}"
              + "".join(f" {mean(rows, lambda r: price(r, c)):>10,.0f} {mean(rows, lambda r: price(r, c) >= 1500):>9.0%}" for c in OTHERS))


if __name__ == "__main__":
    main()
