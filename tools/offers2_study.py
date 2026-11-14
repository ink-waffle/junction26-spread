"""Why direct offers are not taken: the saved offers joined with each driver's gigs of ours (OFFERS2.md).

    python -m tools.offers2_study answers offers-x1 offers-x2    # answers by what the driver was doing for us, how near that ends, the fee, experience
    python -m tools.offers2_study bookers offers-x1 offers-x2    # offers to the driver who later booked that same car in the app
    python -m tools.offers2_study waiting orch-head-record       # cars that waited: was a driver of ours ending a gig near the pickup in time?
    python -m tools.offers2_study played offers2-vet-s14         # a run that sent offers: answers a week and the fee of the accepted ones
"""
from __future__ import annotations

import sys
from collections import defaultdict

import pandas as pd

from dispatch.atlas import DAY, HOUR
from tools.study import atlas, runs

NEAR_KM = 30


def held_gigs(run: dict) -> list[dict]:
    """One record per booking of a gig of ours: the driver, when they held, started and ended it, and where it starts and ends."""
    orders = {e["order"]["id"]: e["order"] for e in run["events"] if e["kind"] == "order_won"}
    gigs = {g["id"]: g for g in run["gigs"]}
    held, current = [], {}
    for e in run["events"]:
        kind, gig = e["kind"], gigs.get(e.get("gigId"))
        if kind == "gig_booked" and gig and gig["stops"][0]["orderId"] in orders and gig["stops"][-1]["orderId"] in orders:
            first, last = (orders[stop["orderId"]]["legs"][stop["leg"]] for stop in (gig["stops"][0], gig["stops"][-1]))
            current[gig["id"]] = {"driver": e["driverId"], "booked": e["at"], "gone": None, "started": None, "done": None, "orders": {s["orderId"] for s in gig["stops"]},
                                  "start": first["pickup"]["placeId"], "end": last["delivery"]["placeId"], "ready": first["pickup"]["window"]["from"]}
            held.append(current[gig["id"]])
        elif kind in ("gig_dropped", "no_show") and e["gigId"] in current:
            current[e["gigId"]]["gone"] = e["at"]
        elif kind == "gig_started" and e["gigId"] in current:
            current[e["gigId"]]["started"] = e["at"]
        elif kind == "delivered" and e["gigId"] in current:
            current[e["gigId"]]["done"] = e["at"]
    return held


