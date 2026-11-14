"""The on-time model against weeks it was not fitted on (research/skeptic). For each sign of fleet.ON_TIME: what the model loses in
log-likelihood on those weeks without it, and the weight those weeks would give it themselves, with a standard error.

    python -m tools.skeptic_fit orch-base-s14 -- final-fresh skeptic-base-s14      # weeks of the fit -- weeks never fitted on

Each week is replayed through the books by tools/fleet_fit.py, so every sign is the one the desk computed in play. The tables are cached in runs/skeptic_fit/."""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

from dispatch.fleet import ON_TIME
from tools.fleet_fit import rows
from tools.study import ROOT

CACHE = os.path.join(ROOT, "runs", "skeptic_fit")
SMALL = ["fee", "level", "slack", "backlog"]  # the signs of the deliberately small model


def week(args: tuple[str, str]) -> list[dict]:
    tag, path = args
    with gzip.open(path, "rt") as file:
        run = json.load(file)
    return rows(run, tag) if run.get("gigs") else []


def table(tag: str) -> pd.DataFrame:
    os.makedirs(CACHE, exist_ok=True)
    cached = os.path.join(CACHE, f"{tag}.pkl")
    if not os.path.exists(cached):
        with Pool(8) as pool:
            parts = pool.map(week, [(tag, path) for path in sorted(glob.glob(os.path.join(ROOT, "runs", tag, "*.json.gz")))])
        pd.DataFrame([row for part in parts for row in part]).to_pickle(cached)
    return pd.read_pickle(cached)


def chance(logit: np.ndarray) -> np.ndarray:
    return np.clip(1 / (1 + np.exp(-logit)), 1e-6, 1 - 1e-6)


def score(logit: np.ndarray, y: np.ndarray) -> float:
    p = chance(logit)
    return float(np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def free(x: np.ndarray, y: np.ndarray, offset: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Logistic weights for the columns of x with `offset` held, and their standard errors."""
    w = np.zeros(x.shape[1])
    for _ in range(60):
        p = chance(offset + x @ w)
        hessian = (x * (p * (1 - p))[:, None]).T @ x + 1e-6 * np.eye(len(w))
        w += np.linalg.solve(hessian, x.T @ (y - p))
    return w, np.sqrt(np.diag(np.linalg.inv(hessian)))


def by_seed(t: pd.DataFrame, x: np.ndarray, y: np.ndarray, offset: np.ndarray, column: int = 1) -> float:
    """The standard error of a weight over weeks: the weight refitted with each week left out (jackknife)."""
    seeds = t.seed.values
    names = sorted(set(seeds))
    ws = np.array([free(x[seeds != s], y[seeds != s], offset[seeds != s])[0][column] for s in names])
    return float(np.sqrt((len(names) - 1) / len(names) * ((ws - ws.mean()) ** 2).sum()))


def report(name: str, t: pd.DataFrame) -> None:
    won, looks = t[t.look == 0], t[t.look == 1]
    y, ones = won.on_time.values, np.ones((len(won), 1))
    logit = won[list(ON_TIME)].values @ np.array(list(ON_TIME.values()))
    level = free(ones, y, logit)[0][0]
    print(f"\n== {name}: {len(won)} orders of {won.seed.nunique()} weeks, {1 - y.mean():.1%} late; the model says {1 - chance(logit).mean():.1%}")
    print(f"log-likelihood as baked {score(logit, y):.4f}, with its intercept free ({level:+.2f}) {score(logit + level, y):.4f}, intercept alone {score(np.full(len(y), np.log(y.mean() / (1 - y.mean()))), y):.4f}")
    print(f"{'sign':<17} {'baked':>6} {'these weeks say':>16} {'se (weeks)':>10} {'z':>6} {'loss without it':>16}")
    for sign, weight in ON_TIME.items():
        if sign in ("one", "waited"):
            continue
        rest = logit - weight * won[sign].values
        x = np.column_stack([np.ones(len(won)), won[sign].values])
        if x[:, 1].std() == 0:
            print(f"{sign:<17} {weight:>6.2f} {'(constant here)':>16}")
            continue
        w, _ = free(x, y, rest)
        se = by_seed(won, x, y, rest)
        without = score(rest + free(ones, y, rest)[0][0], y)
        print(f"{sign:<17} {weight:>6.2f} {w[1]:>16.2f} {se:>10.2f} {w[1] / se:>6.1f} {score(logit + level, y) - without:>16.4f}")
    if len(looks):  # an hour waited is seen only on the later looks at waiting cars
        yl = looks.on_time.values
        rest = looks[[s for s in ON_TIME if s != "waited"]].values @ np.array([w for s, w in ON_TIME.items() if s != "waited"])
        x = np.column_stack([np.ones(len(looks)), looks.waited.values])
        if x[:, 1].std() > 0:
            w, _ = free(x, yl, rest)
            print(f"{'waited':<17} {ON_TIME['waited']:>6.2f} {w[1]:>16.2f} {by_seed(looks, x, yl, rest):>10.2f}   ({len(looks)} later looks, {1 - yl.mean():.1%} late in the end; with the intercept free)")
        w0, _ = free(looks[["waited"]].values, yl, rest)
        print(f"{'waited':<17} {ON_TIME['waited']:>6.2f} {w0[0]:>16.2f}   (the intercept held, as tools/fleet_fit.py fits it)")
    small = won[SMALL].values @ np.array([ON_TIME[s] for s in SMALL])
    low, high = -30.0, 30.0
    for _ in range(60):  # the intercept at which the small model's mean chance is the whole model's
        shift = (low + high) / 2
        low, high = (shift, high) if chance(small + shift).mean() < chance(logit).mean() else (low, shift)
    print(f"small model ({', '.join(SMALL)} as baked): one = {shift:.2f} keeps the mean chance; log-likelihood {score(small + shift, y):.4f}, with its intercept free {score(small + free(ones, y, small)[0][0], y):.4f}")
    all_names = [s for s in ON_TIME if s != "waited" and won[s].std() > 0 or s == "one"]
    w, se = free(won[all_names].values, y, np.zeros(len(won)))
    print("all weights refitted freely on these weeks: " + ", ".join(f"{s} {v:.2f}" for s, v in zip(all_names, w)) + f"; log-likelihood {score(won[all_names].values @ w, y):.4f}")


def main() -> None:
    args = sys.argv[1:]
    cut = args.index("--") if "--" in args else len(args)
    fitted, unseen = args[:cut], args[cut + 1:]
    if fitted:
        report("weeks of the fit: " + ", ".join(fitted), pd.concat([table(tag) for tag in fitted]))
    for tag in unseen:
        report("never fitted on: " + tag, table(tag))
    if len(unseen) > 1:
        report("never fitted on, together", pd.concat([table(tag) for tag in unseen]))


if __name__ == "__main__":
    main()
