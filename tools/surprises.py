"""The week's unannounced events: which day and region each fell on, and what they are worth to the market.

    python -m tools.surprises exact                        # probed weeks (tools/probe_week.py), where every threshold is known: the war day, the outage day and region
    python -m tools.surprises find main-m10 [more tags]    # saved weeks: the same from the dealers' answers alone, as the market weighs them
    python -m tools.surprises money [seeds]                # probed weeks replayed: the euros of each day for our market, for the market before it weighed
                                                           # the events, and for one that is told them at 08:00; how many requests our level takes to follow
    python -m tools.surprises fleet main-m10 [more tags]   # the driver side: the bulk order, the flu day, and each day's bookings

A replay quotes each request of a probed week in the order of the week, at the cost the fleet gave it, and lets the dealer answer by its measured
threshold: it buys the option with the most euros under its threshold. A slower option's threshold is the faster one's minus the dealer's euros for speed."""
from __future__ import annotations

import glob
import json
import math
import os
import sys
from collections import Counter, defaultdict
from typing import Optional

import numpy as np
import pandas as pd

from dispatch import prior
from dispatch.atlas import DAY
from dispatch.books import Books
from dispatch.market import CLOSES, OPENS, OUTAGE, REACH, WAR, WORKDAYS, Market, MarketPolicy
from tools.census import NAMES, flu
from tools.study import ROOT, atlas, runs, table

FOLDER = os.path.join(ROOT, "runs", "bisect")
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
SPEED = {("same_day", "next_day"): 1450, ("next_day", "within_3_days"): 610}  # cents the median dealer gives for the faster option (tools/probe_read.py)
BEFORE = {"surprises": False, "spread": {**prior.SPREAD, "day": 0.125}}  # the market before it weighed the events: its day part's spread was fitted with the events in it
pd.set_option("display.width", 250, "display.max_columns", 40)


def touched(event: str) -> frozenset:
    """The pickup places whose dealers an event reaches: every place in a war, a town and the places within 80 km of it in an outage."""
    a = atlas()
    return frozenset(place for place in a.places if event == "war" or a.crow_km(event, place) <= REACH)


class Costs:
    """The fleet as a market needs it: the map, and what each option cost when the desk quoted it."""

    def __init__(self, asked: Optional[dict] = None):
        self.atlas, self.asked = atlas(), asked or {}

    def cost(self, request, option):
        return self.asked[request["id"]]["cost"][request["options"].index(option)]


class Told(Market):
    """A market that is told each day's event at 08:00: what the best detector could earn."""

    def __init__(self, *args, truth: dict):
        super().__init__(*args)
        self.truth = truth

    def odds(self, day: int) -> dict[str, float]:
        return {event: 1.0 for event in [self.truth.get(day)] if event}


def probed(seed: str) -> tuple[pd.DataFrame, dict]:
    """A probed week: one row per request whose fastest option's threshold is known within 3%."""
    with open(os.path.join(FOLDER, f"week-{seed}.json")) as file:
        week = json.load(file)
    rows = []
    for request_id, bracket in week["brackets"].items():
        request, asked = week["requests"][request_id], week["asked"].get(request_id)
        if asked and "lo" in bracket and "hi" in bracket and bracket["hi"] - bracket["lo"] <= 0.03:
            leg = request["legs"][0]
            rows.append({"seed": seed, "id": request_id, "minute": request["arrivedAt"], "day": request["arrivedAt"] // DAY, "hour": request["arrivedAt"] % DAY / 60, "dealer": request["dealerId"],
                         "from": leg["pickup"]["placeId"], "to": leg["delivery"]["placeId"], "list": request["options"][0]["listPriceCents"], "theta": (bracket["lo"] + bracket["hi"]) / 2,
                         "trust": asked["trust"], "batch": request["batchId"]})
    t = pd.DataFrame(rows).sort_values(["minute", "id"]).reset_index(drop=True)
    t["net"] = t.theta - MarketPolicy().trust * t.trust  # the threshold without the trust we had earned
    return t, week


