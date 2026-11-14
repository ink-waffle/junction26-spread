"""What is a night of many give-backs made of? For each week, the bookings held at each midnight for a car that must be collected that day, and those given
back in the hour after it: whose they are (a driver with one such gig or several, at home that day or at work), which cars (a batch, one yard, one town),
when and at what fee they were booked.

    python -m tools.night_study surprise-weighs surprise-weighs-wide              # all nights together, and each week's worst night in one line
    python -m tools.night_study surprise-weighs --seeds halal-02,halal-08         # those weeks' worst night in detail
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict

import pandas as pd

from dispatch.atlas import DAY, HOUR
from tools.study import runs


def nights(run: dict) -> list[dict]:
    """One row per booking held at a midnight for a car whose last day begins then."""
    events = run["events"]
    owners = {g["id"]: list(dict.fromkeys(s["orderId"] for s in g["stops"])) for g in run["gigs"]}
    requests = {r["request"]["id"]: r["request"] for r in run["reveal"]["requests"]}
    homes = {d["id"]: d["homePlaceId"] for d in run["roster"]}
    last = {e["order"]["id"]: e["order"]["lastPickupAt"] for e in events if e["kind"] == "order_won"}
    won = {e["order"]["id"]: e["at"] for e in events if e["kind"] == "order_won"}
    refunded = {e["line"]["orderId"] for e in events if e["kind"] == "ledger" and e["line"]["kind"] in ("late_refund", "undelivered_penalty")}
    paid = {e["line"]["orderId"] for e in events if e["kind"] == "ledger" and e["line"]["kind"] == "revenue"}
    batch = Counter(r["batchId"] for r in requests.values() if r["batchId"] and r["id"] in won)  # batch -> cars of it that we won
    looked, active = defaultdict(set), defaultdict(set)  # day -> drivers who looked at a gig that day; who booked one or left for one
    for v in run["reveal"]["views"]:
        looked[v["at"] // DAY].add(v["driverId"])
    for e in events:
        if e["kind"] in ("gig_booked", "gig_started") and e.get("driverId"):
            active[e["at"] // DAY].add(e["driverId"])
    out, held, day = [], {}, 0  # gig -> its booking, while a driver holds it and has not left
    for e in events:
        while e["at"] >= (day + 1) * DAY:
            day += 1
            for gig, booking in held.items():
                if any(last.get(o, 0) // DAY == day for o in owners[gig]):
                    out.append(dict(booking, gig=gig, night=day, gave_back=False))
        if e["kind"] == "gig_booked" and e["gigId"] in owners:
            order = owners[e["gigId"]][0]
            request = requests[order]
            held[e["gigId"]] = {"seed": run["seed"], "driver": e["driverId"], "home": homes.get(e["driverId"]), "booked": e["at"], "order": order, "cars": len(owners[e["gigId"]]),
                                "fee": e["feeCents"] / sum(requests[o]["referenceFeeCents"] for o in owners[e["gigId"]]), "from": request["legs"][0]["pickup"]["placeId"],
                                "dealer": request["dealerId"], "batch": batch.get(request["batchId"], 0), "won": won.get(order, 0), "late": order in refunded or order not in paid}
        elif e["kind"] in ("gig_dropped", "no_show", "gig_started"):
            if e["kind"] == "gig_dropped" and e["at"] % DAY < HOUR:
                for row in out:
                    if row["gig"] == e["gigId"] and row["night"] == e["at"] // DAY:
                        row["gave_back"] = True
            held.pop(e["gigId"], None)
    load = Counter((row["night"], row["driver"]) for row in out)
    back = Counter((row["night"], row["driver"]) for row in out if row["gave_back"])
    yard = Counter((row["night"], row["from"]) for row in out)
    for row in out:
        key = (row["night"], row["driver"])
        row["driver's gigs that day"], row["driver gave back"] = load[key], back[key]
        row["driver at work that day"] = row["driver"] in active[row["night"]]
        row["driver looked that day"] = row["driver"] in looked[row["night"]]
        row["same yard that day"] = yard[(row["night"], row["from"])]
        row["booked days before"] = row["night"] - row["booked"] // DAY
    return out


def cut(t: pd.DataFrame, by, n: int) -> str:
    return t.groupby(by, observed=True).agg(per_week=("gave_back", lambda s: len(s) / n), gave_back=("gave_back", "mean"), late=("late", "mean")).round(3).to_string()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tags", nargs="+")
    parser.add_argument("--seeds", default="")
    args = parser.parse_args()
    pd.set_option("display.width", 220)
    weeks = [run for tag in args.tags for run in runs(tag) if not args.seeds or run["seed"] in args.seeds.split(",")]
    t, n = pd.DataFrame([row for run in weeks for row in nights(run)]), len(weeks)
    t = t[t.night < 5]  # the nights before working days of the week itself
    worst = t.groupby(["seed", "night"]).gave_back.sum().groupby("seed").idxmax()
    t["worst night"] = [(seed, night) in set(worst) for seed, night in zip(t.seed, t.night)]
    for seed, night in worst if args.seeds else []:
        w = t[(t.seed == seed) & (t.night == night)]
        g, drivers = w[w.gave_back], w.groupby("driver").agg(held=("gave_back", "size"), back=("gave_back", "sum"), at_work=("driver at work that day", "first"), looked=("driver looked that day", "first"))
        gave = drivers[drivers.back > 0]
        print(f"\n{seed}, night before day {night}: {len(w)} bookings held for that day by {len(drivers)} drivers; {len(g)} given back by {len(gave)} drivers; late: {g.late.sum()} of the given back, {w[~w.gave_back].late.sum()} of the kept")
        print(f"  drivers who gave back: {int((gave.back == gave.held).sum())} gave back all they held, {int((gave.back < gave.held).sum())} kept some; booked or left for a gig that day: {int(gave.at_work.sum())} of {len(gave)}, looked at a gig: {int(gave.looked.sum())} (the drivers who kept all: {int(drivers[drivers.back == 0].at_work.sum())} and {int(drivers[drivers.back == 0].looked.sum())} of {int((drivers.back == 0).sum())})")
        print(f"  by the driver's gigs for that day (gigs: held/given back): " + ", ".join(f"{k}: {int(v.held.sum())}/{int(v.back.sum())}" for k, v in drivers.groupby(drivers.held.clip(upper=4))))
        print(f"  homes of those drivers: {dict(Counter(g.home).most_common(5))}")
        print(f"  pickup places, held/given back: " + ", ".join(f"{place} {len(v)}/{int(v.gave_back.sum())}" for place, v in sorted(w.groupby("from"), key=lambda kv: -len(kv[1]))[:6]))
        print(f"  cars of a batch we won 5+ of: held {int((w.batch >= 5).sum())}, given back {int((g.batch >= 5).sum())}; dealers of the given back: {dict(Counter(g.dealer).most_common(4))}")
        print(f"  booked days before, held/given back: " + ", ".join(f"{k}: {len(v)}/{int(v.gave_back.sum())}" for k, v in w.groupby("booked days before")) + f"; fee x typical: given back {g.fee.mean():.2f}, kept {w[~w.gave_back].fee.mean():.2f}")
        print(f"  hour booked (given back): {dict(sorted(Counter(g.booked % DAY // HOUR // 3 * 3).items()))}; two-car gigs: held {int((w.cars > 1).sum())}, given back {int((g.cars > 1).sum())}")
    print(f"\n{n} weeks, the nights before Tuesday to Friday: {len(t) / n:.0f} bookings a week held at midnight for a car that must be collected that day, {t.gave_back.mean():.1%} given back in the hour after it")
    for name, by in {"worst night of its week": t["worst night"], "the driver's gigs for that day": t["driver's gigs that day"].clip(upper=4), "driver booked or left for a gig that day": [t["worst night"], t["driver at work that day"]], "driver looked at a gig that day": [t["worst night"], t["driver looked that day"]],
                     "cars from the same yard held for that day": pd.cut(t["same yard that day"], [0, 1, 3, 6, 12, 100]), "a batch we won 5+ cars of": [t["worst night"], t.batch >= 5],
                     "booked days before": t["booked days before"].clip(upper=3), "fee x typical": pd.cut(t.fee, [0, 0.8, 0.9, 1.05, 1.2, 9]), "night": t.night}.items():
        print(f"\nby {name}\n" + cut(t, by, n))
    if not args.seeds:
        print("\neach week's worst night: day, held, given back, drivers who gave back, of them booked or left for a gig that day, gave back all they held")
        for seed, night in worst:
            w = t[(t.seed == seed) & (t.night == night)]
            d = w.groupby("driver").agg(held=("gave_back", "size"), back=("gave_back", "sum"), at_work=("driver at work that day", "first"))
            d = d[d.back > 0]
            print(f"  {seed[-2:]}: day {night}, {len(w)}, {int(w.gave_back.sum())}, {len(d)}, {int(d.at_work.sum())}, {int((d.back == d.held).sum())}; batch cars held {int((w.batch >= 5).sum())} / given back {int((w[w.gave_back].batch >= 5).sum())}")


if __name__ == "__main__":
    main()
