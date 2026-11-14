"""Fits what the fleet bakes in, on saved weeks, and prints it for dispatch/fleet.py: ON_TIME (logistic weights of "the car arrives on time"),
BOOKED_LATE (late share of the cars that had a driver before their deadline warning) and REFUND (what a late order paid back, as a share of its list price).

    python -m tools.fleet_fit fleet-explore3 fleet-cap-L085-r0.0 main-m4-r0.15      # tags of saved runs

Each week is replayed through the books, so every sign is computed by the code that computes it in play, at the minute the request arrived.
A gig's own fee and the fee level of the queue are told apart by weeks of two kinds: random fees inside a week, and one fee for a whole week."""
from __future__ import annotations

import os
import random
import sys

import numpy as np
import pandas as pd

from dispatch import notes
from dispatch.atlas import DAY, HOUR
from dispatch.books import Books
from dispatch.fleet import ON_TIME, Fleet, FleetPolicy
from tools.study import ROOT, atlas, runs

DEFAULT = ["fleet-explore3", "fleet-cap-L085-r0.0", "fleet-cap-L100-r0.0", "fleet-cap-L115-r0.0", "main-m4-r0.3", "main-m4-r0.15", "main-m4-r0.0"]


def first_fees(run: dict) -> dict[str, float]:
    """The fee multiple each order was first posted at. The saved schedule of a repriced gig is its last one: then the first view shows it, or the run's policy."""
    typical = {e["request"]["id"]: e["request"]["referenceFeeCents"] / len(e["request"]["legs"]) for e in run["events"] if e["kind"] == "price_request"}
    policy = run["policy"].get("fleet", {})
    viewed, out = {}, {}
    for view in sorted(run["reveal"]["views"], key=lambda v: -v["at"]):
        viewed[view["gigId"]] = view
    for gig in sorted(run["gigs"], key=lambda g: g["postedAt"]):
        order_id, step, view = gig["stops"][0]["orderId"], gig["schedule"][0], viewed.get(gig["id"])
        if order_id in out:
            continue
        cars = sum(1 for stop in gig["stops"] if stop["kind"] == "pickup")
        if policy.get("explore"):
            out[order_id] = random.Random(f"{run['seed']}:{order_id}").choice(policy["explore"])
        elif len(policy.get("fees", [])) == 1:
            out[order_id] = policy["fees"][0]
        elif step["at"] <= gig["postedAt"]:
            out[order_id] = step["feeCents"] / cars / typical[order_id]
        elif view and view["at"] < step["at"]:
            out[order_id] = view["feeCents"] / cars / typical[order_id]
    return out