def exact(t: pd.DataFrame) -> dict:
    """The events of a probed week. A threshold is a pickup part + a delivery part + a day part (medians). The outage is the day and region whose
    cars sit the rules' step above the day's other cars; the war is the lowest day once the outage is taken out."""
    a = atlas()
    regions = defaultdict(list)
    for town in sorted(a.places):
        regions[frozenset(p for p in a.places if a.crow_km(town, p) <= REACH)].append(town)
    working = (t.hour >= 8) & (t.hour < 18)
    event, best, seen = np.zeros(len(t)), None, True
    for turn in range(3):  # the first round's outage is taken out before the parts are fitted again; the second round's must pass the test to stay out
        net = t.net - event
        f, to, d = pd.Series(0.0, index=t["from"].unique()), pd.Series(0.0, index=t["to"].unique()), None
        for _ in range(20):
            d = (net - f.reindex(t["from"]).values - to.reindex(t["to"]).values).groupby(t.day).median()
            f = (net - d.reindex(t.day).values - to.reindex(t["to"]).values).groupby(t["from"]).median()
            to = (net - d.reindex(t.day).values - f.reindex(t["from"]).values).groupby(t["to"]).median()
        flat = (t.net - f.reindex(t["from"]).values - to.reindex(t["to"]).values).values  # what is left for the day and the event
        sd, found = float(np.std(flat - d.reindex(t.day).values - event)), []
        if turn == 2:
            break
        for region, towns in regions.items():
            inside = (t["from"].isin(region) & working).values
            for day in range(WORKDAYS):
                today, there = (t.day == day).values, inside & (t.day == day).values
                if there.sum() >= 3 and (today & ~there).sum() >= 3:
                    taken = flat[today] - OUTAGE * there[today]
                    step = float(np.median(flat[there]) - np.median(flat[today & ~there]))
                    found.append({"day": day, "towns": towns, "region": sorted(region), "n": int(there.sum()), "step": step, "z": step / (sd * math.sqrt(1 / there.sum() + 1 / (today & ~there).sum())),
                                  "gain": float(np.abs(flat[today] - np.median(flat[today])).sum() - np.abs(taken - np.median(taken)).sum())})
        best = max(found, key=lambda item: item["gain"])
        seen = turn == 0 or (best["z"] >= 4 and 0.15 <= best["step"] <= 0.40)  # else its region asked for too few cars that day to tell
        event = OUTAGE * (t["from"].isin(best["region"]) & working & (t.day == best["day"])).values * seen
    days = d - d.median()
    calm = days.drop(best["day"]) if seen else days
    war = int(calm.idxmin())
    return {"outage": best if seen else None, "best": best, "war": war, "days": days.round(3).tolist(), "war_step": float(calm[war] - calm.drop(war).median()),
            "next_lowest": float(calm.drop(war).min() - calm.drop(war).median()), "sd": sd, "events": {war: "war", **({best["day"]: best["towns"][0]} if seen else {})}}


def speed(seed: str) -> dict:
    """Cents each dealer of the seed gives for the faster of two options, from its bisected Monday (tools/probe.py)."""
    path, gaps = os.path.join(FOLDER, f"{seed}.json"), defaultdict(list)
    if os.path.exists(path):
        with open(path) as file:
            monday = json.load(file)
        for request_id, request in monday["requests"].items():
            cents = {}
            for option in request["options"]:
                b = monday["brackets"][request_id][option["kind"]]
                if "lo" in b and "hi" in b and b["hi"] - b["lo"] <= 0.03:
                    cents[option["kind"]] = option["listPriceCents"] * math.exp((b["lo"] + b["hi"]) / 2)
            for fast, slow in SPEED:
                if fast in cents and slow in cents:
                    gaps[(request["dealerId"], fast, slow)].append(cents[fast] - cents[slow])
    return {key: float(np.median(values)) for key, values in gaps.items() if len(values) >= 2}


