"""Offline study of saved runs for the offers question: who books, how fast, and which cars could share a driver.

    python -m tools.offers_study bookers base1      # who books our gigs and how long they sit
    python -m tools.offers_study pairs base1        # how often two cars we hold could go in one gig or one chain
    python -m tools.offers_study offers offers-x1   # answers to direct offers by fee multiple and driver class
    python -m tools.offers_study shared offers-x3   # two cars in one gig against the same two cars in two gigs
    python -m tools.offers_study partners offers-px1  # requests that could pair with a waiting car: win rate and margin by quoted price
"""
from __future__ import annotations

import sys
from collections import defaultdict

import pandas as pd

from dispatch.atlas import DAY, HOUR
from tools.study import atlas, runs

NEAR_KM = 30


def gig_table(run: dict) -> pd.DataFrame:
    """One row per gig we posted: its order, places, typical fee, posting, first booking and the booker's home."""
    a = atlas()
    homes = {d["id"]: d["homePlaceId"] for d in run["roster"]}
    orders = {e["order"]["id"]: e["order"] for e in run["events"] if e["kind"] == "order_won"}
    typical = {item["request"]["id"]: item["request"]["referenceFeeCents"] for item in run["reveal"]["requests"]}
    warned = {}
    for e in run["events"]:
        if e["kind"] == "deadline_close":
            warned.setdefault(e["orderId"], e["at"])
    booked, last_place, rows = {}, {}, []
    position: dict[str, tuple[int, str]] = {}
    gig_driver = {}
    by_gig = defaultdict(list)
    for e in run["events"]:
        if "gigId" in e:
            by_gig[e["gigId"]].append(e)
    for e in run["events"]:  # where each driver was (by our gigs) when they booked
        if e["kind"] == "gig_booked":
            gig_driver[e["gigId"]] = e["driverId"]
            booked.setdefault(e["gigId"], (e["at"], e["driverId"], e["feeCents"], position.get(e["driverId"])))
        elif e["kind"] in ("picked_up", "delivered") and e["gigId"] in gig_driver:
            position[gig_driver[e["gigId"]]] = (e["at"], e["placeId"])
    for gig in run["gigs"]:
        order = orders.get(gig["stops"][0]["orderId"])
        if order is None:
            continue
        leg = order["legs"][gig["stops"][0]["leg"]]
        pu, de = leg["pickup"]["placeId"], leg["delivery"]["placeId"]
        row = {"seed": run["seed"], "gig": gig["id"], "order": order["id"], "pu": pu, "de": de, "posted": gig["postedAt"], "day": gig["postedAt"] // DAY,
               "typical": typical[order["id"]] * sum(1 for s in gig["stops"] if s["kind"] == "pickup") / len(order["legs"]), "fee0": gig["schedule"][0]["feeCents"],
               "ready": leg["pickup"]["window"]["from"], "deadline": order["deadline"], "last_pickup": order["lastPickupAt"], "minutes": a.minutes[(pu, de)],
               "warned": warned.get(order["id"]), "views": sum(1 for e in by_gig[gig["id"]] if e["kind"] == "gig_viewed"),
               "dropped": any(e["kind"] in ("gig_dropped", "no_show") for e in by_gig[gig["id"]])}
        if gig["id"] in booked:
            at, driver, fee, was = booked[gig["id"]]
            home = homes[driver]
            row.update(booked_at=at, wait=at - gig["postedAt"], driver=driver, fee=fee, home=home, home_pu_km=a.crow_km(home, pu), home_de_km=a.crow_km(home, de),
                       was_km=a.crow_km(was[1], pu) if was and was[0] >= at - at % DAY else None)
        rows.append(row)
    return pd.DataFrame(rows)


def bookers(tag: str) -> None:
    t = pd.concat(gig_table(run) for run in runs(tag))
    b = t[t.booked_at.notna()].copy()
    print(f"{len(t)} gigs, {len(b)} booked ({len(b) / len(t):.0%})")
    print("\nminutes from posting to first booking, by day of posting:")
    print(b.groupby("day").wait.describe(percentiles=[.25, .5, .75, .9]).round(0))
    b["who"] = "elsewhere"
    b.loc[b.home_de_km <= NEAR_KM, "who"] = "home at delivery"
    b.loc[b.home_pu_km <= NEAR_KM, "who"] = "home at pickup"
    b.loc[(b.home_pu_km <= NEAR_KM) & (b.home_de_km <= NEAR_KM), "who"] = "home at both"
    b.loc[b.was_km.notna() & (b.was_km <= NEAR_KM) & (b.home_pu_km > NEAR_KM), "who"] = "our gig left them at pickup"
    print("\nwho books (home within 30 km):")
    print(b.groupby("who").agg(n=("gig", "size"), wait=("wait", "median"), fee=("fee", lambda s: (s / b.loc[s.index, "typical"]).mean()), dropped=("dropped", "mean")).round(2))
    print("\nhome to pickup, km, of the booker:")
    print(b.home_pu_km.describe(percentiles=[.25, .5, .75, .9]).round(0))