def request_hours(start: int, end: int) -> float:
    """The hours of [start, end] in which requests arrive: weekdays from 08:00 to 18:00."""
    return sum(max(0, min(end, day * DAY + 18 * HOUR) - max(start, day * DAY + 8 * HOUR)) for day in range(start // DAY, max(start, end) // DAY + 1) if day % 7 < 5) / HOUR


def rows(run: dict, tag: str = "") -> list[dict]:
    """One row per order won: its signs and the queue when its request arrived, the fee it was first posted at, how long it waited for a driver and whether it arrived on time."""
    books, policy = Books(run["roster"]), FleetPolicy()
    fleet = Fleet(policy, books, atlas())
    waiting = sorted(run["gigs"], key=lambda g: g["postedAt"])
    order_of = {g["id"]: g["stops"][0]["orderId"] for g in waiting}
    first_fee, signs, out, refund, posted = first_fees(run), {}, {}, {}, set()
    paid = {e["line"]["orderId"] for e in run["events"] if e["kind"] == "ledger" and e["line"]["kind"] == "revenue"}
    for event in run["events"]:
        if event["kind"] == "ledger" and event["line"]["kind"] in ("late_refund", "undelivered_penalty"):
            refund[event["line"]["orderId"]] = refund.get(event["line"]["orderId"], 0) - event["line"]["cents"]
    for event in run["events"]:
        while waiting and (waiting[0]["postedAt"] < event["at"] or waiting[0]["id"] == event.get("gigId")):
            gig = waiting.pop(0)
            order_id, schedule = order_of[gig["id"]], gig["schedule"]
            if order_id not in posted and order_id in first_fee and order_id in books.requests:  # the fee the gig opened at, not the one it ended with
                cars, request = sum(1 for stop in gig["stops"] if stop["kind"] == "pickup"), books.requests[order_id]
                schedule = [{"at": gig["postedAt"], "feeCents": int(first_fee[order_id] * request["referenceFeeCents"] / len(request["legs"]) * cars)}]
            posted.add(order_id)
            books.gig_posted({"type": "post", "stops": gig["stops"], "audience": gig["audience"], "schedule": schedule}, gig["id"], posted_at=gig["postedAt"])
        kind = event["kind"]
        if kind == "price_request":
            request, queue = event["request"], fleet.queue()
            facts = notes.read(request["note"], request["arrivedAt"])
            for option in request["options"]:
                spans = notes.chances(request, option, facts, fleet.road(request["legs"][0]))
                if spans:
                    signs[(request["id"], option["kind"])] = dict(fleet.signs(request, spans, request["respondBy"], queue.backlog), queue=queue.backlog, going=queue.going, list=option["listPriceCents"])
        elif kind == "order_won":
            order = event["order"]
            if (order["id"], order["option"]) in signs and order["id"] in first_fee:
                out[order["id"]] = dict(signs[(order["id"], order["option"])], seed=run["seed"], tag=tag, id=order["id"], option=order["option"], multiple=first_fee[order["id"]], booked=0, warned=0,
                                        on_time=int(order["id"] in paid and order["id"] not in refund), refund=refund.get(order["id"], 0), price=order["priceCents"],
                                        won_at=event["at"], wait=request_hours(event["at"], max(event["at"], order["lastPickupAt"])))
        elif kind == "gig_booked" and order_of.get(event["gigId"]) in out:
            row = out[order_of[event["gigId"]]]
            if not row["booked"] and not row["warned"]:
                row["booked"], row["wait"] = 1, min(row["wait"], request_hours(row["won_at"], event["at"]))
        elif kind == "deadline_close" and event["orderId"] in books.orders:
            if event["orderId"] in out:
                out[event["orderId"]]["warned"] = 1
            state = books.orders[event["orderId"]]
            for gig in {books.gigs[g].id: books.gigs[g] for g in state.gig_of.values() if g in books.gigs and books.gigs[g].status == "open"}.values():  # the desk raises the fee at the warning
                typical = state.request["referenceFeeCents"] * len(gig.legs) / len(state.order["legs"])
                gig.schedule = [{"at": event["at"], "feeCents": max(gig.schedule[-1]["feeCents"], int(policy.urgent_fee * typical))}]
        elif kind == "order_cancelled":
            out.pop(event["orderId"], None)
        books.observe(event)
    return list(out.values())


def table(tags: list[str]) -> pd.DataFrame:
    t = pd.DataFrame([row for tag in tags for run in runs(tag) if run.get("gigs") for row in rows(run, tag)])
    level = (t.queue * t.going + t.multiple) / (t.queue + 1)  # the going fee once the gig is in the app: Queue.level
    return t.assign(fee=np.log(t.multiple / level), level=np.log(level))


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


def held_out(t: pd.DataFrame, names: list[str]) -> float:
    """Mean log-likelihood on each seed of a model fitted on the other seeds."""
    x, y = t[names].values, t.on_time.values
    return float(np.mean([log_likelihood(x[t.seed == seed], y[t.seed == seed], fit(x[t.seed != seed], y[t.seed != seed])) for seed in sorted(t.seed.unique())]))


def main() -> None:
    t = table(sys.argv[1:] or DEFAULT)
    t.to_pickle(os.path.join(ROOT, "runs", "fleet_fit.pkl"))
    names = list(ON_TIME)
    x, y = t[names].values, t.on_time.values
    w = fit(x, y)
    t["p"] = 1 / (1 + np.exp(-x @ w))
    print(f"{len(t)} orders, {y.mean():.1%} on time; log-likelihood {log_likelihood(x, y, w):.4f}, on held-out seeds {held_out(t, names):.4f}")
    print(t.groupby(pd.cut(t.p, [0, .5, .7, .8, .85, .9, .93, .95, .97, 1]), observed=True).agg(orders=("id", "size"), predicted=("p", "mean"), on_time=("on_time", "mean"), booked=("booked", "mean"), wait=("wait", "mean")).round(3))
    print(t.groupby("tag").agg(orders=("id", "size"), fee=("multiple", "mean"), going=("going", "mean"), queue=("queue", "mean"), predicted=("p", "mean"), on_time=("on_time", "mean"), wait=("wait", "mean")).round(3))
    print("ON_TIME = {" + ", ".join(f'"{name}": {value:.2f}' for name, value in zip(names, w)) + "}")
    late = t[t.on_time == 0]
    print(f"BOOKED_LATE = {1 - t[t.booked == 1].on_time.mean():.3f}\nREFUND = {(late.refund / late.list).mean():.2f}")


if __name__ == "__main__":
    main()