def answers(tags: list[str]) -> None:
    a, rows = atlas(), []
    for run in (run for tag in tags for run in runs(tag)):
        roster = {d["id"]: d for d in run["roster"]}
        orders = {e["order"]["id"]: e["order"] for e in run["events"] if e["kind"] == "order_won"}
        typical = {item["request"]["id"]: item["request"]["referenceFeeCents"] for item in run["reveal"]["requests"]}
        held = defaultdict(list)
        for record in held_gigs(run):
            held[record["driver"]].append(record)
        for o in run.get("offers", []):
            if o["answer"] == "refused" or o["orderId"] not in orders:
                continue
            at, order = o["at"], orders[o["orderId"]]
            pickup = order["legs"][0]["pickup"]
            doing, end_km = "no gig of ours", None
            for r in held[o["driverId"]]:  # the driver's last gig of ours that counts at this minute
                if r["booked"] > at or (r["gone"] is not None and r["gone"] <= at) or (r["done"] is not None and r["done"] <= at and r["done"] // DAY != at // DAY):
                    continue
                doing = ("delivered today" if r["done"] is not None and r["done"] <= at else "driving" if r["started"] is not None and r["started"] <= at
                         else "booked for today" if (r["started"] or r["ready"]) // DAY == at // DAY else "booked for later")
                end_km = a.crow_km(r["end"], pickup["placeId"])
            rows.append({"doing": doing, "near": end_km is not None and end_km <= NEAR_KM, "now": pickup["window"]["from"] <= at + HOUR and order["lastPickupAt"] > at + HOUR,
                         "fee": o["feeCents"] / typical[o["orderId"]], "completed": roster[o["driverId"]]["completedGigs"],
                         "yes": o["answer"] == "accepted", "read": o["answer"] in ("accepted", "declined")})
    t = pd.DataFrame(rows)
    t["fee"], t["completed"] = pd.cut(t.fee, [0, .75, 1.05, 1.3, 9]), pd.cut(t.completed, [-1, 50, 150, 300, 9999])
    holds = t[t.doing.isin(["driving", "booked for today"])]
    for title, part, by in (("by what the driver does for us; near: that gig ends within 30 km of the pickup; now: the car can be collected now", t, ["doing", "near", "now"]),
                            ("by fee, as a multiple of the typical fee", t, ["fee"]), ("by completed gigs", t, ["completed"]),
                            ("drivers who hold a gig of ours for today, by completed gigs", holds, ["near", "now", "completed"])):
        print(title)
        print(part.groupby(by, observed=True).agg(offers=("yes", "size"), read=("read", "mean"), yes=("yes", "mean"), accepted=("yes", "sum")).round(3), "\n")


def bookers(tags: list[str]) -> None:
    rows = []
    for run in (run for tag in tags for run in runs(tag)):
        order_of = {g["id"]: g["stops"][0]["orderId"] for g in run["gigs"]}
        typical = {item["request"]["id"]: item["request"]["referenceFeeCents"] for item in run["reveal"]["requests"]}
        booked = defaultdict(list)
        for e in run["events"]:
            if e["kind"] == "gig_booked":
                booked[(order_of.get(e["gigId"]), e["driverId"])].append((e["at"], e["feeCents"]))
        for o in run.get("offers", []):
            later = [b for b in booked.get((o.get("orderId"), o["driverId"]), []) if b[0] > o["at"] + 10]
            if o["answer"] != "refused" and later:
                rows.append({"answer": o["answer"], "offered": o["feeCents"] / typical[o["orderId"]], "paid": later[0][1] / typical[o["orderId"]],
                             "minutes": later[0][0] - o["at"], "same day": later[0][0] // DAY == o["at"] // DAY})
    t = pd.DataFrame(rows)
    t["offer at least what they took"] = t.offered >= t.paid - 0.01
    print("offers to the driver who later booked that car in the app:")
    print(t.groupby(["answer", "offer at least what they took", "same day"]).agg(offers=("paid", "size"), minutes=("minutes", "median"), offered=("offered", "mean"), paid=("paid", "mean")).round(2))


def waiting(tags: list[str], wait: int = 30) -> None:
    a, rows, chains, weeks = atlas(), [], [], 0
    for run in (run for tag in tags for run in runs(tag)):
        weeks += 1
        orders = {e["order"]["id"]: e["order"] for e in run["events"] if e["kind"] == "order_won"}
        gigs = {g["id"]: g for g in run["gigs"]}
        veteran = {d["id"] for d in run["roster"] if d["completedGigs"] >= 150}
        posted, booked = {}, {}
        for gig in run["gigs"]:
            for stop in gig["stops"]:
                posted[stop["orderId"]] = min(posted.get(stop["orderId"], 10 ** 9), gig["postedAt"])
        for e in run["events"]:
            if e["kind"] == "gig_booked" and e["gigId"] in gigs:
                for stop in gigs[e["gigId"]]["stops"]:
                    booked[stop["orderId"]] = e["at"]
        held = [r for r in held_gigs(run) if r["done"] is not None]
        days = defaultdict(list)
        for r in held:
            days[(r["driver"], r["done"] // DAY)].append(r)
        for day in days.values():  # a driver's gigs of ours in a row on one day: when did they book the next one?
            day.sort(key=lambda r: r["started"] or 0)
            chains += [{"near": a.crow_km(x["end"], y["start"]) <= NEAR_KM, "booked": "while driving" if (x["started"] or 0) <= y["booked"] < x["done"]
                        else "before" if y["booked"] < (x["started"] or 0) else "after delivering"} for x, y in zip(day, day[1:])]
        for order_id, order in orders.items():
            if order_id not in posted or len(order["legs"]) > 1 or booked.get(order_id, 10 ** 9) - posted[order_id] <= wait:
                continue
            pickup, until = order["legs"][0]["pickup"], min(booked.get(order_id, 10 ** 9), order["lastPickupAt"])
            ends = {r["driver"] for r in held if order_id not in r["orders"] and r["booked"] < until and posted[order_id] < r["done"] <= order["lastPickupAt"]
                    and r["done"] >= pickup["window"]["from"] - 2 * HOUR and a.crow_km(r["end"], pickup["placeId"]) <= NEAR_KM}
            rows.append({"drivers": len(ends), "veterans": len(ends & veteran)})
    t, c = pd.DataFrame(rows), pd.DataFrame(chains)
    print(f"{weeks} weeks. One-car orders without a driver {wait} minutes after their first posting: {len(t) / weeks:.0f} a week")
    print(f"of them, with a driver of ours ending a gig within {NEAR_KM} km of the pickup in time: {(t.drivers > 0).sum() / weeks:.0f} ({t.drivers.sum() / weeks:.0f} driver-car pairs a week); "
          f"with such a driver of 150 completed gigs or more: {(t.veterans > 0).sum() / weeks:.0f} ({t.veterans.sum() / weeks:.0f} pairs)")
    print("\na driver's next gig of ours on the same day, a week, by when they booked it:")
    print(c.groupby(["near", "booked"]).size().div(weeks).round(1))


def played(tags: list[str]) -> None:
    rows, weeks = [], 0
    for run in (run for tag in tags for run in runs(tag)):
        weeks += 1
        typical = {item["request"]["id"]: item["request"]["referenceFeeCents"] for item in run["reveal"]["requests"]}
        gigs = {g["id"]: g for g in run["gigs"]}
        for e in run["events"]:
            if e["kind"] == "offer_answered":
                gig = gigs[e["gigId"]]
                rows.append({"answer": e["answer"], "fee": gig["feeCents"] / sum(typical[o] for o in {s["orderId"] for s in gig["stops"]}) if e["answer"] == "accepted" else None})
    t = pd.DataFrame(rows)
    print(f"{weeks} weeks, offers a week: {len(t) / weeks:.1f}")
    print(t.answer.value_counts().div(weeks).round(1))
    print("fee of the accepted, as a multiple of the typical fee:", t.fee.describe().round(2).to_dict())


if __name__ == "__main__":
    {"answers": answers, "bookers": bookers, "waiting": waiting, "played": played}[sys.argv[1]](sys.argv[2:])