def pairs(tag: str) -> None:
    """For each car we held without a driver: was there another such car that one driver could take right after it?"""
    a = atlas()
    out = []
    for run in runs(tag):
        t = gig_table(run)
        first = t.sort_values("posted").groupby("order").first().reset_index()
        last_booking = t[t.get("booked_at").notna()].groupby("order").booked_at.max() if "booked_at" in t else {}
        first["until"] = [last_booking.get(o, 10 ** 9) for o in first.order]  # the minute the car last got a driver
        for x in first.itertuples():
            back = chain = yard = False
            for y in first.itertuples():
                if x.order == y.order or not (y.posted < x.until and x.posted < y.until):  # both without a driver at some minute
                    continue
                start = max(x.posted, y.posted)
                # x then y in one day: x picked up no earlier than its ready time, y delivered by its deadline
                drive = x.minutes + a.minutes[(x.de, y.pu)] + y.minutes
                fits = max(start, x.ready) + drive <= min(y.deadline, x.deadline + a.minutes[(x.de, y.pu)] + y.minutes) and drive <= 12 * HOUR and max(start, x.ready) + x.minutes <= x.deadline
                if not fits:
                    continue
                if a.crow_km(x.de, y.pu) <= NEAR_KM:
                    chain = True
                    if a.crow_km(y.de, x.pu) <= NEAR_KM:
                        back = True
                if x.pu == y.pu:
                    yard = True
            out.append({"seed": run["seed"], "order": x.order, "chain": chain, "back": back, "yard": yard})
    p = pd.DataFrame(out)
    print("share of our cars that, while without a driver, had another such car ...")
    print(p.groupby("seed").agg(cars=("order", "size"), next_starts_where_it_ends=("chain", "mean"), out_and_back=("back", "mean"), same_yard=("yard", "mean")).round(3))
    print(p[["chain", "back", "yard"]].mean().round(3))


def offer_table(tag: str) -> pd.DataFrame:
    a = atlas()
    rows = []
    for run in runs(tag):
        events = run["events"]
        roster = {d["id"]: d for d in run["roster"]}
        orders = {e["order"]["id"]: e["order"] for e in events if e["kind"] == "order_won"}
        views, bookings, booked_gig = defaultdict(list), defaultdict(list), defaultdict(list)
        for e in events:
            if e["kind"] == "gig_viewed":
                views[e["driverId"]].append((e["at"], e["gigId"]))
            elif e["kind"] == "gig_booked":
                bookings[e["driverId"]].append(e["at"])
                booked_gig[e["gigId"]].append((e["at"], e["driverId"], e["feeCents"]))
        for o in run.get("offers", []):
            if o["answer"] == "refused" or o["orderId"] not in orders:
                rows.append({"seed": run["seed"], **o})
                continue
            d, at = roster[o["driverId"]], o["at"]
            leg = orders[o["orderId"]]["legs"][0]
            pu, de = leg["pickup"]["placeId"], leg["delivery"]["placeId"]
            day0 = at - at % DAY
            read = any(at <= v <= at + 10 and g == o["gigId"] for v, g in views[o["driverId"]])
            other = [b for b in booked_gig[o["gigId"]] if at <= b[0] <= at + 11 and b[1] != o["driverId"]]
            rows.append({"seed": run["seed"], **o, "hour": at % DAY // HOUR, "day": at // DAY, "read": read, "taken_by_other": bool(other),
                         "home_pu_km": a.crow_km(d["homePlaceId"], pu), "home_de_km": a.crow_km(d["homePlaceId"], de), "km": a.km[(pu, de)],
                         "viewed_today": any(day0 <= v < at for v, _ in views[o["driverId"]]), "booked_today": any(day0 <= b < at for b in bookings[o["driverId"]]),
                         "viewed_before": any(v < at for v, _ in views[o["driverId"]]), "drops": d["drops"], "completed": d["completedGigs"], "rating": d["rating"],
                         "ready_in": (leg["pickup"]["window"]["from"] - at) / HOUR, "last_pickup_in": (orders[o["orderId"]]["lastPickupAt"] - at) / HOUR})
    return pd.DataFrame(rows)


