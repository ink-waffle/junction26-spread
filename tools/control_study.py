"""What the fleet's control saw during a saved week, and when: the week is replayed through the books and the fleet, and every few hours it prints
the orders so far, the late ones it knew of, the queue's expected late orders, the world's learned shift and the price of a late order,
next to what the week later showed (how many of the orders won by then ended late).

    python -m tools.control_study main-m9-look6-ot96-wide halal-30 [policy JSON]
"""
from __future__ import annotations

import json
import sys

from dispatch.atlas import HOUR, clock
from dispatch.books import Books
from dispatch.fleet import BOOKED_LATE, Fleet, FleetPolicy
from tools.fleet_fit import first_fees
from tools.study import atlas, runs


def trace(run: dict, policy: FleetPolicy, every: int = 4 * HOUR) -> list[dict]:
    books = Books(run["roster"])
    fleet = Fleet(policy, books, atlas())
    waiting = sorted(run["gigs"], key=lambda g: g["postedAt"])
    first_fee, posted = first_fees(run), set()
    paid = {e["line"]["orderId"] for e in run["events"] if e["kind"] == "ledger" and e["line"]["kind"] == "revenue"}
    refunded = {e["line"]["orderId"] for e in run["events"] if e["kind"] == "ledger" and e["line"]["kind"] in ("late_refund", "undelivered_penalty")}
    ended_late = lambda order_id: order_id in refunded or order_id not in paid
    out, look = [], 8 * HOUR
    for event in run["events"]:
        while waiting and (waiting[0]["postedAt"] < event["at"] or waiting[0]["id"] == event.get("gigId")):
            gig = waiting.pop(0)
            order_id, schedule = gig["stops"][0]["orderId"], gig["schedule"]
            if order_id not in posted and order_id in first_fee and order_id in books.requests:
                cars, request = sum(1 for stop in gig["stops"] if stop["kind"] == "pickup"), books.requests[order_id]
                schedule = [{"at": gig["postedAt"], "feeCents": int(first_fee[order_id] * request["referenceFeeCents"] / len(request["legs"]) * cars)}]
            posted.add(order_id)
            action = {"type": "post", "stops": gig["stops"], "audience": gig["audience"], "schedule": schedule}
            now, books.now = books.now, gig["postedAt"]
            fleet.gig_posted(action)
            books.now = now
            books.gig_posted(action, gig["id"], posted_at=gig["postedAt"])
        books.observe(event)
        if event["at"] >= look and event["kind"] == "price_request":
            look = event["at"] + every
            queue = fleet.queue()
            known = sum(1 for s in books.orders.values() if s.late or s.id in books.refunded)
            urgent = sum(1 for s in books.orders.values() if s.urgent and fleet.needs_driver(s) and not s.late)
            expected = queue.late - BOOKED_LATE * queue.backlog + sum((1.0 if s.late else BOOKED_LATE) if s.undelivered() else s.id in books.refunded for s in books.orders.values())
            out.append({"at": clock(event["at"]), "minute": event["at"], "orders": len(books.orders), "expected": round(expected, 1), "known late": known, "urgent": urgent, "backlog": queue.backlog, "queue late": round(queue.late, 1),
                        "world": round(queue.world, 2), "late price": round(fleet.late_price(queue) / 100), "ends late": sum(1 for o in books.orders if ended_late(o))})
    return out


def main() -> None:
    tag, seed = sys.argv[1], sys.argv[2]
    policy = FleetPolicy(**json.loads(sys.argv[3])) if len(sys.argv) > 3 else FleetPolicy(on_time=0.96, early_look=6)
    run = next(run for run in runs(tag) if run["seed"] == seed)
    rows = trace(run, policy)
    print(f"{tag} {seed}: {run['score']['wonOrders']} orders, {run['score']['onTimeShare']:.1%} on time")
    print("  ".join(f"{name:>10}" for name in rows[0]))
    for row in rows:
        print("  ".join(f"{str(value):>10}" for value in row.values()))


if __name__ == "__main__":
    main()
