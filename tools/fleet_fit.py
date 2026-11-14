"""Fits what the fleet bakes in, on saved weeks, and prints it for dispatch/fleet.py: ON_TIME (logistic weights of "the car arrives on time"),
WAIT (hours a car waits for a driver, by its chance of being late) and, from two runs of the same seeds, the crowding of a waiting car.

    python -m tools.fleet_fit fleet-explore2 base1-all:1.15 base1:1.15      # tag, or tag:the flat fee multiple of that run
    python -m tools.fleet_fit --crowding base1-all:1.15 base1:1.15          # the same requests under a heavier and a lighter book

Each week is replayed through the books, so every sign is computed by the code that computes it in play, at the minute the request arrived."""
from __future__ import annotations

import os
import random
import sys
from typing import Optional

import numpy as np
import pandas as pd

from dispatch.atlas import DAY, HOUR
from dispatch.books import Books
from dispatch.fleet import ON_TIME, Fleet, FleetPolicy
from tools.study import ROOT, atlas, runs

DEFAULT = ["fleet-explore2", "base1-all:1.15", "base1:1.15", "fleet-v1", "fleet-v2", "fleet-v2-nocrowd"]


def first_fees(run: dict, flat: Optional[float]) -> dict[str, float]:
    """The fee multiple each order was first posted at. The saved schedule of a repriced gig is its last one: then the first view shows it, or the run's policy."""
    typical = {e["request"]["id"]: e["request"]["referenceFeeCents"] / len(e["request"]["legs"]) for e in run["events"] if e["kind"] == "price_request"}
    explore = run["policy"].get("fleet", {}).get("explore")
    viewed, out = {}, {}
    for view in sorted(run["reveal"]["views"], key=lambda v: -v["at"]):
        viewed[view["gigId"]] = view
    for gig in sorted(run["gigs"], key=lambda g: g["postedAt"]):
        order_id, step, view = gig["stops"][0]["orderId"], gig["schedule"][0], viewed.get(gig["id"])
        if order_id in out:
            continue
        cars = sum(1 for stop in gig["stops"] if stop["kind"] == "pickup")
        if step["at"] <= gig["postedAt"]:
            out[order_id] = step["feeCents"] / cars / typical[order_id]
        elif view and view["at"] < step["at"]:
            out[order_id] = view["feeCents"] / cars / typical[order_id]
        elif explore:
            out[order_id] = random.Random(f"{run['seed']}:{order_id}").choice(explore)
        elif flat:
            out[order_id] = flat
    return out


