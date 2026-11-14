"""The dealer side against weeks it was not fitted on (research/skeptic): how well the market foretells the dealers' answers of saved weeks
with each part of the level taken out. No practice world is played: each week is replayed through the learner, as tools/winmodel.py does.

    python -m tools.skeptic_market final-fresh skeptic-base-s14

Prints, per variant, the mean log-likelihood of an answer (x 1000) and its paired difference to the whole market over weeks, with a standard error."""
from __future__ import annotations

import glob
import gzip
import json
import math
import os
import sys
from multiprocessing import Pool
from types import SimpleNamespace

import numpy as np

from dispatch import prior
from dispatch.books import Books
from dispatch.market import Market, MarketPolicy
from tools.study import ROOT, atlas


def spread(*without: str, **changed: float) -> dict:
    return {**{name: sd for name, sd in prior.SPREAD.items() if name not in without}, **changed}


VARIANTS = {
    "the market as it is": {},
    "no place table": {"places": False},
    "no lane part": {"spread": spread("lane")},
    "no pickup-today part": {"spread": spread("from today")},
    "no dealer part": {"spread": spread("dealer")},
    "no lane, pickup-today, dealer": {"spread": spread("lane", "from today", "dealer")},
    "no event weighting": {"surprises": False},
    "no event weighting, day 0.125 (before idea 13)": {"surprises": False, "spread": spread(day=0.125)},
    "no trust": {"trust": 0.0},
    "no place parts at all (world, day, events)": {"spread": spread("lane", "from today", "dealer", "from", "to"), "places": False},
    "world + day only (0.125), no events": {"surprises": False, "places": False, "spread": {"world": prior.SPREAD["world"], "day": 0.125}},
    "one fixed level (no learning)": {"surprises": False, "places": False, "spread": {}},
}


def week(path: str) -> dict[str, float]:
    with gzip.open(path, "rt") as file:
        run = json.load(file)
    out = {}
    for name, overrides in VARIANTS.items():
        books = Books(run["roster"])  # the replay of tools/winmodel.py, with a map so that the events are weighed
        market = Market(MarketPolicy(**overrides), books, SimpleNamespace(atlas=atlas()))
        total, count, chances = 0.0, 0, {}
        for event in run["events"]:
            books.observe(event)
            kind = event["kind"]
            if kind == "price_request":
                request = event["request"]
                prices = books.quotes[request["id"]] = run["quotes"].get(request["id"]) or {}
                if prices:
                    chances[request["id"]] = max(market.chance(request, o, prices[o["kind"]]) for o in request["options"] if o["kind"] in prices)
            elif kind in ("order_won", "order_lost"):
                request_id, won = (event["order"]["id"], event["order"]["option"]) if kind == "order_won" else (event["requestId"], None)
                request, prices = books.requests[request_id], books.quotes.get(request_id)
                if not prices:
                    continue
                option = market.weighed(request, prices, won)
                if prices[option["kind"]] / option["listPriceCents"] < 3.9:  # a real quote, not a decline
                    p = min(1 - 1e-6, max(1e-6, chances[request_id]))
                    total += math.log(p if won else 1 - p)
                    count += 1
                market.learn(request_id, won)
        out[name] = total / max(1, count)
    return out


def main() -> None:
    paths = [path for tag in sys.argv[1:] for path in sorted(glob.glob(os.path.join(ROOT, "runs", tag, "*.json.gz")))]
    with Pool(8) as pool:
        scores = pool.map(week, paths)
    base = np.array([s["the market as it is"] for s in scores])
    print(f"{len(paths)} weeks of {', '.join(sys.argv[1:])}; log-likelihood of an answer x 1000")
    print(f"{'variant':<50} {'mean':>8} {'against the market':>19} {'se':>6} {'weeks worse':>12}")
    for name in VARIANTS:
        x = np.array([s[name] for s in scores])
        d = (x - base) * 1000
        print(f"{name:<50} {x.mean() * 1000:>8.1f} {d.mean():>19.1f} {d.std(ddof=1) / np.sqrt(len(d)):>6.1f} {int((d < 0).sum()):>9} of {len(d)}")


if __name__ == "__main__":
    main()
