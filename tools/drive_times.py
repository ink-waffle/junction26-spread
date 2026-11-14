"""How much longer than the map's road minutes does a real drive take? The source of timetable.SLOW_DRIVE.

    python -m tools.drive_times base1,explore1        # tune worlds
    python -m tools.drive_times <runs on hold seeds>   # to confirm

Uses each single-car delivery of saved runs without snow or a charging stop: (delivered - picked up) / road minutes."""
from __future__ import annotations

import sys

from tools.study import atlas, runs


def ratios(tags: list[str]) -> list[float]:
    a, out = atlas(), []
    for tag in tags:
        for run in runs(tag):
            legs = {item["request"]["id"]: item["request"]["legs"] for item in run["reveal"]["requests"]}
            snow = [e for e in run["events"] if e["kind"] == "forecast"]
            picked = {(e["orderId"], e["leg"]): e for e in run["events"] if e["kind"] == "picked_up"}
            for e in run["events"]:
                start = picked.get((e.get("orderId"), e.get("leg"))) if e["kind"] == "delivered" else None
                if start is None or len(legs[e["orderId"]]) > 1:
                    continue
                car, ends = legs[e["orderId"]][0]["car"], (start["placeId"], e["placeId"])
                road, took = a.drive(*ends), e["at"] - start["at"]
                charged = car["electric"] and (car["chargePercent"] or 100) < 30 and a.km[ends] > 200
                snowy = any(f["from"] <= start["at"] < f["to"] and set(ends) & set(f["placeIds"]) for f in snow)
                if road >= 20 and took <= 2.5 * road + 60 and not charged and not snowy:  # a car left at a closed site counts hours later
                    out.append(took / road)
    return sorted(out)


if __name__ == "__main__":
    found = ratios(sys.argv[1].split(","))
    print(f"{len(found)} drives: real / map minutes " + "  ".join(f"p{q} {found[int(len(found) * q / 100)]:.3f}" for q in (5, 25, 50, 75, 90, 95, 99)))
