"""What we pay drivers, by the moment of the fleet's rule that chose the fee (research/gap): every done gig of saved weeks,
its multiple of the typical fee and when that fee was last chosen. The table of GAP.md, section 2.

    python -m tools.fee_moments orch-head-record        # a tag of saved runs
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys

import pandas as pd

from dispatch.atlas import DAY
from tools.study import ROOT

STEPS = [0.7, 0.85, 1.0, 1.15, 1.3, 1.5, 1.6, 2.0]  # the fees the policy can name, to bin a paid multiple


def rows(run: dict) -> list[dict]:
    """One row per order of a done gig: the moment its fee was chosen, the multiple, the fee, the refund."""
    orders = {e["order"]["id"]: e["order"] for e in run["events"] if e["kind"] == "order_won"}
    won_at = {e["order"]["id"]: e["at"] for e in run["events"] if e["kind"] == "order_won"}
    typical = {i["request"]["id"]: i["request"]["referenceFeeCents"] / len(i["request"]["legs"]) for i in run["reveal"]["requests"]}
    cars = {g["id"]: list(dict.fromkeys(s["orderId"] for s in g["stops"])) for g in run["gigs"]}
    warned, lost, last, refund, first_post = {}, {}, {}, {}, {}
    for e in run["events"]:
        kind = e["kind"]
        if kind == "deadline_close":
            warned.setdefault(e["orderId"], e["at"])
        elif kind in ("gig_dropped", "no_show"):
            for order_id in cars.get(e["gigId"], []):
                lost.setdefault(order_id, []).append(e["at"])
        elif kind == "ledger" and e["line"]["kind"] in ("late_refund", "undelivered_penalty"):
            refund[e["line"]["orderId"]] = refund.get(e["line"]["orderId"], 0) - e["line"]["cents"]
        if kind in ("order_won", "order_changed") and "order" in e:
            last[e["order"]["id"]] = e["order"]["lastPickupAt"]
    for gig in sorted(run["gigs"], key=lambda g: g["postedAt"]):
        for order_id in cars[gig["id"]]:
            first_post.setdefault(order_id, gig["postedAt"])
    out = []
    for gig in run["gigs"]:
        ids = cars[gig["id"]]
        if gig["status"] != "done" or any(i not in orders for i in ids):
            continue
        multiple = gig["schedule"][-1]["feeCents"] / sum(typical[s["orderId"]] for s in gig["stops"] if s["kind"] == "pickup")
        at, first = gig["schedule"][-1]["at"], ids[0]
        if len(ids) == 2:
            moment = "two-car gig"
        elif len(gig["stops"]) == 4:
            moment = "trade-in"
        elif first in warned and at >= warned[first] - 15:
            moment = "after the deadline warning"
        elif any(0 <= at - x <= 15 for x in lost.get(first, [])):
            moment = "after it lost its driver"
        elif at >= last.get(first, 10 ** 9) - DAY - 15 and at > first_post[first] + 15:
            moment = "last-day look"
        elif at >= first_post[first] + 345:
            moment = "six-hour look"
        else:
            moment = "at the win" if at <= won_at[first] + 60 else "other"
        out += [{"moment": moment, "step": min(STEPS, key=lambda step: abs(step - multiple)), "typical": typical[i], "fee": multiple * typical[i], "refund": refund.get(i, 0)} for i in ids]
    return out


def main() -> None:
    paths = sorted(glob.glob(os.path.join(ROOT, "runs", sys.argv[1], "*.json.gz")))
    table = pd.DataFrame([row for path in paths for row in rows(json.load(gzip.open(path, "rt")))])
    weeks, orders = len(paths), len(table)
    print(f"{sys.argv[1]}: {weeks} weeks, {orders / weeks:.0f} orders a week in done gigs, fees {table.fee.sum() / table.typical.sum():.3f} x typical")
    by = table.groupby("moment").agg(orders=("fee", "size"), typical=("typical", "sum"), fee=("fee", "sum"), refund=("refund", "sum"), late=("refund", lambda s: (s > 0).mean()))
    by["x typical"] = by.fee / by.typical
    by["over 0.85 x, EUR a week"] = (by.fee - 0.85 * by.typical) / weeks / 100
    by["refunds, EUR a week"] = by.refund / weeks / 100
    by["orders a week"] = by.orders / weeks
    print(by[["orders a week", "x typical", "over 0.85 x, EUR a week", "refunds, EUR a week", "late"]].round(3).to_string())
    print("\norders a week by moment and fee step")
    print((table.pivot_table(index="moment", columns="step", values="fee", aggfunc="size", fill_value=0) / weeks).round(1).to_string())


if __name__ == "__main__":
    main()