def replay(t: pd.DataFrame, week: dict, make) -> pd.DataFrame:
    """The week's known requests through the market that `make(books, fleet)` gives: a row per request with our quote, the dealer's answer and the margin over the fleet's cost."""
    books, fleet, euros_for_speed = Books([]), Costs(week["asked"]), speed(week["seed"])
    market, known, rows, levels = make(books, fleet), t.set_index("id"), [], {}
    turns = sorted([(week["requests"][i]["arrivedAt"], 1, i) for i in known.index] + [(week["requests"][i]["respondBy"], 0, i) for i in known.index])
    for minute, asks, request_id in turns:  # at one minute the answers come before the new requests
        request, asked = week["requests"][request_id], week["asked"][request_id]
        books.on_time[request["dealerId"]] = asked["trust"]
        if asks:
            books.requests[request_id] = request
            books.quotes[request_id] = market.quote(request)
            levels[request_id] = market.level(request, request["options"][0])[0] + sum(chance * shift for chance, shift in market.mix(request))
            continue
        prices, options, surplus = books.quotes[request_id], request["options"], {}
        cents = options[0]["listPriceCents"] * math.exp(known.theta[request_id])
        for index, option in enumerate(options):
            if index:
                step = (options[index - 1]["kind"], option["kind"])
                cents -= euros_for_speed.get((request["dealerId"], *step), SPEED[step])
            if option["kind"] in prices:
                surplus[option["kind"]] = cents - prices[option["kind"]]
        bought = max(surplus, key=surplus.get)
        won, first = bought if surplus[bought] >= 0 else None, options[0]
        cost = asked["cost"][[o["kind"] for o in options].index(won)] if won else 0
        rows.append({"id": request_id, "day": request["arrivedAt"] // DAY, "minute": request["arrivedAt"], "from": request["legs"][0]["pickup"]["placeId"], "theta": known.theta[request_id],
                     "level": levels[request_id], "priced": max(prices.values()) < first["listPriceCents"] * 3.9, "won": won, "margin": (prices[won] - cost) / 100 if won else 0.0})
        market.learn(request_id, won)
    return pd.DataFrame(rows)


def follows(ours: pd.DataFrame, told: pd.DataFrame, reached: pd.Series) -> tuple[int, float, float, float]:
    """On the requests an event reached, in order: how many pass until the level we price against is within 5% of the told market's (the median of
    the next five), at what hour, how far off the first one was, and the euros the told market earned more on those before."""
    both = ours[reached.values].merge(told[reached.values][["id", "level", "margin"]], on="id", suffixes=("", "_told")).sort_values("minute").reset_index(drop=True)
    gap = (both.level - both.level_told).abs()
    near = [k for k in range(len(gap)) if gap[k:k + 5].median() <= 0.05]
    k = near[0] if near else len(gap)
    cut = both.minute[k] if k < len(both) else 10 ** 9
    return k, (cut % DAY) / 60 if k < len(both) else float("nan"), float(gap[:3].mean()), float((both.margin_told - both.margin)[both.minute < cut].sum())


