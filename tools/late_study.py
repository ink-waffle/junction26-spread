"""Where a version's late orders come from: per week by cause, per class of order, and what an order that still waits says about its end.

    python -m tools.late_study main-m9-look6-ot96 main-m9-look6-ot96-wide
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from dispatch.atlas import DAY, HOUR
from tools.study import table


def orders(tags: list[str]) -> pd.DataFrame:
    """One row per order won, with the cause of a late one: no driver before the deadline warning, a driver who dropped it, or a driver who arrived late."""
    t = pd.concat([table(tag).assign(tag=tag) for tag in tags])
    t = t[t.price.notna() & (t.get("cancelled") != True)].copy()
    t["late_order"] = ~t.on_time.astype(bool)
    booked = t.first_booked_at.fillna(np.inf)
    t["warned"] = t.warned_at.notna() & (t.warned_at <= booked)
    t["cause"] = np.where(~t.late_order, "", np.where(t.warned, "warned", np.where(t.drops > 0, "dropped", "slow")))
    t["room"] = (t.last_pickup - t.won_at) / HOUR
    t["won_day"] = t.won_at // DAY
    t["margin_eur"] = t.margin / 100
    return t


def weeks(t: pd.DataFrame) -> pd.DataFrame:
    by = t.groupby(["tag", "seed"])
    out = by.agg(orders=("id", "size"), late=("late_order", "mean"), margin=("margin_eur", "sum"), warned=("warned", "sum"))
    for cause in ("warned", "dropped", "slow"):
        out[f"late_{cause}"] = by.apply(lambda g: (g.cause == cause).sum())
    for day in range(5):
        out[f"d{day}"] = by.apply(lambda g: g[g.won_day == day].late_order.mean())
    return out


def classes(t: pd.DataFrame) -> pd.DataFrame:
    n = t.groupby(["tag", "seed"]).ngroups
    cuts = {
        "all": t.id == t.id, "private delivery": t.private_de == True, "private pickup": t.private_pu == True, "premium": t.premium == True, "trade-in": t.legs > 1,
        "drivers at pickup <= 3": t.drivers_pu <= 3, "drivers at pickup 4-15": (t.drivers_pu > 3) & (t.drivers_pu <= 15), "drivers at pickup > 15": t.drivers_pu > 15,
        "drivers at delivery <= 3": t.drivers_de <= 3, "under 40 km": t.km < 40, "40-200 km": (t.km >= 40) & (t.km < 200), "200-400 km": (t.km >= 200) & (t.km < 400), "over 400 km": t.km >= 400,
        "room < 8 h": t.room < 8, "room 8-12 h": (t.room >= 8) & (t.room < 12), "room 12-24 h": (t.room >= 12) & (t.room < 24), "room 24-48 h": (t.room >= 24) & (t.room < 48), "room > 48 h": t.room >= 48,
        "same day": t.option == "same_day", "next day": t.option == "next_day", "within 3 days": t.option == "within_3_days",
        "plain (none of the four)": ~((t.private_de == True) | (t.private_pu == True) | (t.premium == True) | (t.legs > 1)),
    }
    rows = []
    for name, mask in cuts.items():
        g = t[mask]
        rows.append({"class": name, "orders/wk": len(g) / n, "late %": 100 * g.late_order.mean(), "late/wk": g.late_order.sum() / n, "warned %": 100 * g.warned.mean(),
                     "margin/order": g.margin_eur.mean(), "margin/wk": g.margin_eur.sum() / n, "fee x": (-g.fees / g.typical).mean()})
    return pd.DataFrame(rows).set_index("class")


def waiting(t: pd.DataFrame) -> pd.DataFrame:
    """Of the orders still without a first driver some hours after they were won: how many end late, by the hours then left to the last pickup."""
    rows = []
    booked = t.first_booked_at.fillna(np.inf)
    for age in (1, 3, 6, 12, 24, 48):
        at = t.won_at + age * HOUR
        still = t[(booked > at) & (t.last_pickup - 3 * HOUR > at)]
        left = (still.last_pickup - (still.won_at + age * HOUR)) / HOUR
        for lo, hi in ((3, 12), (12, 24), (24, 48), (48, 1000)):
            g = still[(left >= lo) & (left < hi)]
            rows.append({"hours since won": age, "hours left": f"{lo}-{hi}", "orders": len(g), "late %": 100 * g.late_order.mean() if len(g) else np.nan, "warned %": 100 * g.warned.mean() if len(g) else np.nan})
    return pd.DataFrame(rows).pivot(index="hours since won", columns="hours left", values=["orders", "late %"])


def main() -> None:
    t = orders(sys.argv[1:])
    pd.set_option("display.width", 250, "display.max_columns", 40)
    print(weeks(t).round(3).to_string())
    print()
    print(classes(t).round(1).to_string())
    print()
    print(waiting(t).round(0).to_string())


if __name__ == "__main__":
    main()