def offers(tag: str) -> None:
    t = offer_table(tag)
    print(t.answer.value_counts(dropna=False))
    if "reason" in t:
        print(t[t.answer == "refused"].reason.str.replace(r"\S*\d\S*", "#", regex=True).value_counts().head(8))
    t = t[t.answer != "refused"].copy()
    print("offers whose gig another driver booked inside the 10 minutes:", t.taken_by_other.astype(bool).sum())
    t = t[~t.taken_by_other.astype(bool)].copy()
    t["yes"] = t.answer == "accepted"
    t["answered"] = t.answer.isin(["accepted", "declined"])
    show = lambda by: print(t.groupby(by).agg(n=("yes", "size"), read=("answered", "mean"), yes=("yes", "mean"), yes_if_read=("yes", lambda s: s[t.loc[s.index, "answered"]].mean())).round(3), "\n")
    for by in (["class"], ["multiple"], ["class", "multiple"], ["arm", "multiple"], ["hour"], ["viewed_today"], ["booked_today"], ["viewed_today", "class"], ["urgent"]):
        show(by)


def shared_table(tag: str) -> pd.DataFrame:
    """One row per pair of cars the desk matched: what the two cars cost and whether they were on time, as one gig or (control) as two."""
    rows = []
    for run in runs(tag):
        events = run["events"]
        orders = {e["order"]["id"]: e["order"] for e in events if e["kind"] == "order_won"}
        gigs_of = defaultdict(set)
        for gig in run["gigs"]:
            for stop in gig["stops"]:
                gigs_of[stop["orderId"]].add(gig["id"])
        gig = {g["id"]: g for g in run["gigs"]}
        booked, money, refund, warned, delivered, dropped = {}, defaultdict(int), defaultdict(int), set(), {}, defaultdict(int)
        for e in events:
            if e["kind"] == "gig_booked":
                booked.setdefault(e["gigId"], e)
            elif e["kind"] in ("gig_dropped", "no_show"):
                dropped[e["gigId"]] += 1
            elif e["kind"] == "deadline_close":
                warned.add(e["orderId"])
            elif e["kind"] == "delivered":
                delivered[e["orderId"]] = e["at"]
            elif e["kind"] == "ledger":
                line = e["line"]
                if line["kind"] in ("driver_fee", "failed_visit", "release_fee", "waiting"):
                    money[line["gigId"]] += line["cents"]
                elif line["kind"] in ("late_refund", "undelivered_penalty"):
                    refund[line["orderId"]] += line["cents"]
        for pair in run.get("pairs", []):
            p, q = pair["orders"]
            if p not in orders or q not in orders:
                continue
            both = [g for g in gigs_of[p] & gigs_of[q]]
            first = min(both, key=lambda g: gig[g]["postedAt"]) if both else None
            row = {"seed": run["seed"], **pair, "arm": "two gigs" if pair["multiple"] is None else "one gig", "day": pair["at"] // DAY, "hour": pair["at"] % DAY // HOUR,
                   "fees": -sum(money[g] for g in gigs_of[p] | gigs_of[q]) / pair["typicalCents"], "refund": -(refund[p] + refund[q]) / 100,
                   "on_time": sum(o in delivered and delivered[o] <= orders[o]["deadline"] and refund[o] == 0 for o in (p, q)) / 2, "warned": sum(o in warned for o in (p, q)) / 2,
                   "price": (orders[p]["priceCents"] + orders[q]["priceCents"]) / 100, "typical": pair["typicalCents"] / 100}
            if first:
                row.update(booked=first in booked, wait=booked[first]["at"] - gig[first]["postedAt"] if first in booked else None, done=gig[first]["status"] == "done", drops=dropped[first])
            else:
                singles = [min(gigs_of[o], key=lambda g: gig[g]["postedAt"]) for o in (p, q) if gigs_of[o]]
                row.update(booked=all(g in booked for g in singles), wait=max((booked[g]["at"] - gig[g]["postedAt"] for g in singles if g in booked), default=None),
                           done=all(gig[g]["status"] == "done" for g in singles), drops=sum(dropped[g] for g in singles))
            rows.append(row)
    return pd.DataFrame(rows)


