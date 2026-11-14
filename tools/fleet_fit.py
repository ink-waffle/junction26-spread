"""Fits what the fleet bakes in, on saved weeks, and prints it for dispatch/fleet.py: ON_TIME (logistic weights of "the car arrives on time"),
BOOKED_LATE (late share of the cars that had a driver before their deadline warning) and REFUND (what a late order paid back, as a share of its list price).

    python -m tools.fleet_fit fleet-explore3 fleet-cap-L085-r0.0 main-m4-r0.15      # tags of saved runs
    python -m tools.fleet_fit --calibrate main-m6                                   # the model as it stands against the outcomes of these weeks

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
from dispatch.fleet import ON_TIME, Fleet, FleetPolicy, Queue
from tools.study import ROOT, atlas, runs

LOOK = 6 * HOUR  # how often a waiting car gives the model another row
DEFAULT = ["fleet-explore3", "fleet-cap-L085-r0.0", "fleet-cap-L100-r0.0", "fleet-cap-L115-r0.0", "main-m4-r0.3", "main-m4-r0.15", "main-m4-r0.0", "market-z-all", "fleet-v5", "main-m6-nopairs"]


def first_fees(run: dict) -> dict[str, float]:
    """The fee multiple each order was first posted at. The saved schedule of a repriced gig is its last one: then the first view shows it, or the run's policy."""
    typical = {e["request"]["id"]: e["request"]["referenceFeeCents"] / len(e["request"]["legs"]) for e in run["events"] if e["kind"] == "price_request"}
    policy = run["policy"].get("fleet", {})
    viewed, out = {}, {}
    for view in sorted(run["reveal"]["views"], key=lambda v: -v["at"]):
        viewed[view["gigId"]] = view
    paired = {stop["orderId"] for gig in run["gigs"] if len({stop["orderId"] for stop in gig["stops"]}) > 1 for stop in gig["stops"]}
    for gig in sorted(run["gigs"], key=lambda g: g["postedAt"]):
        order_id, step, view = gig["stops"][0]["orderId"], gig["schedule"][0], viewed.get(gig["id"])
        if order_id in out or order_id in paired:  # a car that went with a second one tells nothing of a gig of its own
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
    first_fee, signs, out, refund, posted, looks, look = first_fees(run), {}, {}, {}, set(), [], 0
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
                    signs[(request["id"], option["kind"])] = (fleet.car(request, spans, request["respondBy"]), queue, option["listPriceCents"], option is request["options"][0])
        elif kind == "order_won":
            order = event["order"]
            if (order["id"], order["option"]) in signs and order["id"] in first_fee:
                car, queue, list_price, fastest = signs[(order["id"], order["option"])]
                leg = books.requests[order["id"]]["legs"][0]
                out[order["id"]] = dict(fleet.signs(car, first_fee[order["id"]], queue), queue=queue.backlog, going=queue.going, bookings=queue.known, list=list_price, fastest=fastest,
                                        km=atlas().km[(leg["pickup"]["placeId"], leg["delivery"]["placeId"])],
                                        seed=run["seed"], tag=tag, id=order["id"], option=order["option"], multiple=first_fee[order["id"]], booked=0, warned=0,
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
        if event["at"] >= look:  # every few hours, each car that still waits: the same question, asked of an older gig
            look, queue = event["at"] + LOOK, fleet.queue()
            for state in [s for s in books.orders.values() if s.id in out and fleet.waits(s) and fleet.posted(s) and not s.urgent]:  # after the warning the fee is no longer the one we chose
                multiple = fleet.posted(state)
                others = Queue(queue.backlog - 1, (queue.going * queue.backlog - multiple) / max(1, queue.backlog - 1), queue.known)
                car = fleet.car(state.request, fleet.chances(state), books.now, state.won_at)
                looks.append(dict(fleet.signs(car, multiple, others), queue=others.backlog, going=others.going, bookings=queue.known, list=out[state.id]["list"], seed=run["seed"], tag=tag, id=state.id,
                                  option=state.order["option"], multiple=multiple, on_time=out[state.id]["on_time"], refund=out[state.id]["refund"], won_at=state.won_at, look=1))
    return [dict(row, look=0) for row in out.values()] + [row for row in looks if row["id"] in out]


def table(tags: list[str]) -> pd.DataFrame:
    return pd.DataFrame([row for tag in tags for run in runs(tag) if run.get("gigs") for row in rows(run, tag)])


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


def calibrate(tags: list[str]) -> None:
    """The model as it stands in dispatch/fleet.py against what happened in these weeks: predicted and realised share of late orders, cut several ways."""
    t = table(tags)
    t = t[t.look == 0].copy()
    t["late"], t["predicted"] = 1 - t.on_time, 1 - 1 / (1 + np.exp(-t[list(ON_TIME)].values @ np.array(list(ON_TIME.values()))))
    t["option"], t["room"], t["weekday"] = np.where(t.fastest, "fastest", "slower"), np.expm1(t.slack), t.won_at // DAY
    cuts = {"all": t.one, "option": t.option, "hours of real room": pd.cut(t.room, [0, 8, 12, 24, 30, 48, 80, 400]), "lane km": pd.cut(t.km, [0, 40, 80, 150, 250, 400, 2000]), "weekday": t.weekday,
            "first fee": t.multiple.round(2), "queue": pd.cut(t.queue, [-1, 5, 10, 20, 30, 50, 500]), "premium": t.premium, "trade-in": t.trade_in,
            "option and room": [t.option, pd.cut(t.room, [0, 12, 24, 48, 80, 400])]}
    print(f"{len(t)} orders of {', '.join(tags)}")
    for name, by in cuts.items():
        print(f"\nby {name}\n" + t.groupby(by, observed=True).agg(orders=("id", "size"), late=("late", "mean"), predicted=("predicted", "mean"), fee=("multiple", "mean")).round(3).to_string())


def add(names: list[str], tags: list[str]) -> None:
    """Weights for new signs with the rest of the model held as it stands, on these weeks, and the intercept that leaves the model's mean chance where it was:
    the new signs then only move risk between cars, and the caution the control was tuned with stays."""
    t = table(tags)
    t = t[t.look == 0]
    held = [name for name in ON_TIME if name not in names and name != "waited"]
    base, y = t[held].values @ np.array([ON_TIME[name] for name in held]), t.on_time.values
    x = np.column_stack([np.ones(len(t))] + [t[name].values for name in names])
    w = np.zeros(x.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-base - x @ w))
        w -= np.linalg.solve((x * (p * (1 - p))[:, None]).T @ x + 1e-2 * np.eye(len(w)), x.T @ (p - y) + 1e-2 * w)
    extra, before, low, high = x[:, 1:] @ w[1:], (1 / (1 + np.exp(-base))).mean(), -5.0, 5.0
    for _ in range(60):  # bisection: the intercept at which the mean chance is the old one
        shift = (low + high) / 2
        low, high = (shift, high) if (1 / (1 + np.exp(-base - extra - shift))).mean() < before else (low, shift)
    chance = lambda logit: np.clip(1 / (1 + np.exp(-logit)), 1e-6, 1 - 1e-6)
    score = lambda logit: float(np.mean(y * np.log(chance(logit)) + (1 - y) * np.log(1 - chance(logit))))
    print(f"{len(t)} orders of {', '.join(tags)}: {1 - y.mean():.1%} late, the model says {1 - before:.1%}")
    print(f"log-likelihood as it stands {score(base):.4f}, with its intercept fitted {score(base + np.log(y.mean() / (1 - y.mean())) - np.log(before / (1 - before))):.4f}, with the new signs {score(base + x @ w):.4f}")
    print("ON_TIME: " + ", ".join(f'"{name}": {weight:.2f}' for name, weight in zip(names, w[1:])) + f', "one": {ON_TIME["one"] + shift:.2f}  (the intercept moved by {shift:+.2f}; fitted freely it would move by {w[0]:+.2f})')


