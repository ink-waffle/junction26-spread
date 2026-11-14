"""Two policies on the same weeks, each played several times (the same seed at other strides is another sample of the same policy: one week moves by a point
of on-time and EUR 1-3k between them). Per week: on time and margin of every sample; then the means, and the paired difference with its standard error.

    python -m tools.replicates fleet3-main-s12,fleet3-main-s13,fleet3-main-s15 fleet3-flu-s12,fleet3-flu-s13,fleet3-flu-s15
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import sys

import numpy as np

from tools.study import ROOT


def weeks(tags: list[str]) -> dict[str, list[dict]]:
    """seed -> the summary of each saved sample."""
    out: dict[str, list[dict]] = {}
    for tag in tags:
        for path in sorted(glob.glob(os.path.join(ROOT, "runs", tag, "*.json.gz"))):
            with gzip.open(path, "rt") as file:
                run = json.load(file)
            out.setdefault(run["seed"], []).append(run["summary"])
    return out


def main() -> None:
    a, b = (weeks(arg.split(",")) for arg in sys.argv[1:3])
    seeds = sorted(set(a) & set(b))
    mean = lambda rows, key: float(np.mean([row[key] for row in rows]))
    late = lambda rows: float(np.mean([row["won"] * (1 - row["onTime"]) for row in rows]))
    print(f"{'week':<9} {'first: on time of each sample':<34} {'second':<34} {'on time':>15} {'late orders':>13} {'margin':>17}")
    diffs = []
    for seed in seeds:
        show = lambda rows: " ".join(f"{row['onTime'] * 100:.1f}" for row in rows)
        diffs.append((mean(b[seed], "onTime") - mean(a[seed], "onTime"), late(b[seed]) - late(a[seed]), mean(b[seed], "margin") - mean(a[seed], "margin")))
        print(f"{seed:<9} {show(a[seed]):<34} {show(b[seed]):<34} {mean(a[seed], 'onTime'):>6.1%} -> {mean(b[seed], 'onTime'):<6.1%} {late(a[seed]):>5.1f} -> {late(b[seed]):<5.1f} "
              f"{mean(a[seed], 'margin'):>7,.0f} -> {mean(b[seed], 'margin'):<7,.0f}")
    d = np.array(diffs)
    se = d.std(axis=0, ddof=1) / np.sqrt(len(d))
    worst = lambda x: min(row["onTime"] for rows in x.values() for row in rows)
    under = lambda x: sum(row["onTime"] < 0.935 for seed in seeds for row in x[seed])
    print(f"\n{len(seeds)} weeks, {sum(len(a[s]) for s in seeds)} and {sum(len(b[s]) for s in seeds)} samples: on time {d[:, 0].mean() * 100:+.2f} points (se {se[0] * 100:.2f}), "
          f"late orders {d[:, 1].mean():+.1f} a week (se {se[1]:.1f}), margin {d[:, 2].mean():+,.0f} (se {se[2]:,.0f}); weeks up {int((d[:, 0] > 0).sum())} of {len(d)}")
    print(f"worst sample {worst({s: a[s] for s in seeds}):.1%} -> {worst({s: b[s] for s in seeds}):.1%}; samples under 93.5%: {under(a)} -> {under(b)}")


if __name__ == "__main__":
    main()
