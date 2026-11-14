"""The vital signs of our world, read from the server alone: is a desk answering? For a desk that runs on another
machine, and before anyone starts a second one: two desks on one world would both quote and both post.

    python -m tools.watch                 # the final that is set or runs now; reads only, never an action
    python -m tools.watch --world w123    # any world of ours

A desk that answers wins orders and posts gigs. During the working hours of a weekday (08:00 to 18:00) a world sends
about a hundred requests an hour, so an hour of them without one win and without one new gig means no desk."""
from __future__ import annotations

import argparse
import time

from spread.client import Client, SpreadError

from dispatch.atlas import DAY, HOUR, clock


def signs(world, events: list[dict]) -> str:
    """One line: the score, how long ago a desk last won an order or posted a gig, and what that says."""
    snapshot, score = world.snapshot(), world.score()
    now = snapshot["now"]
    events += world.events(after=events[-1]["seq"] if events else -1)
    won = max((e["at"] for e in events if e["kind"] == "order_won"), default=None)
    posted = max((gig["postedAt"] for gig in snapshot["gigs"]), default=None)
    asked = sum(1 for e in events if e["kind"] == "price_request" and now - HOUR <= e["request"]["respondBy"] <= now)
    seen = max((at for at in (won, posted) if at is not None), default=None)
    if asked < 20:
        verdict = "few requests in the last hour: no way to tell if a desk answers"
    elif seen is not None and now - seen <= HOUR:
        verdict = "a desk is answering"
    else:
        verdict = "NO DESK IS ANSWERING"
    ago = lambda at: "never" if at is None else f"{now - at} min ago"
    return (f"{clock(now)}  margin €{score['marginCents'] / 100:>10,.2f}  {score['wonOrders']:>4} orders  {score['onTimeShare']:6.1%} on time  "
            f"last win {ago(won)}, last gig {ago(posted)}, {asked} requests closed in the last hour, {len(snapshot['openRequests'])} open  ->  {verdict}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--world", help="a world id; default: the final that is set or runs now")
    parser.add_argument("--every", type=float, default=5, help="seconds between lines; 0 prints one line and stops")
    args = parser.parse_args()
    client, events = Client(), []
    world = client.world(args.world or client.final()["worldId"])
    while True:
        try:
            print(signs(world, events), flush=True)
        except SpreadError as error:
            print(f"cannot read the world: {error}", flush=True)
        if not args.every:
            return
        time.sleep(args.every)


if __name__ == "__main__":
    main()
