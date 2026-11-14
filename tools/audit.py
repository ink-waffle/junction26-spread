"""Loss audit of a saved run: where money leaks on orders we won, what we leave on requests we lost, and when drivers have time.

    python -m tools.audit main-m4-r0.0                      # the tables behind AUDIT.md, per week over the run's seeds
    python -m tools.audit main-m4-r0.0 --pool base1,explore1  # other runs on the same seeds, for each request's threshold

A request recurs in every run of its seed at a different price. From those answers we fit, with the market's own curve
(dispatch/prior.py), a level per seed and day and then a threshold per request: the multiple of the list price at which its dealer buys half the time."""
from __future__ import annotations

import argparse
import collections
import glob
import math
import os

import numpy as np
import pandas as pd

from dispatch import notes, prior, timetable
from dispatch.atlas import DAY
from tools.study import ROOT, atlas, runs

KINDS = ["same_day", "next_day", "within_3_days"]
REQUEST_SLOPE, REQUEST_SPREAD = 20.0, 0.15  # one dealer's answer to one request is sharper than the curve around a day's level; best on a held-out run
pd.set_option("display.width", 250, "display.max_columns", 60, "display.max_rows", 200)


def trust_counts(run: dict) -> dict[str, int]:
    """Each request's dealer trust count at the minute the request arrived (RULES.md, level 8)."""
    count, dealer_of, refunded, at_request = collections.Counter(), {}, set(), {}
    for e in run["events"]:
        if e["kind"] == "price_request":
            dealer_of[e["request"]["id"]] = e["request"]["dealerId"]
            at_request[e["request"]["id"]] = count[e["request"]["dealerId"]]
        elif e["kind"] == "ledger" and e["line"].get("orderId") in dealer_of:
            order, dealer = e["line"]["orderId"], dealer_of[e["line"]["orderId"]]
            if e["line"]["kind"] in ("late_refund", "undelivered_penalty") and order not in refunded:
                refunded.add(order)
                count[dealer] = (count[dealer] - 1) // 2 if e["line"]["kind"] == "late_refund" else count[dealer] // 2
            elif e["line"]["kind"] == "revenue":
                count[dealer] = min(25, count[dealer] + 1)
    return at_request


def rows(run: dict) -> list[dict]:
    """One row per request: our quote, the dealer's answer and, for a won order, its story and its account."""
    a, trust, story = atlas(), trust_counts(run), collections.defaultdict(lambda: collections.defaultdict(float))
    gigs = sorted(run["gigs"], key=lambda g: g["postedAt"])
    order_of = {g["id"]: g["stops"][0]["orderId"] for g in gigs}
    won = {e["order"]["id"]: e for e in run["events"] if e["kind"] == "order_won"}
    for e in run["events"]:
        kind, line = e["kind"], e.get("line") or {}
        order = e["order"]["id"] if kind == "order_changed" else e.get("orderId") or line.get("orderId") or order_of.get(e.get("gigId") or line.get("gigId"))
        s = story[order]
        if kind == "ledger":
            s["eur_" + line["kind"]] += line["cents"] / 100
        elif kind == "order_changed":
            s["slot_moved" if "booked hours" in e["message"]["text"] else "snow" if "Snow" in e["message"]["text"] else "redirected"] += 1
        elif kind == "order_cancelled":
            s["cancelled"] = 1
        elif kind == "gig_booked":
            s.setdefault("first_booked_at", e["at"])
        elif kind in ("gig_dropped", "no_show", "driver_late", "visit_failed", "deadline_close"):
            s[kind] += 1
        elif kind == "picked_up" and not e["leg"]:
            s["picked_at"] = e["at"]
    snow = [e for e in run["events"] if e["kind"] == "forecast"]
    out = []
    for item in run["reveal"]["requests"]:
        r, quote = item["request"], item["quote"] or {}
        leg, facts = r["legs"][0], notes.read(r["note"], r["arrivedAt"])
        ends, car = (leg["pickup"]["placeId"], leg["delivery"]["placeId"]), leg["car"]
        drive = a.minutes[ends] + 40 * bool(car["electric"] and (car["chargePercent"] if car["chargePercent"] is not None else 100) < 30 and a.km[ends] > 200)
        row = {"seed": run["seed"], "id": r["id"], "dealer": r["dealerId"], "arrived": r["arrivedAt"], "day": r["arrivedAt"] // DAY, "hour": r["arrivedAt"] % DAY // 60, "legs": len(r["legs"]),
               "pu": ends[0], "de": ends[1], "km": a.km[ends], "minutes": a.minutes[ends], "typical": r["referenceFeeCents"] / 100, "list": r["options"][0]["listPriceCents"] / 100,
               "klass": "trade-in" if len(r["legs"]) > 1 else "private pickup" if leg["pickup"]["privateAddress"] else "premium" if car["premium"] else "private delivery" if leg["delivery"]["privateAddress"] else "plain",
               "fact": facts != notes.NoteFacts(), "ready": leg["pickup"]["window"]["from"], "trust": trust.get(r["id"], 0), "won": item["outcome"] == "won", "option": item["option"]}
        for i, option in enumerate(r["options"]):
            spans = timetable.chances(r, option, facts, drive) if len(r["legs"]) == 1 else []
            row.update({f"list_{option['kind']}": option["listPriceCents"] / 100, f"skip_{option['kind']}": i, f"room_{option['kind']}": sum(b - c for c, b in spans) / 60})
            if option["kind"] in quote:
                row[f"q_{option['kind']}"] = quote[option["kind"]] / 100
        if r["id"] in won:
            order, mine = won[r["id"]]["order"], [g for g in gigs if g["stops"][0]["orderId"] == r["id"]]
            truth = next((o["legs"][0] for o in run["reveal"]["orders"] if o["orderId"] == r["id"]), {})
            picked = truth.get("pickedUpAt")
            row.update(won_at=won[r["id"]]["at"], price=order["priceCents"] / 100, last_pickup=order["lastPickupAt"], list_won=row[f"list_{order['option']}"], first_posted=mine[0]["postedAt"] if mine else np.nan,
                       picked=picked, snowy=any(f["from"] <= (picked or -1) < f["to"] and set(ends) & set(f["placeIds"]) for f in snow), **story[r["id"]])
        out.append(row)
    return out


