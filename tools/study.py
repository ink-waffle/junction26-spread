"""Turns saved runs (runs/<tag>/<seed>.json.gz) into one table with a row per price request, for research.

    from tools.study import table
    t = table("explore1")       # pandas DataFrame: the request, our quote, the outcome, the gig, the money
"""
from __future__ import annotations

import glob
import gzip
import json
import math
import os

import pandas as pd

from dispatch.atlas import DAY, Atlas

ROOT = os.environ.get("SPREAD_SHARED") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # runs/ and .slots/ are shared by all worktrees
_atlas = None


def atlas() -> Atlas:
    global _atlas
    if _atlas is None:
        path = os.path.join(ROOT, "runs", "map.json")
        if not os.path.exists(path):
            from spread.client import Client
            with open(path, "w") as file:
                json.dump(Client().map(), file)
        with open(path) as file:
            _atlas = Atlas(json.load(file))
    return _atlas


def runs(tag: str) -> list[dict]:
    out = []
    for path in sorted(glob.glob(os.path.join(ROOT, "runs", tag, "*.json.gz"))):
        with gzip.open(path, "rt") as file:
            out.append(json.load(file))
    return out


def fold(b: dict, e: dict, cars: int) -> None:
    """One event into the record of one of the orders it is about; `cars` orders share it."""
    kind = e["kind"]
    if kind == "gig_booked":
        b["bookings"] += 1
        b.setdefault("first_booked_at", e["at"])
        b["booked_at"], b["booked_fee"], b["driver"] = e["at"], e["feeCents"] / cars, e["driverId"]
    elif kind in ("gig_dropped", "no_show"):
        b["drops"] += 1
    elif kind == "visit_failed":
        b["failed"] += 1
    elif kind == "deadline_close":
        b.setdefault("warned_at", e["at"])
    elif kind == "gig_expired":
        b.setdefault("expired_at", e["at"])
    elif kind == "picked_up":
        b["picked_at"] = e["at"]
    elif kind == "delivered":
        b["delivered_at"] = e["at"]
    elif kind == "order_cancelled":
        b["cancelled"] = True
    elif kind == "ledger":
        key = {"driver_fee": "fees", "revenue": "revenue", "late_refund": "refund", "undelivered_penalty": "refund"}.get(e["line"]["kind"], "other")
        b[key] += e["line"]["cents"] / cars


def rows(run: dict) -> list[dict]:
    """One row per price request of a run."""
    a, events = atlas(), run["events"]
    homes = {d["id"]: d["homePlaceId"] for d in run["roster"]}
    near = lambda place, km: sum(1 for home in homes.values() if a.crow_km(home, place) <= km)
    won = {e["order"]["id"]: e for e in events if e["kind"] == "order_won"}
    gig_orders, posts = {}, {}
    truth = {o["orderId"]: o["legs"] for o in run["reveal"]["orders"]}
    by_order: dict[str, dict] = {}
    views: dict[str, int] = {}
    for g in run["reveal"]["views"]:
        views[g["gigId"]] = views.get(g["gigId"], 0) + 1
    # gigs are not in the events: recover gig -> order from picked_up/delivered/visit_failed lines and ledger lines
    def carries(gig_id: str, order_id: str) -> None:
        if order_id not in gig_orders.setdefault(gig_id, []):
            gig_orders[gig_id].append(order_id)

    for e in events:
        if e["kind"] in ("picked_up", "delivered", "visit_failed"):
            carries(e["gigId"], e["orderId"])
        elif e["kind"] == "ledger" and e["line"].get("gigId") and e["line"].get("orderId"):
            carries(e["line"]["gigId"], e["line"]["orderId"])
    first_fee: dict[str, int] = {}
    for gig in sorted(run.get("gigs", []), key=lambda g: g["postedAt"]):
        for stop in gig["stops"]:
            carries(gig["id"], stop["orderId"])
        first_fee.setdefault(gig["stops"][0]["orderId"], gig["schedule"][0]["feeCents"])
    for e in events:  # what happens to a gig happens to every order with a car in it; its money is shared between them
        line = e.get("line", {})
        owners = [o for o in [e.get("orderId") or line.get("orderId")] if o] or gig_orders.get(e.get("gigId") or line.get("gigId"), [])
        for order_id in owners:
            fold(by_order.setdefault(order_id, {"bookings": 0, "drops": 0, "failed": 0, "fees": 0, "refund": 0, "revenue": 0, "other": 0}), e, len(owners))
    out = []
    for item in run["reveal"]["requests"]:
        r = item["request"]
        leg = r["legs"][0]
        pu, de = leg["pickup"]["placeId"], leg["delivery"]["placeId"]
        quote = item["quote"] or {}
        first = r["options"][0]
        row = {
            "seed": run["seed"], "id": r["id"], "dealer": r["dealerId"], "batch": r["batchId"], "arrived": r["arrivedAt"], "day": r["arrivedAt"] // DAY,
            "hour": r["arrivedAt"] % DAY / 60, "legs": len(r["legs"]), "pu": pu, "de": de, "km": a.km[(pu, de)], "minutes": a.minutes[(pu, de)],
            "typical": r["referenceFeeCents"], "list": first["listPriceCents"], "first_option": first["kind"], "n_options": len(r["options"]),
            "private_pu": leg["pickup"]["privateAddress"], "private_de": leg["delivery"]["privateAddress"], "premium": leg["car"]["premium"],
            "electric": leg["car"]["electric"], "note": r["note"]["text"] if r["note"] else None, "ready": leg["pickup"]["window"]["from"],
            "pu_window_to": leg["pickup"]["window"]["to"], "outcome": item["outcome"], "option": item["option"],
            "drivers_pu": near(pu, 30), "drivers_de": near(de, 30),
        }
        for option in r["options"]:
            k = option["kind"]
            row[f"list_{k}"], row[f"deadline_{k}"] = option["listPriceCents"], option["deadline"]
            row[f"q_{k}"] = quote.get(k)
            row[f"m_{k}"] = quote[k] / option["listPriceCents"] if k in quote else math.nan
        if r["id"] in won:
            order = won[r["id"]]["order"]
            row.update(price=order["priceCents"], deadline=order["deadline"], last_pickup=order["lastPickupAt"], won_at=won[r["id"]]["at"],
                       list_won=row[f"list_{order['option']}"], **by_order.get(r["id"], {}))
            row["first_fee"] = first_fee.get(r["id"])
            if "delivered_at" in row:
                row["late"] = row["delivered_at"] - row["deadline"]
            row["on_time"] = bool(row.get("late", 1) <= 0) and row.get("refund", 0) == 0
            row["margin"] = row.get("revenue", 0) + row.get("fees", 0) + row.get("refund", 0) + row.get("other", 0)
            if row.get("driver"):
                row["home"] = homes.get(row["driver"])
            legs_truth = truth.get(r["id"])
            if legs_truth:
                row.update(t_ready=legs_truth[0]["readyAt"], t_released=legs_truth[0]["releasedAt"], t_deadline=legs_truth[0]["noteDeadline"],
                           t_manual=legs_truth[0]["manualGearbox"], t_plates=legs_truth[0]["needsPlates"], t_summer=legs_truth[0]["summerTyres"])
        out.append(row)
    return out


def table(tag: str) -> pd.DataFrame:
    return pd.DataFrame([row for run in runs(tag) for row in rows(run)])


if __name__ == "__main__":
    import sys
    t = table(sys.argv[1])
    print(t.groupby("seed").agg(requests=("id", "size"), won=("price", "count"), on_time=("on_time", "mean"), margin=("margin", lambda s: s.sum() / 100)))
