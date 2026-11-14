"""Versions side by side on the weeks they share, from runs/log.jsonl: margin, orders, late orders and the worst week of each, against the first tag.

    python -m tools.compare fleet2-base-look6 fleet2-k1-spare fleet2-k2-redrop
"""
from __future__ import annotations

import json
import os
import sys

from tools.study import ROOT


def results(tags: list[str]) -> dict[str, dict[str, dict]]:
    """tag -> seed -> the summary of its last run."""
    out: dict[str, dict[str, dict]] = {tag: {} for tag in tags}
    with open(os.path.join(ROOT, "runs", "log.jsonl")) as file:
        for line in file:
            entry = json.loads(line)
            for tag in tags:
                if entry["tag"] == tag or entry["tag"].startswith(tag + "+"):
                    out[tag].update({r["seed"]: r for r in entry["results"]})
    return out


def main() -> None:
    names = [name.split("+") for name in sys.argv[1:]]  # a+b joins the weeks of two tags into one version
    flat = [tag for name in names for tag in name]
    found = results(flat)
    versions = {"+".join(name): {seed: r for tag in name for seed, r in found[tag].items()} for name in names}
    base = next(iter(versions.values()))
    print(f"{'version':<34} {'weeks':>5} {'margin':>8} {'vs base':>8} {'orders':>7} {'late/wk':>8} {'on time':>8} {'worst':>7} {'weeks<93.5':>10} {'fee':>5} {'drops':>6}  (base = first, on shared weeks)")
    for name, weeks in versions.items():
        seeds = sorted(set(weeks) & set(base))
        if not seeds:
            continue
        n = len(seeds)
        mean = lambda key, of=weeks: sum(of[s][key] for s in seeds) / n
        late = sum(weeks[s]["won"] * (1 - weeks[s]["onTime"]) for s in seeds) / n
        worst = min(seeds, key=lambda s: weeks[s]["onTime"])
        print(f"{name:<34} {n:>5} {mean('margin'):>8,.0f} {mean('margin') - mean('margin', base):>+8,.0f} {mean('won'):>7.0f} {late:>8.1f} {1 - late / mean('won'):>8.1%} "
              f"{weeks[worst]['onTime']:>7.1%} {sum(weeks[s]['onTime'] < 0.935 for s in seeds):>10} {mean('fee'):>5.2f} {mean('drops'):>6.1f}  {worst}")


if __name__ == "__main__":
    main()
