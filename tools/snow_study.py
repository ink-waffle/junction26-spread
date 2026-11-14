"""Snow: when a forecast is announced, for which places and hours, and how the orders that touch it end.

    python -m tools.snow_study fleet2-s-v2b fleet2-s-v2b-wide

An order is "in the snow" when its pickup or delivery place is in a forecast and the snow's hours overlap the time from its win (or the car's ready time) to its last pickup plus the drive;
"known" when the forecast had been announced before the order was won."""
from __future__ import annotations

import sys

import pandas as pd

from dispatch.atlas import DAY, HOUR, clock
from tools.late_study import orders
from tools.study import runs


def forecasts(tags: list[str]) -> pd.DataFrame:
    return pd.DataFrame([{"tag": tag, "seed": run["seed"], "at": e["at"], "from": e["from"], "to": e["to"], "places": set(e["placeIds"])}
                         for tag in tags for run in runs(tag) for e in run["events"] if e["kind"] == "forecast"])


def main() -> None:
    pd.set_option("display.width", 220, "display.max_rows", 100)
    tags = sys.argv[1:]
    f, t = forecasts(tags), orders(tags)
    weeks = t.groupby(["tag", "seed"]).ngroups
    print(f"{len(f) / weeks:.1f} forecasts a week; announced a median {((f['from'] - f['at']) / HOUR).median():.0f} h ahead (quartiles {((f['from'] - f['at']) / HOUR).quantile(.25):.0f}-{((f['from'] - f['at']) / HOUR).quantile(.75):.0f}), "
          f"lasting a median {((f['to'] - f['from']) / HOUR).median():.0f} h, over a median {f.places.map(len).median():.0f} places")
    print(f.assign(announced=f["at"].map(clock), begins=f["from"].map(clock), ends=f["to"].map(clock), n=f.places.map(len)).groupby(["tag", "seed"]).head(3)[["seed", "announced", "begins", "ends", "n"]].head(24).to_string(index=False))
    rows = []
    for (tag, seed), g in t.groupby(["tag", "seed"]):
        snow = f[(f.tag == tag) & (f.seed == seed)]
        for _, r in g.iterrows():
            start, end = max(r.won_at, r.ready), r.last_pickup + r.minutes
            hit = [s for _, s in snow.iterrows() if ({r.pu, r.de} & s.places) and s["from"] < end and s["to"] > start]
            last = [s for s in hit if s["from"] <= r.last_pickup + r.minutes and s["to"] >= r.last_pickup - DAY]
            rows.append({"snow": "none" if not hit else "known at the win" if any(s["at"] <= r.won_at for s in hit) else "announced after the win", "last_day": bool(last),
                         "late": r.late_order, "cause": r.cause, "drops": r.drops, "margin": r.margin_eur, "seed": seed, "pair": r.get("bookings", 0)})
    x = pd.DataFrame(rows)
    print("\norders by snow on their way, a week")
    print(x.groupby("snow").agg(orders=("late", lambda s: len(s) / weeks), late=("late", "mean"), late_per_week=("late", lambda s: s.sum() / weeks), dropped=("drops", lambda s: (s > 0).mean()), margin=("margin", "mean")).round(3).to_string())
    print("\nthe same, only orders whose last day before the last pickup has the snow")
    print(x[x.last_day].groupby("snow").agg(orders=("late", lambda s: len(s) / weeks), late=("late", "mean"), late_per_week=("late", lambda s: s.sum() / weeks), dropped=("drops", lambda s: (s > 0).mean()), margin=("margin", "mean")).round(3).to_string())
    print("\nlate orders with snow on their last day, by cause:", x[x.last_day & x.late].cause.value_counts().to_dict())
    by = x.groupby("seed").agg(orders=("late", "size"), late=("late", "sum"), in_snow=("last_day", "sum"), late_in_snow=("late", lambda s: (s & x.loc[s.index, "last_day"]).sum()))
    print("\nby week: orders, late orders, orders with snow on their last day, late ones among them")
    print(by.T.to_string())


if __name__ == "__main__":
    main()