def request_hours(start: int, end: int) -> float:
    """The hours of [start, end] in which requests arrive: weekdays from 08:00 to 18:00."""
    return sum(max(0, min(end, day * DAY + 18 * HOUR) - max(start, day * DAY + 8 * HOUR)) for day in range(start // DAY, max(start, end) // DAY + 1) if day % 7 < 5) / HOUR


def rows(run: dict, tag: str = "", flat: Optional[float] = None) -> list[dict]:
    """One row per order won: its signs when its request arrived, the fee it was first posted at, how long it waited for a driver and whether it arrived on time."""
    books = Books(run["roster"])
    fleet = Fleet(FleetPolicy(), books, atlas())
    waiting = sorted(run["gigs"], key=lambda g: g["postedAt"])
    order_of = {g["id"]: g["stops"][0]["orderId"] for g in waiting}
    first_fee, signs, out = first_fees(run, flat), {}, {}
    late = {e["line"]["orderId"] for e in run["events"] if e["kind"] == "ledger" and e["line"]["kind"] in ("late_refund", "undelivered_penalty")}
    paid = {e["line"]["orderId"] for e in run["events"] if e["kind"] == "ledger" and e["line"]["kind"] == "revenue"}
    for event in run["events"]:
        while waiting and (waiting[0]["postedAt"] < event["at"] or waiting[0]["id"] == event.get("gigId")):
            gig = waiting.pop(0)
            books.gig_posted({"type": "post", "stops": gig["stops"], "audience": gig["audience"], "schedule": gig["schedule"]}, gig["id"], posted_at=gig["postedAt"])
        kind = event["kind"]
        if kind == "price_request":
            request, backlog = event["request"], len(fleet.waiting())
            for option in request["options"]:
                last = fleet.last_pickup(request, option)
                if last is not None:
                    signs[(request["id"], option["kind"])] = fleet.signs(request, last, request["respondBy"], backlog)
        elif kind == "order_won":
            order = event["order"]
            if (order["id"], order["option"]) in signs and order["id"] in first_fee:
                out[order["id"]] = dict(signs[(order["id"], order["option"])], seed=run["seed"], tag=tag, id=order["id"], multiple=first_fee[order["id"]], booked=0, warned=0,
                                        on_time=int(order["id"] in paid and order["id"] not in late), won_at=event["at"], wait=request_hours(event["at"], max(event["at"], order["lastPickupAt"])))
        elif kind == "gig_booked" and order_of.get(event["gigId"]) in out:
            row = out[order_of[event["gigId"]]]
            if not row["booked"] and not row["warned"]:
                row["booked"], row["wait"] = 1, min(row["wait"], request_hours(row["won_at"], event["at"]))
        elif kind == "deadline_close" and event["orderId"] in out:
            out[event["orderId"]]["warned"] = 1
        elif kind == "order_cancelled":
            out.pop(event["orderId"], None)
        books.observe(event)
    return list(out.values())


def table(tags: list[str]) -> pd.DataFrame:
    """The rows of every saved week of these tags; `tag:1.15` says that the run posted every order at that flat multiple."""
    parts = [(tag.split(":")[0], float(tag.split(":")[1]) if ":" in tag else None) for tag in tags]
    return pd.DataFrame([row for tag, flat in parts for run in runs(tag) if run.get("gigs") for row in rows(run, tag, flat)])


def design(t: pd.DataFrame) -> pd.DataFrame:
    """The columns of the model, in the order of ON_TIME: the signs and the fee."""
    return t.assign(fee=t.multiple - 1)[list(ON_TIME)]


def fit(x: np.ndarray, y: np.ndarray, ridge: float = 1e-2) -> np.ndarray:
    """Logistic regression by Newton's method."""
    w = np.zeros(x.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-x @ w))
        w -= np.linalg.solve((x * (p * (1 - p))[:, None]).T @ x + ridge * np.eye(x.shape[1]), x.T @ (p - y) + ridge * w)
    return w


def log_likelihood(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> float:
    p = np.clip(1 / (1 + np.exp(-x @ w)), 1e-6, 1 - 1e-6)
    return float(np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def crowding(heavy: str, light: str) -> None:
    """Two runs of the same seeds that won the same requests at the same fee, one with more orders: the late orders that each extra hour of waiting caused among the shared ones."""
    a, b = table([heavy]), table([light])
    both = a.merge(b, on=["seed", "id"], suffixes=("_heavy", "_light"))
    caused, hours = (both.on_time_light - both.on_time_heavy).sum(), a.wait.sum() - b.wait.sum()
    print(f"{len(both)} shared orders: {both.on_time_heavy.mean():.1%} on time under the heavier book, {both.on_time_light.mean():.1%} under the lighter; "
          f"{caused:.0f} more late for {hours:.0f} more car-hours of waiting\nCROWDING = {caused / hours:.3f}")


def main() -> None:
    if sys.argv[1:2] == ["--crowding"]:
        return crowding(*sys.argv[2:4])
    t = table(sys.argv[1:] or DEFAULT)
    t.to_pickle(os.path.join(ROOT, "runs", "fleet_fit.pkl"))
    x, y, seeds = design(t), t.on_time.values, sorted(t.seed.unique())
    held_out = [log_likelihood(x[t.seed == seed].values, y[t.seed == seed], fit(x[t.seed != seed].values, y[t.seed != seed])) for seed in seeds]
    w = fit(x.values, y)
    t["p"] = 1 / (1 + np.exp(-x.values @ w))
    print(f"{len(t)} orders, {y.mean():.1%} on time; log-likelihood {log_likelihood(x.values, y, w):.4f}, on held-out seeds {np.mean(held_out):.4f}")
    print(t.groupby(pd.cut(t.p, [0, .5, .7, .8, .85, .9, .93, .95, .97, 1]), observed=True).agg(orders=("id", "size"), predicted=("p", "mean"), on_time=("on_time", "mean"), booked=("booked", "mean"), wait=("wait", "mean")).round(3))
    print(t.groupby("tag").agg(orders=("id", "size"), predicted=("p", "mean"), on_time=("on_time", "mean"), wait=("wait", "mean")).round(3))
    print("ON_TIME = {\n    " + ", ".join(f'"{name}": {value:.2f}' for name, value in zip(x.columns, w)) + ",\n}")
    slope, base = np.polyfit(1 - t.p, t.wait, 1)
    print(f"WAIT = ({base:.2f}, {slope:.2f})")


if __name__ == "__main__":
    main()
