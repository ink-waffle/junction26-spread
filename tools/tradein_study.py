"""Trade-ins in saved runs (research/tradein): how many requests a week, what they pay, what we quote, and how the ones we won fared.

    python -m tools.tradein_study orch-head-record skeptic-notradein-s14 tradein-w0-s14
"""
from __future__ import annotations

import sys
from collections import Counter

import pandas as pd

from tools.study import runs, table


def won(tag: str) -> pd.DataFrame:
    """One row per trade-in we won: the new car's booked hour against its delivery, the first fee, and why it ended late."""
    out = []
    for run in runs(tag):
        requests = {item["request"]["id"]: item["request"] for item in run["reveal"]["requests"]}
        gig_order = {gig["id"]: stop["orderId"] for gig in run.get("gigs", []) for stop in gig["stops"]}
        first = {}
        for gig in sorted(run.get("gigs", []), key=lambda g: g["postedAt"]):
            legs = {stop["leg"] for stop in gig["stops"]}
            first.setdefault(gig["stops"][0]["orderId"], (gig["schedule"][0]["feeCents"] * 2 / len(legs), len(legs)))
        events: dict[str, list[dict]] = {}
        for e in run["events"]:
            order_id = e.get("orderId") or e.get("line", {}).get("orderId") or gig_order.get(e.get("gigId"))
            events.setdefault(order_id, []).append(e)
        for e in run["events"]:
            if e["kind"] != "order_won" or len(e["order"]["legs"]) != 2:
                continue
            order, mine = e["order"], events.get(e["order"]["id"], [])
            at = lambda kind, leg=None: next((x["at"] for x in mine if x["kind"] == kind and (leg is None or x.get("leg") == leg)), None)
            new_car = order["legs"][0]["delivery"]
            due = new_car["window"]["to"] + 30 if new_car["privateAddress"] else order["deadline"]  # RULES.md rule 5: the booked hour + 30 minutes
            delivered, warned, booked, collected = at("delivered", 0), at("deadline_close"), at("gig_booked"), at("picked_up", 0)
            refund = -sum(x["line"]["cents"] for x in mine if x["kind"] == "ledger" and x["line"]["kind"] in ("late_refund", "undelivered_penalty"))
            money = sum(x["line"]["cents"] for x in mine if x["kind"] == "ledger")
            kinds = {x["kind"] for x in mine}
            fee, legs = first.get(order["id"], (0, 0))
            on_time = delivered is not None and delivered <= due and not refund
            why = ("on time" if on_time else "never delivered" if delivered is None else
                   "warning before a driver" if warned is not None and (booked is None or warned < booked) else
                   "driver lost (drop, no-show)" if kinds & {"gig_dropped", "no_show"} else
                   "booked driver collected after lastPickupAt" if collected and collected > order["lastPickupAt"] else "other")
            request = requests[order["id"]]
            out.append({"seed": run["seed"], "order": order["id"], "option": order["option"], "won_day": e["at"] // 1440,
                        "price_x_list": order["priceCents"] / request["options"][0]["listPriceCents"],
                        "first_fee_x_typical": round(fee / request["referenceFeeCents"], 2), "one_gig": legs == 2,
                        "hour_before_deadline_h": (order["deadline"] - new_car["window"]["to"]) / 60,
                        "on_time": on_time, "why": why, "margin": money / 100})
    return pd.DataFrame(out)


def main() -> None:
    for tag in sys.argv[1:]:
        t = table(tag)
        weeks, trade = t.seed.nunique(), t[t.legs == 2]
        quote = trade[[c for c in trade.columns if c.startswith("m_")]].min(axis=1)
        w = won(tag)
        print(f"== {tag}: {weeks} weeks; {len(trade) / weeks:.1f} trade-in requests a week, typical fee {(trade.typical / trade.list).median():.2f} x list "
              f"(one car {(t[t.legs == 1].typical / t[t.legs == 1].list).median():.2f} x), list EUR {trade.list.median() / 100:.0f}, private delivery {trade.private_de.mean():.0%}; "
              f"our quote a median {quote.median():.2f} x list (quartile {quote.quantile(0.25):.2f} x)")
        if w.empty:
            continue
        print(f"   won {len(w)} ({len(w) / weeks:.2f} a week) at {w.price_x_list.median():.2f} x list: {w.on_time.sum()} on time, margin EUR {w.margin.mean():.1f} an order "
              f"(EUR {w.margin.sum() / weeks:+.0f} a week); one gig from the first posting {w.one_gig.mean():.0%}; booked hour ends a median "
              f"{w.hour_before_deadline_h.median():.0f} h before the order's deadline")
        print("   on time by first fee x typical:", {fee: f"{g.on_time.sum()}/{len(g)}" for fee, g in w.groupby("first_fee_x_typical")})
        print("   by outcome:", dict(Counter(w.why)))


if __name__ == "__main__":
    main()
