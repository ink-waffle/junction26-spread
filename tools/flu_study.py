"""The flu: nobody announces it, but in the hour after midnight its drivers give back the gigs of that day. Per week: the night with the most drops in that hour,
where those drivers live, what the drivers of those towns do on that day against their other days, and how the dropped orders end.

    python -m tools.flu_study fleet2-s-v2b fleet2-s-v2b-wide
"""
from __future__ import annotations

import sys
from collections import Counter

import pandas as pd

from dispatch.atlas import DAY, HOUR
from tools.study import runs


def week(run: dict) -> dict:
    events, homes = run["events"], {d["id"]: d["homePlaceId"] for d in run["roster"]}
    owners = {g["id"]: list(dict.fromkeys(s["orderId"] for s in g["stops"])) for g in run["gigs"]}
    refunded = {e["line"]["orderId"] for e in events if e["kind"] == "ledger" and e["line"]["kind"] in ("late_refund", "undelivered_penalty")}
    paid = {e["line"]["orderId"] for e in events if e["kind"] == "ledger" and e["line"]["kind"] == "revenue"}
    won = [e["order"]["id"] for e in events if e["kind"] == "order_won"]
    late = {o for o in won if o in refunded or o not in paid}
    drops = [e for e in events if e["kind"] == "gig_dropped"]
    day, count = Counter(e["at"] // DAY for e in drops if e["at"] % DAY < HOUR).most_common(1)[0] if drops else (0, 0)  # the night with the most drops in its first hour
    night = [e for e in drops if e["at"] // DAY == day and e["at"] % DAY < HOUR]
    towns = Counter(homes.get(e["driverId"]) for e in night)
    sick_towns = {town for town, n in towns.items() if n >= 2}
    hit = {o for e in night for o in owners.get(e["gigId"], [])}
    local = {d for d, home in homes.items() if home in sick_towns}
    booked = Counter(e["at"] // DAY for e in events if e["kind"] == "gig_booked" and e["driverId"] in local)
    viewed = Counter(v["at"] // DAY for v in run["reveal"]["views"] if v["driverId"] in local)
    other = [d for d in range(5) if d != day]
    return {"seed": run["seed"], "day": day, "drops in that hour": count, "drops in the week": len(drops), "towns": ", ".join(f"{t} {n}" for t, n in towns.most_common(4)),
            "orders dropped": len(hit), "of them late": len(hit & late), "late in the week": len(late), "drivers of those towns": len(local),
            "their bookings that day": booked[day], "on other weekdays": round(sum(booked[d] for d in other) / max(1, len(other)), 1),
            "their views that day": viewed[day], "views other weekdays": round(sum(viewed[d] for d in other) / max(1, len(other)), 1), "next day bookings": booked[day + 1]}


def main() -> None:
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_rows", 100)
    t = pd.DataFrame([week(run) for tag in sys.argv[1:] for run in runs(tag)])
    print(t.to_string(index=False))
    print(f"\n{len(t)} weeks: the night's drops {t['drops in that hour'].mean():.1f} of {t['drops in the week'].mean():.1f} a week; orders dropped that night {t['orders dropped'].mean():.1f}, late {t['of them late'].mean():.1f} "
          f"({t['of them late'].sum() / max(1, t['orders dropped'].sum()):.0%}) of {t['late in the week'].mean():.1f} late orders a week")


if __name__ == "__main__":
    main()
