"""Fits what dealers pay from saved runs, and scores the market's online learner on them.

    python -m tools.winmodel fit explore1 [more tags]     # writes dispatch/prior.py from every seed of the tags
    python -m tools.winmodel cv explore1 [more tags]      # each seed scored with a prior fitted on the other seeds
    python -m tools.winmodel score <tag> [more tags]      # replays the tags through the learner with the prior in dispatch/prior.py

A score is the mean log-likelihood of the dealers' answers under the chance the market gave when it quoted (higher is better)."""
from __future__ import annotations

import math
import os
import pprint
import sys
from typing import Optional

import numpy as np
import pandas as pd

from dispatch import prior as baked
from dispatch.atlas import DAY
from dispatch.books import Books
from dispatch.market import Market, MarketPolicy
from tools.study import runs


def replay(run: dict, places: Optional[dict] = None, policy: Optional[MarketPolicy] = None) -> list[dict]:
    """Replays a saved run through the books and the market, as a restart does: a row per real quote, with the chance the market gave it."""
    books = Books(run["roster"])
    market = Market(policy or MarketPolicy(), books, None, places)
    rows, chances = [], {}
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
            multiple = prices[option["kind"]] / option["listPriceCents"]
            if multiple < 3.9:  # a real quote, not a decline
                leg = request["legs"][0]
                rows.append({"seed": run["seed"], "run": f"{run.get('tag', '')}|{run['seed']}", "id": request_id, "day": request["arrivedAt"] // DAY, "dealer": request["dealerId"],
                             "from": leg["pickup"]["placeId"], "to": leg["delivery"]["placeId"], "skip": request["options"].index(option), "offered": len(prices),
                             "x": math.log(multiple), "won": float(won is not None), "trust": books.on_time[request["dealerId"]], "chance": chances[request_id]})
            market.learn(request_id, won)
    return rows


def logistic(X: np.ndarray, y: np.ndarray, penalty: np.ndarray) -> np.ndarray:
    """Ridge logistic regression by Newton steps."""
    w = np.zeros(X.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-X @ w))
        step = np.linalg.solve((X * (p * (1 - p))[:, None]).T @ X + np.diag(penalty + 1e-9), X.T @ (y - p) - penalty * w)
        w += step
        if np.abs(step).max() < 1e-9:
            break
    return w


def fit(t: pd.DataFrame, requests: int = baked.REQUESTS) -> dict:
    """The prior: the slope, the price of a skipped option and of trust, the spread of worlds, days and dealers, and each place's lasting part."""
    t = t[t.offered == 1]
    groups = {"run-day": t.run + "|" + t.day.astype(str), "from": t["from"], "to": t["to"], "dealer": t.run + "|" + t.dealer}
    columns, names, penalty = [t.x.values, t.skip.values, t.trust.values], [("x", ""), ("skip", ""), ("trust", "")], [0.0] * 3
    for group, key in groups.items():
        for value in sorted(key.unique()):
            columns.append((key == value).values.astype(float))
            names.append((group, value))
            penalty.append(0.0 if group == "run-day" else 4.0)
    w = logistic(np.column_stack(columns), t.won.values, np.array(penalty))
    slope = -w[0]
    effect = {name: value / slope for name, value in zip(names, w)}  # in log price
    part = lambda group: pd.Series({value: e for (g, value), e in effect.items() if g == group})
    days = part("run-day")
    worlds = days.groupby(days.index.str.rsplit("|", n=1).str[0])
    spread = {"world": worlds.mean().std(), "day": (days - worlds.transform("mean")).std(), "dealer": part("dealer").std()}
    return {"SLOPE": round(float(slope), 2), "SPEED": round(float(-effect[("skip", "")]), 4), "TRUST": round(float(effect[("trust", "")]), 4),
            "LEVEL": round(float(worlds.mean().mean()), 3), "REQUESTS": requests,
            "SPREAD": {**baked.SPREAD, **{name: round(float(sd), 3) for name, sd in spread.items()}},
            "PLACES": {end: {place: round(float(e), 3) for place, e in part(end).items()} for end in ("from", "to")}}


def policy_of(prior: dict) -> MarketPolicy:
    return MarketPolicy(slope=prior["SLOPE"], speed=prior["SPEED"], trust=prior["TRUST"], level=prior["LEVEL"], spread=prior["SPREAD"])


def loglik(t: pd.DataFrame) -> float:
    return float(np.mean(t.won * np.log(t.chance) + (1 - t.won) * np.log(1 - t.chance)))


def table(saved: list[dict], places: Optional[dict] = None, policy: Optional[MarketPolicy] = None) -> pd.DataFrame:
    return pd.DataFrame([row for run in saved for row in replay(run, places, policy)])


def main() -> None:
    command, tags = sys.argv[1], sys.argv[2:]
    saved = [{**run, "tag": tag} for tag in tags for run in runs(tag)]
    t = table(saved)
    if command == "score":
        print(t.groupby("seed").apply(loglik).round(4).to_string(), f"\nall {loglik(t):.4f}  quotes {len(t)}")
    elif command == "fit":
        requests = round(float(np.mean([sum(event["kind"] == "price_request" for event in run["events"]) for run in saved])))
        prior = fit(t, requests)
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dispatch", "prior.py"), "w") as file:
            file.write(f'"""What dealers pay, as far as it holds in every world. Generated by `python -m tools.winmodel fit {" ".join(tags)}`: do not edit."""\n')
            for name, value in prior.items():
                file.write(f"{name} = {pprint.pformat(value, width=200, compact=True)}\n")
        print({name: value for name, value in prior.items() if name != "PLACES"})
    elif command == "cv":
        scores = []
        for seed in sorted(t.seed.unique()):
            prior = fit(t[t.seed != seed])
            held = [run for run in saved if run["seed"] == seed]
            learned, bare = table(held, prior["PLACES"], policy_of(prior)), table(held, {}, policy_of(prior))
            fixed = learned.assign(chance=1 / (1 + np.exp(-prior["SLOPE"] * (prior["LEVEL"] - learned.x))))
            scores.append({"seed": seed, "quotes": len(learned), "fixed level": loglik(fixed), "learner": loglik(bare), "learner + places": loglik(learned),
                           "slope": prior["SLOPE"], "speed": prior["SPEED"], "trust": prior["TRUST"], "level": prior["LEVEL"]})
        scores = pd.DataFrame(scores).set_index("seed")
        print(scores.round(4).to_string(), "\nmean", scores.mean().round(4).to_dict())


if __name__ == "__main__":
    main()