def table(tag: str) -> pd.DataFrame:
    t = pd.DataFrame([row for run in runs(tag) if "gigs" in run for row in rows(run)])
    for column in ("eur_revenue", "eur_driver_fee", "eur_late_refund", "eur_undelivered_penalty", "eur_failed_visit", "eur_waiting", "eur_fine", "eur_release_fee",
                   "gig_dropped", "no_show", "driver_late", "visit_failed", "deadline_close", "cancelled", "redirected", "slot_moved"):
        t[column] = t[column].fillna(0.0) if column in t else 0.0
    t["margin"] = t[[c for c in t.columns if c.startswith("eur_")]].sum(axis=1)
    t["late"] = t.eur_late_refund + t.eur_undelivered_penalty < 0
    t["warned"] = t.deadline_close > 0
    t["kmb"] = pd.cut(t.km, [0, 40, 100, 200, 400, 2000], labels=["<40 km", "40-100", "100-200", "200-400", ">400"])
    return t


def answers(tag: str, seeds: set) -> pd.DataFrame:
    """One row per request quoted on a single option in a run: log multiple, won or not, and what the prior knows of its level."""
    out = []
    for run in runs(tag):
        if run.get("seed") not in seeds or run.get("level", 8) != 8 or "reveal" not in run:
            continue
        trust = trust_counts(run)
        for item in run["reveal"]["requests"]:
            r, quote = item["request"], item["quote"] or {}
            if len(quote) != 1:
                continue
            (kind, cents), leg = next(iter(quote.items())), r["legs"][0]
            skip, option = next((i, o) for i, o in enumerate(r["options"]) if o["kind"] == kind)
            if cents < 3 * option["listPriceCents"]:
                known = prior.PLACES["from"].get(leg["pickup"]["placeId"], 0) + prior.PLACES["to"].get(leg["delivery"]["placeId"], 0) - prior.SPEED * skip + prior.TRUST * trust.get(r["id"], 0)
                out.append((f"{run['seed']}|{r['arrivedAt'] // DAY}", f"{run['seed']}|{r['id']}", math.log(cents / option["listPriceCents"]), float(item["outcome"] == "won"), known))
    return pd.DataFrame(out, columns=["day", "request", "x", "won", "known"])


def levels(groups: pd.Series, base: np.ndarray, x: np.ndarray, y: np.ndarray, slope: float, spread: float = 0.0) -> dict:
    """One level per group by Newton steps on y ~ sigmoid(slope * (base + level - x)); shrunk to zero with the given spread."""
    codes, names = pd.factorize(groups)
    level = np.zeros(len(names))
    for _ in range(60):
        p = 1 / (1 + np.exp(-slope * (base + level[codes] - x)))
        gradient = np.bincount(codes, slope * (y - p), len(names)) - (level / spread ** 2 if spread else 0)
        curvature = np.bincount(codes, slope * slope * p * (1 - p), len(names)) + (1 / spread ** 2 if spread else 0)
        level += np.clip(gradient / np.maximum(curvature, 1e-9), -0.5, 0.5)
    return dict(zip(names, level))