def money(seeds: list[str]) -> None:
    totals, speeds = [], []
    for seed in seeds:
        t, week = probed(seed)
        truth = exact(t)
        events = truth["events"]
        makes = {"before": lambda books, fleet: Market(MarketPolicy(**BEFORE), books, fleet), "ours": lambda books, fleet: Market(MarketPolicy(), books, fleet),
                 "told": lambda books, fleet: Told(MarketPolicy(), books, fleet, truth=events)}
        plays = {name: replay(t, week, make) for name, make in makes.items()}
        by_day = pd.DataFrame({name: play.groupby("day").margin.sum() for name, play in plays.items()}).round(0)
        won = pd.DataFrame({name: play.groupby("day").won.count() for name, play in plays.items()})
        real = sum((week["quotes"][i][k] - week["asked"][i]["cost"][[o["kind"] for o in week["requests"][i]["options"]].index(k)]) / 100
                   for i, k in week["outcomes"].items() if k and i in week["asked"] and week["requests"][i]["arrivedAt"] < WORKDAYS * DAY)
        names = {day: ("war" if event == "war" else f"outage {event}") for day, event in events.items()}
        print(f"\n== {seed}: {len(t)} requests; the desk's own week at the fleet's cost €{real:,.0f}; a replay, euros over the fleet's cost and orders by day")
        print(by_day.assign(orders_before=won.before, orders_ours=won.ours, orders_told=won.told, event=[names.get(d, "") for d in by_day.index]).rename(index=dict(enumerate(DAYS))).to_string())
        row = {"seed": seed, **{name: play.margin.sum() for name, play in plays.items()}}
        before, ours, told = plays["before"], plays["ours"], plays["told"]
        working = (t.minute % DAY >= OPENS) & (t.minute % DAY < CLOSES)
        for day, event in events.items():
            kind = "war" if event == "war" else "outage"
            reached = (t.day == day) & working & t["from"].isin(touched(event))
            calm = replay(t.assign(theta=t.theta - (WAR if event == "war" else OUTAGE) * reached), week, makes["ours"])  # the same week without this event
            on = lambda play, d=day: round(play[play.day == d].margin.sum())
            there = reached[(t.day == day).values].values
            line = {"seed": seed, "event": f"{kind} {DAYS[day]}" + ("" if kind == "war" else f" {event}"), "requests reached": int(reached.sum())}
            for name, play in (("before", before), ("ours", ours)):
                k, hour, first, lost = follows(play, told, reached)
                off = (play.level - told.level)[(play.day == day).values]  # how far the level is from the told market's over the day: where the event reached, and elsewhere
                line.update({f"{name}: requests until within 5%": k, f"{name}: at hour": round(hour, 1), f"{name}: median off where reached": round(off[there].median(), 3),
                             f"{name}: elsewhere": round(off[~there].median(), 3)})
            line.update({"that day: before": on(before), "ours": on(ours), "told": on(told), "orders before": int(before[before.day == day].won.count()), "orders ours": int(ours[ours.day == day].won.count()),
                         "without the event: ours": on(calm), "orders": int(calm[calm.day == day].won.count()),
                         "next day: before": on(before, day + 1), "ours ": on(ours, day + 1), "told ": on(told, day + 1)})
            speeds.append(line)
            row.update({f"{kind} {name}": play[play.day == day].margin.sum() for name, play in plays.items()})
            row[f"{kind} gives"] = on(ours) - on(calm) + on(ours, day + 1) - on(calm, day + 1)
        totals.append(row)
    totals = pd.DataFrame(totals).set_index("seed").round(0)
    print("\n== a week, euros over the fleet's cost\n" + totals.to_string())
    print("mean   " + totals.mean().round(0).to_string().replace("\n", "   "))
    for name in ("ours", "told"):
        more = totals[name] - totals.before
        print(f"{name} - before: mean €{more.mean():,.0f} a week ({more.sum() / totals.before.sum():+.1%}), standard error {more.std() / len(more) ** 0.5:,.0f}, {int((more > 0).sum())} of {len(more)} weeks up, by week {more.astype(int).tolist()}")
    speeds = pd.DataFrame(speeds)
    print("\n== how fast the level follows an event (requests the event reached, in order of arrival), and the day's euros\n" + speeds.to_string(index=False))
    numbers = speeds.select_dtypes("number")
    for kind in ("war", "outage"):
        print(f"median {kind} day: " + numbers[speeds.event.str.startswith(kind).values].median().round(2).to_string().replace("\n", "   "))


def show_exact(seeds: list[str]) -> None:
    for seed in seeds:
        e = exact(probed(seed)[0])
        o, b = e["outage"], e["best"]
        outage = (f"outage {DAYS[o['day']]} around {'/'.join(o['towns'])} [{' '.join(o['region'])}]: {o['n']} requests {o['step']:+.3f} over the day's others (z {o['z']:.1f})" if o else
                  f"no outage seen (best: {DAYS[b['day']]} {b['towns'][0]}, {b['n']} requests {b['step']:+.3f}, z {b['z']:.1f})")
        print(f"{seed}  war {DAYS[e['war']]} ({e['war_step']:+.3f} against the calm days; the next lowest day {e['next_lowest']:+.3f})   {outage}   days {e['days']}   sd left {e['sd']:.3f}")