def shared(tag: str) -> None:
    t = shared_table(tag)
    t["multiple"] = t.multiple.fillna(0)
    agg = dict(pairs=("fees", "size"), booked=("booked", "mean"), wait_median=("wait", "median"), wait_p90=("wait", lambda s: s.quantile(.9)), done_as_posted=("done", "mean"), drops=("drops", "mean"),
               fees_over_typical=("fees", "mean"), on_time=("on_time", "mean"), warned=("warned", "mean"), refund=("refund", "mean"), typical=("typical", "mean"))
    print("multiple 0 = control: the same two cars as two single gigs")
    print(t.groupby(["kind", "arm", "multiple"]).agg(**agg).round(2).to_string())
    print(t.groupby(["kind", "arm"]).agg(**agg).round(2).to_string())
    print(t.groupby("seed").agg(pairs=("fees", "size"), cars=("fees", lambda s: 2 * len(s))))


def request_table(run: dict) -> pd.DataFrame:
    """One row per price request we quoted: outcome and, when won, its money, with a shared gig's fee split by typical fee."""
    events = run["events"]
    typical = {item["request"]["id"]: item["request"]["referenceFeeCents"] for item in run["reveal"]["requests"]}
    orders = {e["order"]["id"]: e["order"] for e in events if e["kind"] == "order_won"}
    cancelled = {e["orderId"] for e in events if e["kind"] == "order_cancelled"}
    owners = {gig["id"]: list(dict.fromkeys(stop["orderId"] for stop in gig["stops"])) for gig in run["gigs"]}
    money, shared_with = defaultdict(int), {}
    for e in events:
        if e["kind"] == "ledger":
            line = e["line"]
            ids = [line["orderId"]] if line.get("orderId") else owners.get(line.get("gigId"), [])
            total = sum(typical.get(i, 0) for i in ids) or 1
            for i in ids:
                money[(i, "fees" if line["kind"] in ("driver_fee", "failed_visit", "release_fee", "waiting", "fine") else line["kind"])] += line["cents"] * typical.get(i, 0) / total if len(ids) > 1 else line["cents"]
    for gig in run["gigs"]:
        if len(owners[gig["id"]]) > 1 and gig["status"] == "done":
            for i in owners[gig["id"]]:
                shared_with[i] = gig["id"]
    partnered = run.get("partnered", {})
    rows = []
    for item in run["reveal"]["requests"]:
        r, quote = item["request"], item["quote"] or {}
        if not quote:
            continue
        kind, cents = next(iter(quote.items()))
        option = next(o for o in r["options"] if o["kind"] == kind)
        if cents >= 3 * option["listPriceCents"]:
            continue
        i = r["id"]
        won = item["outcome"] == "won" and i not in cancelled
        late = money[(i, "late_refund")] + money[(i, "undelivered_penalty")]
        rows.append({"seed": run["seed"], "id": i, "day": r["arrivedAt"] // DAY, "partner": i in partnered, "multiple": round(cents / option["listPriceCents"], 2),
                     "drawn": partnered.get(i, {}).get("multiple"), "won": won, "typical": r["referenceFeeCents"] / 100, "list": option["listPriceCents"] / 100,
                     "price": cents / 100 if won else 0.0, "fees": -money[(i, "fees")] / 100 if won else 0.0, "refund": -late / 100 if won else 0.0,
                     "margin": (money[(i, "revenue")] + money[(i, "fees")] + late) / 100 if won else 0.0, "in_pair": i in shared_with, "on_time": bool(won and late == 0 and money[(i, "revenue")] > 0)})
    return pd.DataFrame(rows)


def partners(tag: str) -> None:
    t = pd.concat(request_table(run) for run in runs(tag))
    t["quoted_at"] = t.drawn.fillna(0)  # 0: not a partner request, quoted as usual
    agg = lambda d: pd.Series({"requests": len(d), "won": d.won.mean(), "in_pair_if_won": d[d.won].in_pair.mean(), "on_time_if_won": d[d.won].on_time.mean(),
                               "fees_over_typical_if_won": d[d.won].fees.sum() / max(1, d[d.won].typical.sum()), "margin_per_request": d.margin.mean(), "margin_per_win": d[d.won].margin.mean()})
    print("requests whose car could share a gig with a car that waited, by the multiple of list we quoted; and the others")
    print(t.groupby(["partner", "quoted_at"]).apply(agg).round(3).to_string())
    print(t.groupby("seed").apply(lambda d: pd.Series({"quoted": len(d), "partner": d.partner.mean(), "won": d.won.sum(), "in_pair": d[d.won].in_pair.mean()})).round(3))


if __name__ == "__main__":
    {"bookers": bookers, "pairs": pairs, "offers": offers, "shared": shared, "partners": partners}[sys.argv[1]](sys.argv[2])