def thresholds(t: pd.DataFrame, pool: list[str]) -> pd.DataFrame:
    """Adds each request's day level and own threshold (log multiple of the first option's list price, before trust)."""
    seen = pd.concat([answers(tag, set(t.seed)) for tag in pool], ignore_index=True)
    day = levels(seen.day, seen.known.values, seen.x.values, seen.won.values, prior.SLOPE)
    own = levels(seen.request, seen.known.values + seen.day.map(day).values, seen.x.values, seen.won.values, REQUEST_SLOPE, REQUEST_SPREAD)
    t["day_level"] = (t.pu.map(prior.PLACES["from"]).fillna(0) + t.de.map(prior.PLACES["to"]).fillna(0) + (t.seed + "|" + t.day.astype(str)).map(day)).values
    t["threshold"] = t.day_level + (t.seed + "|" + t.id).map(own).fillna(0).values
    quoted = []
    for r in t.itertuples():  # the option we priced, as multiples of its list price: our quote and the dealer's threshold for it
        kind = next((k for k in KINDS if getattr(r, f"q_{k}", np.nan) == getattr(r, f"q_{k}", np.nan)), None)
        shift = (-prior.SPEED * getattr(r, f"skip_{kind}") + prior.TRUST * r.trust) if kind else np.nan
        quoted.append((kind, getattr(r, f"q_{kind}") / getattr(r, f"list_{kind}") if kind else np.nan, math.exp(r.threshold + shift) if kind else np.nan, getattr(r, f"room_{kind}") if kind else np.nan))
    t[["kind", "quote", "buys_at", "room"]] = pd.DataFrame(quoted, index=t.index)
    return t


def cause(r) -> str:
    if r.redirected:
        return "redirected by the dealer"
    if r.slot_moved or (r.klass == "private pickup" and r.no_show):
        return "private slot missed"
    if r.picked != r.picked:
        return "never collected"
    if r.picked <= r.last_pickup:
        return "collected in time, slow drive in snow" if r.snowy else "collected in time by the stated facts, late by the note's" if r.fact else "collected in time, slow drive"
    if r.first_booked_at == r.first_booked_at and r.first_booked_at < r.last_pickup - 180:
        return "booked in time, then dropped" if r.gig_dropped else "booked in time, collected too late"
    return "no driver before the warning"


def pairs(w: pd.DataFrame, hold: int) -> tuple[int, float]:
    """Plain won cars that could share a gig, and their typical fees: B follows A when B's pickup is within 30 road km of A's delivery,
    the two fit in 12 h of driving, B can still be collected after A is delivered, and they were won at most `hold` minutes apart."""
    a, cars, typical = atlas(), 0, 0.0
    for _, g in w[w.klass == "plain"].groupby("seed"):
        order, used = list(g.sort_values("won_at").itertuples()), set()
        for i, first in enumerate(order):
            for j, second in enumerate(order):
                if i == j or i in used or j in used or abs(first.won_at - second.won_at) > hold or a.km[(first.de, second.pu)] > 30:
                    continue
                hop, start = a.minutes[(first.de, second.pu)], max(first.ready, first.won_at, second.won_at)
                if first.minutes + hop + second.minutes <= 12 * 60 and start <= first.last_pickup and second.ready - 360 <= start + first.minutes + hop <= second.last_pickup:
                    used.update((i, j))
                    cars, typical = cars + 2, typical + first.typical + second.typical
    return cars, typical


