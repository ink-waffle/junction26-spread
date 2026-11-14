"""Reads what tools/probe.py measured (runs/bisect/): how thresholds spread, what speed is worth, how a dealer chooses, what Monday does to Tuesday.

    python -m tools.probe_read
"""
from __future__ import annotations

import glob
import json
import math
import os

import numpy as np
import pandas as pd

from tools.probe import FOLDER
from tools.study import atlas

pd.set_option("display.width", 250, "display.max_columns", 60)
NARROW = 0.03  # a threshold counts as known when its bracket is this narrow (log)


def thresholds() -> tuple[pd.DataFrame, list[dict]]:
    """One row per option of every probed Monday request, and the probed worlds."""
    a, rows, worlds = atlas(), [], []
    for path in sorted(glob.glob(os.path.join(FOLDER, "halal-*.json"))):
        with open(path) as file:
            world = json.load(file)
        worlds.append(world)
        for request_id, request in world["requests"].items():
            leg = request["legs"][0]
            ends = (leg["pickup"]["placeId"], leg["delivery"]["placeId"])
            for index, option in enumerate(request["options"]):
                b = world["brackets"][request_id][option["kind"]]
                rows.append({"seed": world["seed"], "id": request_id, "dealer": request["dealerId"], "lane": ">".join(ends), "to": ends[1], "km": a.km[ends], "hour": request["arrivedAt"] // 60,
                             "kind": option["kind"], "index": index, "list": option["listPriceCents"] / 100, "lo": b.get("lo", np.nan), "hi": b.get("hi", np.nan)})
    t = pd.DataFrame(rows)
    t["log"], t["known"] = (t.lo + t.hi) / 2, (t.hi - t.lo) <= NARROW
    t["euros"] = t.list * np.exp(t.log)
    return t, worlds


def inside(t: pd.DataFrame, keys: list[str], column: str) -> tuple[float, int]:
    """The sd of a column around the mean of its group, from groups of two or more (n - 1), and how many rows that used."""
    t = t.dropna(subset=[column])
    group = t.groupby(keys)[column]
    size, freedom = group.transform("size"), (group.size() - 1).clip(lower=0).sum()
    return math.sqrt((((t[column] - group.transform("mean"))[size > 1]) ** 2).sum() / max(1, freedom)), int((size > 1).sum())


def spreads(t: pd.DataFrame) -> None:
    first = t[t.known & (t["index"] == 0)]
    print(f"\nlog threshold of a request's fastest option: {len(first)} known; sd over everything {first.log.std():.3f}")
    for name, keys in [("one world's Monday", ["seed"]), ("and one delivery place", ["seed", "to"]), ("and one lane", ["seed", "lane"]), ("and one dealer", ["seed", "lane", "dealer"]),
                       ("and the same hour", ["seed", "lane", "dealer", "hour"])]:
        sd, n = inside(first, keys, "log")
        print(f"  inside {name:<24} sd {sd:.3f}   slope of the logistic {math.pi / (sd * math.sqrt(3)):5.1f}   ({n} requests)")
    levels = first.groupby("seed").log.mean()
    print(f"  Monday level by world: mean {levels.mean():.3f} (x{math.exp(levels.mean()):.2f} list), sd {levels.std():.3f}; the three lowest {levels.nsmallest(3).round(2).tolist()} (price-war Mondays)")
    relative = first.assign(rel=first.log - first.groupby("seed").log.transform("mean"))
    for column in ("to", "lane", "dealer"):  # what the other worlds know about a world: their mean for the same place, lane or dealer
        guess = np.zeros(len(relative))
        for seed in relative.seed.unique():
            others, here = relative[relative.seed != seed].groupby(column).rel.agg(["sum", "size"]), (relative.seed == seed).values
            guess[here] = (others["sum"] / (others["size"] + 2)).reindex(relative[column][here]).fillna(0).values
        print(f"  other worlds' {column:<7} predicts a world's: r = {np.corrcoef(guess, relative.rel)[0, 1]:.2f}, sd left {(relative.rel - guess).std():.3f} of {relative.rel.std():.3f}")


