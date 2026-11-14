"""What does the desk ask for a car once a week has gone wrong? Plays a seed and keeps, for every option of every request, what the fleet said
of it at that minute (fee, chance of a late car, the price of a late order, the harm to the queue) and where the market put the dealer's level.

    python -m tools.crisis_study play fleet3-trace halal-09 [--policy '{...}']   # runs/<tag>/<seed>.json.gz and <seed>-trace.json
    python -m tools.crisis_study show fleet3-trace halal-09
"""
from __future__ import annotations

import argparse
import json
import math
import os

import pandas as pd

from dispatch import notes
from dispatch.atlas import DAY, HOUR
from dispatch.fleet import REFUND
from dispatch.market import Market
from tools import harness
from tools.study import ROOT, runs

TRACE: list[dict] = []


def traced(quote):
    def wrapper(self: Market, request):
        fleet, books = self.fleet, self.books
        queue = fleet.queue()
        late_price = fleet.late_price(queue)
        for option in request["options"]:
            spans = notes.chances(request, option, notes.read(request["note"], request["arrivedAt"]), fleet.road(request["legs"][0]))
            if not spans:
                continue
            typical, refund = request["referenceFeeCents"], REFUND * option["listPriceCents"]
            car = fleet.car(request, spans, request["respondBy"])
            multiple, late = fleet.fee(car, typical, refund, late_price, queue)
            calm = fleet.fee(car, typical, refund, 0.0, queue)
            TRACE.append({"id": request["id"], "at": books.now, "option": option["kind"], "list": option["listPriceCents"], "typical": typical, "room": math.expm1(car["slack"]),
                          "multiple": multiple, "late": late, "late_price": late_price, "backlog": queue.backlog, "queue_late": queue.late, "world": queue.world,
                          "harm": fleet.harm(multiple, queue, late_price), "refund": refund, "cost": fleet.cost(request, option), "level": self.level(request, option)[0],
                          "calm_multiple": calm[0], "calm_late": calm[1], "orders": len(books.orders)})
        return quote(self, request)
    return wrapper


def play(tag: str, seed: str, overrides: dict) -> None:
    Market.quote = traced(Market.quote)
    summary = harness.play(tag, seed, 8, overrides, save=True, stride=14)
    print(harness.line(summary))
    with open(os.path.join(ROOT, "runs", tag, f"{seed}-trace.json"), "w") as file:
        json.dump(TRACE, file)


def show(tag: str, seed: str) -> None:
    pd.set_option("display.width", 250)
    run = next(r for r in runs(tag) if r["seed"] == seed)
    with open(os.path.join(ROOT, "runs", tag, f"{seed}-trace.json")) as file:
        t = pd.DataFrame(json.load(file))
    won = {e["order"]["id"]: e["order"] for e in run["events"] if e["kind"] == "order_won"}
    t["day"] = t["at"] // DAY
    t["quoted"] = [run["quotes"].get(i, {}).get(o) for i, o in zip(t["id"], t["option"])]
    t["won"] = [i in won and won[i]["option"] == o for i, o in zip(t["id"], t["option"])]
    t["room_days"] = pd.cut(t["room"] / 24, [-1, 0.5, 1.5, 3.5, 99], labels=["today", "tomorrow", "2-3 days", "more"])
    t["fee €"], t["late cost €"], t["harm €"] = t["multiple"] * t["typical"] / 100, t["late"] * (t["refund"] + t["late_price"]) / 100, t["harm"] / 100
    t["cost/list"], t["quote/list"], t["dealer/list"] = t["cost"] / t["list"], t["quoted"] / t["list"], t["level"].map(math.exp)
    t["calm cost/list"] = (t["calm_multiple"] * t["typical"] + t["calm_late"] * t["refund"]) / t["list"]
    cols = dict(options=("won", "size"), won=("won", "sum"), late_price=("late_price", lambda s: s.mean() / 100), backlog=("backlog", "mean"), multiple=("multiple", "mean"), late=("late", "mean"),
                fee=("fee €", "mean"), late_cost=("late cost €", "mean"), harm=("harm €", "mean"), cost_list=("cost/list", "mean"), calm_cost_list=("calm cost/list", "mean"),
                quote_list=("quote/list", "median"), dealer_list=("dealer/list", "mean"), calm_multiple=("calm_multiple", "mean"), calm_late=("calm_late", "mean"))
    print(t.groupby(["day", "room_days"], observed=True).agg(**cols).round(2).to_string())
    score = run["score"]
    print(f"\n{seed}: {score['wonOrders']} orders, {score['onTimeShare']:.1%} on time, margin €{score['marginCents'] / 100:,.0f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("what", choices=["play", "show"])
    parser.add_argument("tag")
    parser.add_argument("seed")
    parser.add_argument("--policy", default="{}")
    args = parser.parse_args()
    play(args.tag, args.seed, json.loads(args.policy)) if args.what == "play" else show(args.tag, args.seed)


if __name__ == "__main__":
    main()
