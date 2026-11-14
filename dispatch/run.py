"""Plays a world with the desk: a practice world turn by turn, or the final from the live stream. Only the transport differs."""
from __future__ import annotations

import argparse
import fcntl
import http.client
import json
import sys
import time
import traceback
from typing import Callable, Iterator, Optional

from spread.client import ACTIONS_PER_CALL, Client, SpreadError, Unreachable, World
from spread.types import Action, ActionResult, DeskEvent, DeskEventKind, Score

from .atlas import DAY, HOUR, Atlas, clock
from .desk import Desk, Policy

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
# The events that can need an action. Everything else arrives with the next of these.
WAKE_ON: list[DeskEventKind] = ["price_request", "order_won", "order_changed", "order_cancelled", "visit_failed", "gig_expired", "deadline_close",
                                "gig_dropped", "no_show", "offer_answered"]
GAP = 0.02  # seconds of silence that end a burst of events
QUIET = 1.0  # seconds without an event before the live loop reads the clock
SILENCE = 15  # world minutes the clock may move without an event before the live loop reads the log: a stream can die without a word
PATIENCE = 5  # seconds without a byte before a request of the final counts as lost: the kit waits 20, more than a world hour


class Impatient(Client):
    """The kit's client with the final's patience."""

    def _send(self, method, path, payload, headers):
        if self._connection is None:  # else the kit opens it with its own 20 seconds
            kind = http.client.HTTPSConnection if self._parts.scheme == "https" else http.client.HTTPConnection
            self._connection = kind(self._parts.netloc, timeout=PATIENCE)
        return super()._send(method, path, payload, headers)


def play_practice(world: World, desk: Desk, on_day: Optional[Callable[[int, Score], None]] = None, until: int = 10 ** 9) -> None:
    """One request a turn: the advance carries the outbox, then moves the clock to the next event that can need an action, or to the next alarm.
    With `until`, returns after the first turn that ends at that minute or later, the outbox unsent."""
    snapshot = world.snapshot()
    desk.books.now, ends_at = snapshot["now"], snapshot["endsAt"]
    while desk.books.now < min(until, ends_at):
        day, actions = desk.books.now // DAY, desk.take()
        step = world.advance(until=WAKE_ON, max=min(ends_at, (day + 1) * DAY, max(desk.alarm(), desk.books.now)), actions=actions)
        desk.sent(actions, step["results"])
        desk.step(step["events"], step["now"])
        if on_day and desk.books.now // DAY > day:
            on_day(day, world.score())


