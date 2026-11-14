"""The ablation table of research/skeptic: every variant against a baseline on the same weeks, as paired differences per week
(a week's samples, the same seed at several strides, are averaged first), with standard errors over weeks. Prints Markdown.

    python -m tools.ablations skeptic-base skeptic-nolook skeptic-nopairs ...       # each name stands for the tags <name>-s14, <name>-s13, ...
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys

import numpy as np

from tools.study import ROOT


def weeks(name: str, cache: dict = {}) -> dict[str, list[dict]]:
    """seed -> the summary of each saved sample of this variant."""
    if name not in cache:
        out: dict[str, list[dict]] = {}
        for path in sorted(glob.glob(os.path.join(ROOT, "runs", f"{name}-s[0-9]*", "*.json.gz"))):
            brief = path[:-8] + ".summary.json"  # a small copy: the saved weeks are 15 MB each
            if os.path.exists(brief):
                with open(brief) as file:
                    summary = json.load(file)
            else:
                with gzip.open(path, "rt") as file:
                    summary = json.load(file)["summary"]
                with open(brief, "w") as file:
                    json.dump(summary, file)
            out.setdefault(summary["seed"], []).append(summary)
        cache[name] = out
    return cache[name]


def measures(samples: list[dict]) -> tuple[float, float, float, float]:
    mean = lambda f: float(np.mean([f(s) for s in samples]))
    return mean(lambda s: s["margin"]), mean(lambda s: s["onTime"] * 100), mean(lambda s: s["won"] * (1 - s["onTime"])), mean(lambda s: s["won"])


def main() -> None:
    names = sys.argv[1:]
    base = weeks(names[0])
    flat = [s for samples in base.values() for s in samples]
    print(f"Baseline `{names[0]}`: {len(base)} weeks, {len(flat)} samples: margin EUR {np.mean([s['margin'] for s in flat]):,.0f} a week, on time {np.mean([s['onTime'] for s in flat]):.1%} "
          f"(worst sample {min(s['onTime'] for s in flat):.1%}), {np.mean([s['won'] for s in flat]):.0f} orders, {np.mean([s['won'] * (1 - s['onTime']) for s in flat]):.1f} late a week.\n")
    print("| Without | weeks × samples | margin (se) | on time, points (se) | late orders a week (se) | orders | worst sample | samples < 93.5% | not ranked |")
    print("|---|---|---|---|---|---|---|---|---|")
    for name in names:
        other = weeks(name)
        seeds = sorted(set(base) & set(other))
        if not seeds:
            continue
        d = np.array([np.subtract(measures(other[s]), measures(base[s])) for s in seeds])
        se = d.std(axis=0, ddof=1) / np.sqrt(len(d)) if len(d) > 1 else d[0] * 0
        samples = [s for seed in seeds for s in other[seed]]
        count = "×".join([str(len(seeds)), str(len(samples) // len(seeds))])
        print(f"| `{name}` | {count} | {d[:, 0].mean():+,.0f} ({se[0]:,.0f}) | {d[:, 1].mean():+.2f} ({se[1]:.2f}) | {d[:, 2].mean():+.1f} ({se[2]:.1f}) | {d[:, 3].mean():+.0f} | "
              f"{min(s['onTime'] for s in samples):.1%} | {sum(s['onTime'] < 0.935 for s in samples)} | {sum(not s['ranked'] for s in samples)} |")


if __name__ == "__main__":
    main()