def believed(run: dict) -> tuple[Market, list[dict]]:
    """A saved week through the weighing market, as a restart would replay it: the market at the week's end, and what it believed of each day after each answer."""
    books = Books(run["roster"])
    market, trail = Market(MarketPolicy(), books, Costs()), []
    for event in run["events"]:
        books.observe(event)
        kind = event["kind"]
        if kind == "price_request":
            books.quotes[event["request"]["id"]] = run["quotes"].get(event["request"]["id"]) or {}
        elif kind in ("order_won", "order_lost"):
            request_id, won = (event["order"]["id"], event["order"]["option"]) if kind == "order_won" else (event["requestId"], None)
            if books.quotes.get(request_id):
                market.learn(request_id, won)
                day = books.requests[request_id]["arrivedAt"] // DAY
                if day < WORKDAYS:
                    trail.append({"day": day, "at": event["at"], "odds": market.odds(day)})
    return market, trail


def find(tags: list[str]) -> None:
    truths, right = {}, Counter()
    for tag in tags:
        for run in runs(tag):
            seed = run["seed"]
            market, trail = believed(run)
            odds = [market.odds(day) for day in range(WORKDAYS)]
            war = max(range(WORKDAYS), key=lambda day: odds[day]["war"])
            day, town = max(((d, town) for d in range(WORKDAYS) for town in odds[d] if town != "war"), key=lambda item: odds[item[0]][item[1]])
            region = market.regions[town]
            there = sum(1 for d in trail if d["day"] == day)
            shares = {d: sum(chance for event, chance in odds[d].items() if event != "war") for d in range(WORKDAYS)}
            line = (f"{tag} {seed}  war {DAYS[war]} (chance {odds[war]['war']:.2f}; log-likelihood against a calm day {market.heard.get(war, {}).get('war', 0):+.0f}, the next day's "
                    f"{sorted((market.heard.get(d, {}).get('war', 0) for d in range(WORKDAYS)), reverse=True)[1]:+.0f})   outage {DAYS[day]} (chance {shares[day]:.2f}) around {town} "
                    f"[{' '.join(sorted(region))}] ({odds[day][town]:.2f}; {market.heard.get(day, {}).get(town, 0):+.0f})")
            if os.path.exists(os.path.join(FOLDER, f"week-{seed}.json")):
                truth = truths[seed] = truths.get(seed) or exact(probed(seed)[0])
                o = truth["outage"]
                def sure(d: int, war: bool) -> int:
                    """The answers of the day after which the chance of a war (or of an outage, wherever) stays at 0.9 or more."""
                    steps = [s for s in trail if s["day"] == d]
                    doubts = [i for i, step in enumerate(steps) if sum(chance for event, chance in step["odds"].items() if (event == "war") == war) < 0.9]
                    return (doubts[-1] + 2 if doubts else 1) if not doubts or doubts[-1] + 1 < len(steps) else -1

                right["war"] += war == truth["war"]
                right["weeks"] += 1
                line += f"   | measured: war {DAYS[truth['war']]} {'RIGHT' if war == truth['war'] else 'WRONG'}, sure (chance 0.9 from then on) after {sure(truth['war'], True)} answers of the day"
                if o:
                    right["outage"] += day == o["day"]
                    right["outages"] += 1
                    line += (f"; outage {DAYS[o['day']]} {o['towns'][0]} {'RIGHT' if day == o['day'] else 'WRONG'}, sure after {sure(o['day'], False)} answers, "
                             f"{len(set(region) & set(o['region']))} of {len(set(region) | set(o['region']))} places shared")
                else:
                    line += "; outage reached too few requests to measure"
            print(line)
    if right:
        print(f"== against the measured weeks: war day right in {right['war']} of {right['weeks']}, outage day right in {right['outage']} of {right['outages']}")