def speed(t: pd.DataFrame) -> None:
    wide = t[t.known].pivot_table(index=["seed", "id", "dealer"], columns="kind", values="euros").reset_index()
    print("\nwhat speed is worth: threshold of an option minus that of the next slower one, euros")
    for name, fast, slow in [("same day over next day", "same_day", "next_day"), ("next day over within 3 days", "next_day", "within_3_days")]:
        gap = wide.assign(gap=wide[fast] - wide[slow]).dropna(subset=["gap"])
        dealers = gap.groupby(["seed", "dealer"]).gap.agg(["median", "size", "std"]).query("size >= 3")
        table = dealers["median"].unstack(0)
        other = pd.concat([table.drop(columns=seed).mean(axis=1).rename(seed) for seed in table.columns], axis=1)
        both = table.notna() & other.notna()
        print(f"  {name}: {len(gap)} requests, median {gap.gap.median():.1f}, quartiles {gap.gap.quantile(.25):.1f}-{gap.gap.quantile(.75):.1f}, 5%/95% {gap.gap.quantile(.05):.1f}/{gap.gap.quantile(.95):.1f}; "
              f"sd inside one world and dealer {inside(gap, ['seed', 'dealer'], 'gap')[0]:.2f}; dealers whose requests agree within a euro {(dealers['std'] < 1).mean():.1%}; "
              f"a dealer's value against its mean in other worlds r = {np.corrcoef(table.values[both.values], other.values[both.values])[0, 1]:.2f}")
    never = t[t.lo.isna()]
    print(f"  never bought down to half the list price: {len(never)} options, {(never['index'] > 0).mean():.0%} of them slower options; the dealers: {never.groupby(['seed', 'dealer']).size().nlargest(4).to_dict()}")


def menus(worlds: list[dict]) -> None:
    rows = []
    for world in worlds:
        for menu in world.get("menus", []):
            for offer in menu:
                request = world["requests"][offer["id"]]
                surplus = {o["kind"]: o["listPriceCents"] * math.exp(sum(world["brackets"][offer["id"]][o["kind"]][side] for side in ("lo", "hi")) / 2) - offer["prices"][o["kind"]]
                           for o in request["options"] if o["kind"] in offer["prices"]}
                rows.append({"bought": offer["bought"], "most": max(surplus, key=surplus.get), "margin": abs(np.subtract(*surplus.values())) / request["options"][0]["listPriceCents"]})
    m = pd.DataFrame(rows)
    if len(m):
        print(f"\nmenus of two options, each under its own threshold: {len(m)}; none bought {m.bought.isna().mean():.1%}; bought the one with the largest threshold minus price: {(m.bought == m.most).mean():.1%}"
              f" ({(m.bought == m.most)[m.margin > 0.01].mean():.1%} when the two differ by more than 1% of the list price)")


def tuesday() -> None:
    rows = []
    for path in sorted(glob.glob(os.path.join(FOLDER, "tuesday-desk-*.json"))):
        other = path.replace("tuesday-desk-", "tuesday-none-")
        if os.path.exists(other):
            with open(path) as file, open(other) as second:
                desk, none = json.load(file), json.load(second)
            for request_id, request in desk["requests"].items():
                a, b = desk["brackets"].get(request_id, {}), none["brackets"].get(request_id, {})
                if request["arrivedAt"] >= 1440 and {"lo", "hi"} <= set(a) and {"lo", "hi"} <= set(b) and max(a["hi"] - a["lo"], b["hi"] - b["lo"]) <= 0.02:
                    monday = desk["monday"].get(request["dealerId"], {"requests": 0, "won": 0})
                    rows.append({"moved": (a["lo"] + a["hi"] - b["lo"] - b["hi"]) / 2, "trust": desk["trust"].get(request_id, 0), "share": monday["won"] / max(1, monday["requests"])})
    t = pd.DataFrame(rows)
    if len(t):
        w = np.linalg.lstsq(np.column_stack([np.ones(len(t)), t.trust, t.share]), t.moved.values, rcond=None)[0]
        print(f"\nTuesday after a Monday with our desk against a Monday of declines: {len(t)} requests; log threshold moved by {w[0]:+.4f} {w[1]:+.4f} x the dealer's trust count {w[2]:+.3f} x the share of its Monday requests we won")
        print("  median by trust count:", t.groupby(pd.cut(t.trust, [-1, 0, 2, 5, 10, 15, 25])).moved.median().round(3).to_dict())


def main() -> None:
    t, worlds = thresholds()
    print(f"{len(worlds)} worlds, {len(t)} options of {t[['seed', 'id']].drop_duplicates().shape[0]} Monday requests; threshold known within {NARROW:.0%}: {t.known.mean():.1%} (median bracket {(t.hi - t.lo)[t.known].median():.4f})")
    spreads(t)
    speed(t)
    menus(worlds)
    tuesday()


if __name__ == "__main__":
    main()