def requote(t: pd.DataFrame, mask: pd.Series, position: float, fee: float, refund: float) -> tuple[float, float]:
    """Expected wins and margin if the masked requests were quoted at `position` (log) against their day's level, on the option we priced."""
    s = t[mask & t.kind.notna()]
    shift = np.log(s.buys_at) - s.threshold  # the option's speed and the dealer's trust
    multiple = np.exp(s.day_level + shift + position)
    chance = 1 / (1 + np.exp(-REQUEST_SLOPE * (np.log(s.buys_at) - np.log(multiple))))
    lists = np.array([getattr(r, f"list_{r.kind}") for r in s.itertuples()])
    return chance.sum(), (chance * (multiple * lists * (1 - refund) - fee * s.typical)).sum()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("tag")
    parser.add_argument("--pool", help="runs on the same seeds for the thresholds, separated by commas; default: every saved run")
    args = parser.parse_args()
    t = table(args.tag)
    n, w = t.seed.nunique(), None
    pool = args.pool.split(",") if args.pool else sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(os.path.join(ROOT, "runs", "*", "halal-01.json.gz")) if os.path.getsize(p))
    t = thresholds(t, pool)
    w = t[t.won & (t.cancelled == 0)].copy()
    per_week = lambda frame: len(frame) / n
    print(f"{args.tag}: {n} weeks; requests {per_week(t):.0f}, won {per_week(w):.0f}, margin €{t.margin.sum() / n:,.0f}, late {w.late.mean():.1%}, worst seed {1 - w.groupby('seed').late.mean().max():.1%} on time")

    print("\n1. THE ACCOUNT, per week:", {c[4:]: round(t[c].sum() / n) for c in t.columns if c.startswith("eur_")})
    late = w[w.late].assign(cause=lambda d: d.apply(cause, axis=1))
    g = late.groupby("cause").agg(orders=("id", "size"), euros=("margin", lambda s: (late.loc[s.index, "eur_late_refund"] + late.loc[s.index, "eur_undelivered_penalty"]).sum()))
    print((g / n).round(1).sort_values("euros").to_string())
    w["fee"], w["wait"] = -w.eur_driver_fee / w.typical, w.first_booked_at - w.first_posted
    tail, rest = w[w.warned], w[~w.warned]
    print(f"\nwarned without a driver: {per_week(tail):.1f} orders, in the app a median {((tail.last_pickup - 180 - tail.first_posted) / 60).median():.0f} h before the warning; late {tail.late.mean():.0%}; "
          f"margin €{tail.margin.mean():.1f} each against €{rest.margin.mean():.1f}; fees above 0.85 x typical €{(-tail.eur_driver_fee - 0.85 * tail.typical).sum() / n:,.0f}, refunds €{-(tail.eur_late_refund + tail.eur_undelivered_penalty).sum() / n:,.0f}")
    for lead in (48, 24, 12):
        at = w.last_pickup - 180 - lead * 60
        still = w[(w.first_posted <= at) & ~(w.first_booked_at <= at)]
        print(f"   {lead} h before the warning: {per_week(still):.1f} orders still open, {still.warned.mean():.0%} of them end warned; 0.3 x their typical fee = €{0.3 * still.typical.sum() / n:,.0f}")
    print(f"not warned: fee x{rest.fee.mean():.2f}; booked within 5 min {(rest.wait <= 5).mean():.0%}, 30 min {(rest.wait <= 30).mean():.0%}; drops {w.gig_dropped.sum() / n:.0f}; failed visits {w.visit_failed.sum() / n:.2f}; driver_late {w.driver_late.sum() / n:.2f}")
    slower = w[[getattr(r, f"skip_{r.option}") > 0 for r in w.itertuples()]]
    room = pd.Series([max([getattr(r, f"room_{k}") for k in KINDS if getattr(r, f"skip_{k}", 9) < getattr(r, f"skip_{r.option}")], default=0) for r in slower.itertuples()], index=slower.index)
    print(f"won on a slower option than the fastest offered: {per_week(slower):.0f}; the faster one had 8 h or more of real room for {(room >= 8).sum() / n:.0f}: +{math.exp(prior.SPEED) - 1:.1%} of their price = €{slower.price[room >= 8].sum() * (math.exp(prior.SPEED) - 1) / n:,.0f}")

    for hold in (30, 120):
        cars, typical = pairs(w, hold)
        print(f"two cars in one gig, a car held {hold} min for a partner: {cars / n:.0f} of {per_week(w[w.klass == 'plain']):.0f} plain cars pair; their typical fees €{typical / n:,.0f} (0.15-0.25 x of that is the saving)")

    print("\n2. REQUESTS: our quote against the request's own threshold, per week")
    over = np.log(t.quote / t.buys_at).where(t.quote < 3, 9)
    how = pd.cut(over, [-9, -0.05, 0.05, 0.15, 0.30, 8, 10], labels=["5%+ below", "within 5%", "5-15% above", "15-30% above", "30%+ above", "declined"])
    print((t.groupby(how, observed=True).agg(requests=("id", "size"), won=("won", "sum"), margin=("margin", "sum")) / n).round(1).to_string())
    t["daytype"] = pd.qcut(t.groupby(["seed", "day"]).day_level.transform("median"), 4, labels=["cheapest days", "cheap", "dear", "dearest days"])
    t["roomb"] = pd.cut(t.room, [-1, 5, 8, 12, 1000], labels=["room < 5 h", "5-8 h", "8-12 h", ">= 12 h"])
    for key in ("kmb", "klass", "kind", "roomb", "day", "daytype"):
        g = t.groupby(key, observed=True).agg(requests=("id", "size"), won=("won", "sum"), quote=("quote", lambda s: s[s < 3].median()), buys_at=("buys_at", "median"), margin=("margin", "sum"),
                                              late=("late", "sum"), warned=("warned", "sum"))
        g["won_share"], g["per_won"], g["late"], g["warned"] = g.won / g.requests, g.margin / g.won, g.late / g.won, g.warned / g.won
        g[["requests", "won", "margin"]] /= n
        print(f"\nby {key}:\n{g.round(2).to_string()}")
    safe = (t.klass == "plain") & (t.room >= 8)
    print("\nrequotes: a class quoted at one position against its day's level, at a stated fee (x typical) and refund share; now -> then")
    for name, mask, position, fee, refund in (("dearest days, safe, up to 400 km", safe & (t.daytype == "dearest days") & (t.km <= 400), -0.05, 1.0, 0.012),
                                              ("over 400 km, safe, at today's cost", safe & (t.km > 400), 0.0, 1.0, 0.024), ("over 400 km, safe, at a dearer cost", safe & (t.km > 400), 0.0, 1.1, 0.035),
                                              ("premium with 8 h of room", (t.klass == "premium") & (t.room >= 8), 0.05, 1.1, 0.02)):
        wins, margin = requote(t, mask, position, fee, refund)
        now = t[mask & t.won & (t.cancelled == 0)]
        print(f"  {name:<36} {mask.sum() / n:4.0f} requests at {position:+.2f}: won {per_week(now):.0f} -> {wins / n:.0f}, margin €{now.margin.sum() / n:,.0f} -> €{margin / n:,.0f}")
    dealers = t.groupby(["seed", "dealer"]).agg(requests=("id", "size"), won=("won", "sum"), margin=("margin", "sum"), count=("trust", "max")).sort_values(["seed", "requests"], ascending=[True, False])
    dealers["rank"] = pd.cut(dealers.groupby("seed").cumcount(), [-1, 0, 2, 5, 20, 99], labels=["biggest", "2-3", "4-6", "7-21", "22+"])
    g = dealers.groupby("rank", observed=True).agg(requests=("requests", "sum"), won=("won", "sum"), margin=("margin", "sum"), highest_count=("count", "mean"))
    g[["requests", "won", "margin"]] /= n
    print(f"\ndealers by size:\n{g.round(1).to_string()}\ntrust paid €{(w.price * (1 - np.exp(-prior.TRUST * w.trust))).sum() / n:,.0f} a week; by day {(w.assign(u=w.price * (1 - np.exp(-prior.TRUST * w.trust))).groupby('day').u.sum() / w.groupby('day').price.sum()).round(3).to_dict()}")

    print("\n3. TIMING: gigs by the day they were first posted (0 = Monday)")
    w["post_day"] = w.first_posted // DAY
    g = w.groupby("post_day").agg(orders=("id", "size"), in_5_min=("wait", lambda s: (s <= 5).mean()), in_30_min=("wait", lambda s: (s <= 30).mean()), in_3_h=("wait", lambda s: (s <= 180).mean()),
                                  median_wait=("wait", "median"), warned=("warned", "mean"), late=("late", "mean"), margin_each=("margin", "mean"))
    g["orders"] /= n
    print(g.round(2).to_string())
    clock = collections.Counter()
    for run in runs(args.tag):
        lookers, bookers = collections.defaultdict(set), collections.defaultdict(set)
        for e in run["events"]:
            if e["kind"] in ("gig_viewed", "gig_booked"):
                (lookers if e["kind"] == "gig_viewed" else bookers)[e["at"] // DAY].add(e["driverId"])
                clock[(e["at"] // DAY, e["kind"])] += 1
        for d in range(8):
            clock[(d, "lookers")] += len(lookers[d])
            clock[(d, "bookers")] += len(bookers[d])
    print("per day: bookings, drivers who looked, drivers who booked:", {d: (round(clock[(d, 'gig_booked')] / n), round(clock[(d, 'lookers')] / n), round(clock[(d, 'bookers')] / n)) for d in range(8)})


if __name__ == "__main__":
    main()