def main() -> None:
    if sys.argv[1:2] == ["--calibrate"]:
        return calibrate(sys.argv[2:])
    if sys.argv[1:2] == ["--add"]:
        return add(sys.argv[2].split(","), sys.argv[3:])
    t = table(sys.argv[1:] or DEFAULT)
    t.to_pickle(os.path.join(ROOT, "runs", "fleet_fit.pkl"))
    names = [name for name in ON_TIME if name != "waited"]
    won, looks = t[t.look == 0].copy(), t[t.look == 1].copy()
    x, y = won[names].values, won.on_time.values
    w = fit(x, y)
    won["p"] = 1 / (1 + np.exp(-x @ w))
    print(f"{len(won)} orders, {y.mean():.1%} on time; log-likelihood {log_likelihood(x, y, w):.4f}, on held-out seeds {held_out(won, names):.4f}")
    print(won.groupby(pd.cut(won.p, [0, .5, .7, .8, .85, .9, .93, .95, .97, 1]), observed=True).agg(orders=("id", "size"), predicted=("p", "mean"), on_time=("on_time", "mean"), booked=("booked", "mean"), wait=("wait", "mean")).round(3))
    print(won.groupby("tag").agg(orders=("id", "size"), fee=("multiple", "mean"), going=("going", "mean"), queue=("queue", "mean"), predicted=("p", "mean"), on_time=("on_time", "mean"), wait=("wait", "mean")).round(3))
    waited, base = 0.0, looks[names].values @ w  # what an hour without a taker says: one weight, fitted on the later looks with the rest of the model held
    for _ in range(30):
        p = 1 / (1 + np.exp(-base - waited * looks.waited.values))
        waited += float((looks.waited.values * (looks.on_time.values - p)).sum() / ((looks.waited.values ** 2 * p * (1 - p)).sum() + 1e-9))
    looks["before"], looks["p"], looks["hours"] = 1 / (1 + np.exp(-base)), 1 / (1 + np.exp(-base - waited * looks.waited.values)), (looks.won_at * 0 + 1)
    print(f"{len(looks)} later looks at waiting cars, {looks.on_time.mean():.1%} on time in the end; the model for a new gig says {looks.before.mean():.1%}, with the hour they waited {looks.p.mean():.1%}")
    print(looks.groupby(pd.cut(looks.p, [0, .5, .7, .8, .9, .95, 1]), observed=True).agg(looks=("id", "size"), as_new=("before", "mean"), predicted=("p", "mean"), on_time=("on_time", "mean")).round(3))
    print("ON_TIME = {" + ", ".join(f'"{name}": {value:.2f}' for name, value in zip(names + ["waited"], list(w) + [waited])) + "}")
    late = won[won.on_time == 0]
    print(f"BOOKED_LATE = {1 - won[won.booked == 1].on_time.mean():.3f}\nREFUND = {(late.refund / late.list).mean():.2f}")


if __name__ == "__main__":
    main()