def fleet(tags: list[str]) -> None:
    """The driver side of the week, for the fleet: the bulk order, and bookings by the day an order was won."""
    for tag in tags:
        t = table(tag)
        t = t[t.day < WORKDAYS]
        t["quoted"] = t[[c for c in t.columns if c.startswith("m_")]].min(axis=1) < 3.9
        t["won"] = t.outcome == "won"
        t["wait"] = (t.first_booked_at - t.won_at) / 60 if "first_booked_at" in t else np.nan
        sizes = t.groupby(["seed", "batch"]).id.transform("size").where(t.batch.notna(), 1)
        bulk = t[sizes >= 30]
        rows = []
        for (seed, batch), b in bulk.groupby(["seed", "batch"]):
            rest = t[(t.seed == seed) & ~t.index.isin(b.index) & t.won]
            w = b[b.won]
            rows.append({"seed": seed, "when": f"{DAYS[b.day.iloc[0]]} {int(b.hour.iloc[0]):02d}:{int(b.hour.iloc[0] % 1 * 60):02d}", "yard": b.pu.mode()[0], "dealer": b.dealer.mode()[0], "cars": len(b), "quoted": int(b.quoted.sum()),
                         "won": len(w), "on time": int(w.on_time.sum()), "margin €": round(w.margin.sum() / 100), "€/order": round(w.margin.mean() / 100, 1) if len(w) else np.nan,
                         "price x list": round((w.price / w.list_won).mean(), 2) if len(w) else np.nan, "fee x typical": round((w.booked_fee / w.typical).mean(), 2) if len(w) else np.nan,
                         "median h to a driver": round(w.wait.median(), 1) if len(w) else np.nan, "rest of week: on time": round(rest.on_time.mean(), 3), "€/order ": round(rest.margin.mean() / 100, 1)})
        print(f"\n== {tag}: the bulk order (30 or more requests in one batch from one yard)\n" + pd.DataFrame(rows).to_string(index=False))
        won = t[t.won]
        by_day = won.groupby(["seed", "day"]).agg(orders=("id", "size"), on_time=("on_time", "mean"), wait=("wait", "median"), in_hour=("wait", lambda w: (w <= 1).mean()), margin=("margin", lambda m: m.mean() / 100))
        print(f"\n== {tag}: orders by the day they were won (on time share; median hours to the first booking; share booked within the hour; € per order)")
        for column in ("orders", "on_time", "wait", "in_hour", "margin"):
            print(f"  {column}\n" + by_day[column].unstack("day").rename(columns=dict(enumerate(DAYS))).round(2).to_string())
        rows = []
        for seed in sorted(won.seed.unique()):  # the flu day, where the count of drivers (tools/census.py) saw one: that day against the week's other four
            day, missing = flu(seed)
            if day is not None and day < WORKDAYS:
                mine = won[won.seed == seed]
                that, rest, booked = mine[mine.day == day], mine[mine.day != day], mine.first_booked_at // DAY
                rows.append({"seed": seed, "flu day": NAMES[day], "regular drivers at home": f"{missing:.0%}", "orders won": len(that), "a day of the rest": round(len(rest) / 4),
                             "bookings an hour (08-20)": round((booked == day).sum() / 12, 1), "rest ": round(((booked < WORKDAYS) & (booked != day)).sum() / 48, 1),
                             "median h to a driver": round(that.wait.median(), 2), "rest  ": round(rest.wait.median(), 2), "within the hour": round((that.wait <= 1).mean(), 2),
                             "rest   ": round((rest.wait <= 1).mean(), 2), "late": round(1 - that.on_time.mean(), 3), "rest    ": round(1 - rest.on_time.mean(), 3)})
        if rows:
            print(f"\n== {tag}: the flu day, where the count of drivers saw one on a working day\n" + pd.DataFrame(rows).to_string(index=False))


def seeds_probed() -> list[str]:
    return sorted(os.path.basename(path)[5:-5] for path in glob.glob(os.path.join(FOLDER, "week-*.json")))


if __name__ == "__main__":
    command, rest = sys.argv[1], sys.argv[2:]
    {"exact": lambda: show_exact(rest or seeds_probed()), "money": lambda: money(rest or seeds_probed()), "find": lambda: find(rest), "fleet": lambda: fleet(rest)}[command]()
