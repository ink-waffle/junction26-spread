"""The ablation table of research/skeptic: every variant against a baseline on the same weeks, as paired differences per week
(a week's samples are the same seed at several strides; a variant is set against the baseline's samples of the same strides, and they are
averaged per week first), with standard errors over weeks. Prints Markdown.

    python -m tools.ablations skeptic-base skeptic-nolook skeptic-nopairs ...       # each name stands for the tags <name>-s14, <name>-s13, ...
    python -m tools.ablations --frontier skeptic-t965 skeptic-t975 skeptic-base ...  # also the margin at equal on time

With `--frontier`, a point of on-time is priced at what the on-time target buys it for on these weeks (between the two named variants),
and "at equal on time" is the margin difference with the variant's on-time difference paid at that price: a part that only trades
on-time for margin, as the target does, shows about zero there.
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys

import numpy as np

from tools.study import ROOT


def weeks(name: str, cache: dict = {}) -> dict[str, dict[str, dict]]:
    """seed -> stride -> the summary of that saved sample of this variant."""
    if name not in cache:
        out: dict[str, dict[str, dict]] = {}
        for path in sorted(glob.glob(os.path.join(ROOT, "runs", f"{name}-s[0-9]*", "*.json.gz"))):
            brief = path[:-8] + ".summary.json"  # a small copy: a saved week is 15 MB
            if os.path.exists(brief):
                with open(brief) as file:
                    summary = json.load(file)
            else:
                try:
                    with gzip.open(path, "rt") as file:
                        summary = json.load(file)["summary"]
                except (EOFError, OSError, ValueError):  # a week that is being written now
                    continue
                with open(brief, "w") as file:
                    json.dump(summary, file)
            out.setdefault(summary["seed"], {})[os.path.basename(os.path.dirname(path)).rsplit("-s", 1)[1]] = summary
        cache[name] = out
    return cache[name]


def measures(samples: list[dict]) -> tuple[float, float, float, float]:
    mean = lambda f: float(np.mean([f(s) for s in samples]))
    return mean(lambda s: s["margin"]), mean(lambda s: s["onTime"] * 100), mean(lambda s: s["won"] * (1 - s["onTime"])), mean(lambda s: s["won"])


def against(base: dict, other: dict) -> tuple[np.ndarray, list[dict]]:
    """Per week: the variant's measures minus the baseline's over the strides both have; and the variant's samples."""
    rows, samples = [], []
    for seed in sorted(set(base) & set(other)):
        strides = sorted(set(base[seed]) & set(other[seed]))
        if strides:
            rows.append(np.subtract(measures([other[seed][s] for s in strides]), measures([base[seed][s] for s in strides])))
            samples += [other[seed][s] for s in strides]
    return np.array(rows), samples


def main() -> None:
    names, price = sys.argv[1:], None
    if names[0] == "--frontier":
        low, high, names = names[1], names[2], names[3:]
    base = weeks(names[0])
    flat = [s for samples in base.values() for s in samples.values()]
    print(f"Baseline `{names[0]}`: {len(base)} weeks, {len(flat)} samples: margin EUR {np.mean([s['margin'] for s in flat]):,.0f} a week, on time {np.mean([s['onTime'] for s in flat]):.1%} "
          f"(worst sample {min(s['onTime'] for s in flat):.1%}), {np.mean([s['won'] for s in flat]):.0f} orders, {np.mean([s['won'] * (1 - s['onTime']) for s in flat]):.1f} late a week.")
    if sys.argv[1] == "--frontier":
        a, b = against(base, weeks(low))[0].mean(axis=0), against(base, weeks(high))[0].mean(axis=0)
        price = (a[0] - b[0]) / (b[1] - a[1])
        print(f"A point of on-time costs EUR {price:,.0f} of margin through the target (`{low}`: {a[0]:+,.0f} and {a[1]:+.2f} points; `{high}`: {b[0]:+,.0f} and {b[1]:+.2f}).")
    print("\n| Without | weeks × samples | margin (se) | on time, points (se) | " + ("margin at equal on time (se) | " if price else "") + "late orders a week (se) | orders | worst sample | samples < 93.5% | not ranked |")
    print("|---|---|---|---|---|---|---|---|---|" + ("---|" if price else ""))
    for name in names[1:]:
        d, samples = against(base, weeks(name))
        if not len(d):
            continue
        se = lambda x: x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else 0.0
        equal = d[:, 0] + price * d[:, 1] if price else None
        print(f"| `{name}` | {len(d)}×{len(samples) // len(d)} | {d[:, 0].mean():+,.0f} ({se(d[:, 0]):,.0f}) | {d[:, 1].mean():+.2f} ({se(d[:, 1]):.2f}) | "
              + (f"{equal.mean():+,.0f} ({se(equal):,.0f}) | " if price else "")
              + f"{d[:, 2].mean():+.1f} ({se(d[:, 2]):.1f}) | {d[:, 3].mean():+.0f} | {min(s['onTime'] for s in samples):.1%} | {sum(s['onTime'] < 0.935 for s in samples)} | {sum(not s['ranked'] for s in samples)} |")


if __name__ == "__main__":
    main()