def play_live(world: World, desk: Desk, now: Callable[[], int], on_day: Optional[Callable[[int, Score], None]] = None) -> None:
    """A world whose clock runs by itself: a new desk rejoins, then answers every burst of events with one batch of actions."""
    history = world.events()
    snapshot = world.snapshot()
    ends_at = snapshot["endsAt"]
    desk.rejoin(snapshot, history)
    books = desk.books
    print(f"{clock(books.now)}  joined after {len(history)} events: {len(books.orders)} orders, {len(books.quotes)} of {len(books.requests)} requests quoted, "
          f"{len(desk.outbox)} actions to send", flush=True)
    send(world, desk)
    stream, heard, slowest = world.stream(after=books.seq, idle=GAP), books.now, 0.0
    while books.now < ends_at:
        hour = books.now // HOUR
        burst = waiting(stream, QUIET if desk.alarm() > ends_at else QUIET / 4)  # an alarm is due at a minute: look at the clock more often
        started = time.monotonic()
        minute = burst[-1]["at"] if burst else now()
        if not burst and minute - heard >= SILENCE:  # the clock moved and the stream said nothing
            heard, burst = minute, waiting(stream, 0)  # unless it spoke while we read the clock
            if not burst:  # then the log knows: with news in it the stream is dead, and we open a new one
                burst = world.events(after=books.seq)
                if burst:
                    stream.close()
                    stream = world.stream(after=burst[-1]["seq"], idle=GAP)
        heard = burst[-1]["at"] if burst else heard
        turn(desk, burst, minute)
        send(world, desk)
        slowest = max(slowest, time.monotonic() - started)
        if books.now // HOUR > hour:
            waiting_cars = sum(1 for state in books.orders.values() if state.unposted() or any(books.gigs[g].status == "open" for g in state.gig_of.values()))
            print(f"{clock(books.now)}  margin €{books.margin() / 100:>10,.2f}  {len(books.orders):>4} orders  {waiting_cars:>3} without a driver  "
                  f"{len(books.quotes):>4} of {len(books.requests):>4} requests quoted  slowest turn {slowest * 1000:.0f} ms", flush=True)
            slowest = 0.0
            if on_day and books.now // DAY > hour // 24:
                on_day(hour // 24, world.score())


def waiting(stream: Iterator[Optional[DeskEvent]], quiet: float) -> list[DeskEvent]:
    """Every event that is already waiting on the stream, so one batch answers them all; [] after `quiet` seconds without one."""
    burst, since = [], time.monotonic()
    for event in stream:  # None after GAP seconds without an event
        if event is not None:
            burst.append(event)
        elif burst or time.monotonic() - since >= quiet:
            break
    return burst


def turn(desk: Desk, burst: list[DeskEvent], minute: int) -> None:
    """A turn of the final. An event that the desk cannot answer is logged and passed over: the turn starts again after it."""
    while True:
        seen = desk.books.seq
        try:
            return desk.step(burst, minute)
        except Exception:
            traceback.print_exc()
            if desk.books.seq == seen:  # no event got us here: the plan itself failed, and the next turn tries it again
                return


def send(world: World, desk: Desk) -> None:
    """Sends the outbox, quotes first, and gives the desk the world's answers. A refused post can need one more round."""
    for _ in range(3):
        actions = desk.take()
        if not actions:
            return
        desk.sent(actions, act(world, actions))
        turn(desk, [], desk.books.now)


def act(world: World, actions: list[Action]) -> list[ActionResult]:
    """One request for a turn's actions, as long as they are 50 at most: on a slow network every request costs a quote its time.
    A batch that the server cannot read goes again one action at a time, so a bad action costs only itself."""
    results: list[ActionResult] = []
    for i in range(0, len(actions), ACTIONS_PER_CALL):
        batch = actions[i:i + ACTIONS_PER_CALL]
        try:
            results += world.act(batch)
        except Unreachable:
            raise
        except SpreadError as error:
            results += [{"ok": False, "reason": str(error)}] if len(batch) == 1 else [result for action in batch for result in act(world, [action])]
    return results


def next_final(client: Client) -> World:
    """Our copy of the final that is set or runs now. Waits while none is set, and while the last one has ended."""
    said = False
    while True:
        try:
            world = client.world(client.final()["worldId"])
            snapshot = world.snapshot()
            if snapshot["now"] < snapshot["endsAt"]:
                return world
        except SpreadError as error:
            if isinstance(error, Unreachable) or error.status != 404:
                raise
        if not said:
            print("No final is set. Waiting for it.", flush=True)
            said = True
        time.sleep(10)


def live(client: Client, overrides: dict, world_id: Optional[str] = None) -> Score:
    """Plays the final, or a world whose clock someone else moves, to its end. Every failure leads to the same place: a new desk that rejoins."""
    atlas, world, wait, failed_at = None, None, 0.5, 0.0
    while True:
        try:
            atlas = atlas or Atlas(client.map())
            world = world or (client.world(world_id) if world_id else next_final(client))
            now = (lambda: world.snapshot()["now"]) if world_id else (lambda: client.final()["now"])
            desk = Desk(atlas, world.roster(), Policy.of(overrides, seed=world.id), journal=f"journal-{world.id}.jsonl", verbose=True)
            desk.careful = True
            print(f"World {world.id}. Ctrl-C stops the desk, not the world: start it again and it rejoins.", flush=True)
            play_live(world, desk, now, lambda day, score: report(WEEKDAYS[day % 7], score))
            return world.score()
        except Exception as error:  # the server restarts, the network drops, or we have a bug: the world keeps going, so do we
            if not isinstance(error, Unreachable):
                traceback.print_exc()
            if isinstance(error, SpreadError) and error.status in (403, 404):  # this world is not ours to play any more: ask again which one is
                world = None
            wait = 0.5 if time.monotonic() - failed_at > 60 else min(5.0, wait * 2)
            failed_at = time.monotonic()
            print(f"{error}. A new desk rejoins in {wait:.1f} s.", file=sys.stderr, flush=True)
            time.sleep(wait)


def report(label: str, score: Score) -> None:
    orders = f"{score['wonOrders']:>4} orders  {score['onTimeShare']:6.1%} on time  {score['undeliveredShare']:5.1%} not delivered"
    print(f"{label:<9}  margin €{score['marginCents'] / 100:>11,.2f}  revenue €{score['revenueCents'] / 100:>11,.2f}  {orders}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Plays a Spread world with the desk. Set SPREAD_URL and SPREAD_KEY first.")
    parser.add_argument("--level", type=int, choices=range(1, 9), default=8)
    parser.add_argument("--seed")
    parser.add_argument("--board", action="store_true", help="play the next ranking run at the level")
    parser.add_argument("--final", action="store_true", help="play our copy of the final from the live stream; start it again at any time and it rejoins")
    parser.add_argument("--world", help="with --final: play this world instead of the final (a rehearsal: someone else advances a practice world)")
    parser.add_argument("--policy", default="{}", help='JSON overrides, for example {"market": {"price": 1.4}}')
    args = parser.parse_args()
    if args.final:
        lock = open("journal-desk.lock", "a")  # two desks on one world would both quote and both post
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            sys.exit("Another desk already runs from this folder. Stop it first.")
        try:
            score = live(Impatient(), json.loads(args.policy), args.world)
        except KeyboardInterrupt:
            sys.exit("Stopped. The world keeps running without the desk; start it again with --final.")
    else:
        client = Client()
        world = client.create(level=args.level, seed=args.seed, board=args.board)
        print(f"World {world.id}, level {args.level}.", flush=True)
        desk = Desk(Atlas(client.map()), world.roster(), Policy.of(json.loads(args.policy), seed=args.seed or ""), verbose=True)
        try:
            play_practice(world, desk, lambda day, score: report(WEEKDAYS[day % 7], score))
        except BaseException:
            if not args.board:
                world.delete()
            raise
        score = world.score()
    report("End", score)
    print("Ranked." if score["ranked"] else "Not ranked.")


if __name__ == "__main__":
    main()
