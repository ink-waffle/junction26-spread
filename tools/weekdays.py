"""Where in the week a variant wins its orders (research/skeptic): orders won per weekday, the share sold on the request's fastest option
(of orders whose request had more than one), and the share of each weekday's orders that ended late. Against a baseline, on the same weeks
and strides, as tools/ablations.py pairs them. Prints Markdown.

    python -m tools.weekdays skeptic-base skeptic-cal skeptic-calnw ...     # each name stands for the tags <name>-s14, <name>-s13, ...
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys
from multiprocessing import Pool

import numpy as np

from tools.study import ROOT

DAY, DAYS = 24 * 60, 5


def extract(path: str) -> dict:
    """Per weekday of the win: orders, those with a choice of options, those sold on the fastest, those that paid a refund, euros of price."""
    brief = path[:-8] + ".weekdays.json"
    if os.path.exists(brief):
        with open(brief) as file:
            return json.load(file)
    try:
        with gzip.open(path, "rt") as file:
            run = json.load(file)
    except (EOFError, OSError, ValueError):  # a week that is being written now
        return {}
    requests = {e["request"]["id"]: e["request"] for e in run["events"] if e["kind"] == "price_request"}
    late = {e["line"]["orderId"] for e in run["events"] if e["kind"] == "ledger" and e["line"]["kind"] in ("late_refund", "undelivered_penalty")}
    out = {key: [0] * DAYS for key in ("won", "choice", "fastest", "late", "euros")}
    for event in run["events"]:
        if event["kind"] == "order_won" and event["at"] // DAY < DAYS:
            order, day = event["order"], event["at"] // DAY
            options = requests[order["id"]]["options"]
            out["won"][day] += 1
            out["choice"][day] += len(options) > 1
            out["fastest"][day] += len(options) > 1 and order["option"] == options[0]["kind"]
            out["late"][day] += order["id"] in late
            out["euros"][day] += order["priceCents"] / 100
    out["seed"] = run["seed"]
    with open(brief, "w") as file:
        json.dump(out, file)
    return out


def weeks(name: str) -> dict[str, dict[str, dict]]:
    """seed -> stride -> that sample's extract."""
    paths = sorted(glob.glob(os.path.join(ROOT, "runs", f"{name}-s[0-9]*", "*.json.gz")))
    with Pool(8) as pool:
        extracts = pool.map(extract, paths)
    out: dict[str, dict[str, dict]] = {}
    for path, sample in zip(paths, extracts):
        if sample:
            out.setdefault(sample["seed"], {})[os.path.basename(os.path.dirname(path)).rsplit("-s", 1)[1]] = sample
    return out


def measures(samples: list[dict]) -> np.ndarray:
    """Mean over a week's samples: orders by weekday (5), Monday's and the week's share on the fastest option, Monday's and the week's late share, Monday's euros."""
    rows = []
    for s in samples:
        share = lambda a, b: 100 * sum(a) / max(1, sum(b))
        rows.append([*s["won"], share(s["fastest"][:1], s["choice"][:1]), share(s["fastest"], s["choice"]), share(s["late"][:1], s["won"][:1]), share(s["late"], s["won"]), s["euros"][0]])
    return np.mean(rows, axis=0)


def main() -> None:
    names = sys.argv[1:]
    base = weeks(names[0])
    print("| Variant | weeks × samples | orders won Mon / Tue / Wed / Thu / Fri | Monday's orders against the baseline (se) | fastest option, Monday / week | against the baseline, week (se) | late, Monday's orders / week | Monday's sales in euros against the baseline (se) |")
    print("|---|---|---|---|---|---|---|---|")
    for name in names:
        other = base if name == names[0] else weeks(name)
        rows, diffs, count = [], [], 0
        for seed in sorted(set(base) & set(other)):
            strides = sorted(set(base[seed]) & set(other[seed]))
            if strides:
                a, b = measures([base[seed][s] for s in strides]), measures([other[seed][s] for s in strides])
                rows.append(b)
                diffs.append(b - a)
                count += len(strides)
        if not rows:
            continue
        m, d = np.mean(rows, axis=0), np.array(diffs)
        se = d.std(axis=0, ddof=1) / np.sqrt(len(d)) if len(d) > 1 else d[0] * 0
        print(f"| `{name}` | {len(rows)}×{count // len(rows)} | {' / '.join(f'{x:.0f}' for x in m[:5])} | {d[:, 0].mean():+.1f} ({se[0]:.1f}) | {m[5]:.0f}% / {m[6]:.0f}% | {d[:, 6].mean():+.1f} ({se[6]:.1f}) | "
              f"{m[7]:.1f}% / {m[8]:.1f}% | {d[:, 9].mean():+,.0f} ({se[9]:,.0f}) |")


if __name__ == "__main__":
    main()
