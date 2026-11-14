"""A rehearsal of the final on a practice world: a pacer moves the clock as the final does, and the real
live loop (dispatch.run.live) plays it through the stream and `act`, with the trouble we inject.

    python -m tools.rehearse --tag live-r1 --seeds quick --speed 4
    python -m tools.rehearse --tag live-lag --seeds halal-01 --speed 2 --lag 1500 --trouble kill:3,dead:2,cut:2,fail:2 --down 18

Trouble, each at random working minutes: `kill` the desk dies and a new one starts `--down` real seconds later;
`dead` the stream goes silent without an error; `cut` the stream's socket is closed; `fail` a request gets no answer.
Every run is saved like a harness run, with the rehearsal's own numbers, and compared with `--baseline`."""
from __future__ import annotations

import argparse
import contextlib
import gzip
import json
import os
import random
import socket
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import spread.stream
from spread.client import Client, SpreadError, Unreachable

from dispatch import run
from dispatch.atlas import DAY, HOUR, Atlas, clock
from dispatch.desk import Desk, Policy
from tools.harness import RUNS, SEEDS, Slot, create, summarise


class Killed(BaseException):
    """The desk process dies here."""


def pace(minute: int) -> float:
    """Real seconds that a world hour takes in the final (API.md)."""
    day, hour = minute // DAY, minute % DAY // HOUR
    if not 6 <= hour < 22 or day % 7 == 6 or day > 7:
        return 3
    return {5: 6, 7: 9}.get(day, 18)


class Pacer(threading.Thread):
    """Moves a practice world's clock by the wall clock, `speed` times as fast as the final's."""

    def __init__(self, world, speed: float, now: int, ends_at: int):
        super().__init__(daemon=True)
        self.world, self.speed, self.now, self.ends_at = world, speed, now, ends_at

    def run(self) -> None:
        minute, last = float(self.now), time.monotonic()
        while self.now < self.ends_at:
            time.sleep(0.05)
            wall = time.monotonic()
            minute, last = minute + (wall - last) * self.speed * HOUR / pace(int(minute)), wall
            if int(minute) > self.now:
                try:
                    self.now = self.world.advance(to=min(int(minute), self.ends_at))["now"]
                except SpreadError as error:
                    print(f"pacer: {error}", flush=True)


class Stage:
    """A practice world dressed as the final, for `dispatch.run.live`: `final()` names it and reads the pacer's clock,
    and every call goes through the trouble we inject. It times each quote from the event to the world's answer."""

    def __init__(self, client: Client, world, pacer: Pacer, lag: float, trouble: list[tuple[int, str]]):
        self.client, self.real, self.pacer, self.lag, self.trouble = client, world, pacer, lag, sorted(trouble)
        self.id = world.id
        self.asked: dict[str, float] = {}  # request id -> when its event reached us
        self.answered: dict[str, float] = {}  # request id -> seconds from the event to the world's answer to our quote
        self.batches: list[tuple[float, int]] = []  # (when, actions) of each batch sent
        self.count = {"joins": 0, "streams": 0, "refused": 0}
        self.tokens, self.refilled = 50.0, time.monotonic()  # the final's bucket for actions: 20 a second, 50 at most
        self.sockets: list[socket.socket] = []
        dial = socket.create_connection
        spread.stream.socket.create_connection = lambda *a, **k: self.sockets.append(dial(*a, **k)) or self.sockets[-1]

    def due(self, *kinds: str) -> bool:
        """True when the next trouble is of one of these kinds and its minute has come."""
        if self.trouble and self.trouble[0][0] <= self.pacer.now and self.trouble[0][1] in kinds:
            print(f"{clock(self.pacer.now)}  -- trouble: {self.trouble.pop(0)[1]}", flush=True)
            return True
        return False

    def late(self) -> None:
        if self.due("kill"):
            raise Killed
        time.sleep(self.lag)

    # the client
    def map(self):
        return self.client.map()

    def final(self):
        self.late()
        return {"worldId": self.id, "startsAt": "", "now": self.pacer.now}

    def world(self, world_id: str) -> "Stage":
        return self

    # the world
    def snapshot(self):
        self.late()
        return {**self.real.snapshot(), "endsAt": self.pacer.ends_at}

    def roster(self):
        self.late()
        return self.real.roster()

    def score(self):
        self.late()
        return self.real.score()

    def events(self, after: int = -1):
        self.late()
        self.count["joins"] += after < 0
        return self.real.events(after)

    def act(self, actions):
        self.late()
        if self.due("fail"):  # half of the lost requests reach the world, half do not
            if random.random() < 0.5:
                self.real.act(actions)
            raise Unreachable(0, "rehearsal: the request got no answer")
        wall = time.monotonic()
        self.tokens, self.refilled = min(50.0, self.tokens + (wall - self.refilled) * 20), wall
        time.sleep(max(0.0, (len(actions) - self.tokens) / 20))
        self.tokens -= len(actions)
        results = self.real.act(actions)
        wall = time.monotonic()
        self.batches.append((wall, len(actions)))
        for action, result in zip(actions, results):
            self.count["refused"] += not result["ok"]
            if action["type"] == "quote" and result["ok"] and action["requestId"] in self.asked:
                self.answered.setdefault(action["requestId"], wall - self.asked[action["requestId"]])
        return results

    def stream(self, after=None, idle=None):
        self.count["streams"] += 1
        self.late()
        for event in self.real.stream(after=after, idle=idle):
            if self.due("kill"):
                raise Killed
            if self.due("cut"):
                self.sockets[-1].shutdown(socket.SHUT_RDWR)
            if self.due("dead"):
                while True:  # no error and no event, until the loop gives this stream up
                    time.sleep(idle or 1)
                    yield None
            if event is not None and event["kind"] == "price_request":
                self.asked.setdefault(event["request"]["id"], time.monotonic())
            yield event


def rehearse(tag: str, seed: str, level: int, overrides: dict, speed: float, lag: float, trouble: dict[str, int], down: float, until: int) -> dict:
    folder = os.path.join(RUNS, tag)
    os.makedirs(folder, exist_ok=True)
    os.chdir(folder)  # the desk keeps its journal where it runs
    sys.stdout = sys.stderr = open(f"{seed}.log", "w", buffering=1)
    client, rng = Client(), random.Random(f"{tag}:{seed}")
    with Slot() as slot:
        world = create(client, level, seed)
        slot.hold(world.id)
        started = time.time()
        try:
            ends_at = min(until, world.snapshot()["endsAt"])
            start = world.advance(to=7 * HOUR)["now"]  # nothing happens before Monday 08:00
            working = [day * DAY + minute for day in range(5) for minute in range(9 * HOUR, 18 * HOUR) if day * DAY + minute < ends_at]
            schedule = [(rng.choice(working), kind) for kind, times in trouble.items() for _ in range(times)]
            pacer = Pacer(Client().world(world.id), speed, start, ends_at)
            stage = Stage(client, world, pacer, lag, schedule)
            pacer.start()
            downtime = 0.0
            while True:
                try:
                    run.live(stage, overrides)
                    break
                except Killed:
                    print(f"{clock(pacer.now)}  -- the desk is dead for {down:.0f} s", flush=True)
                    downtime += down
                    time.sleep(down)
            pacer.join()
            if world.snapshot()["now"] < world.snapshot()["endsAt"]:  # only a part of the week was rehearsed: the practice loop plays the rest at once
                desk = Desk(Atlas(client.map()), world.roster(), Policy.of(overrides, seed=world.id), journal=f"journal-{world.id}.jsonl")
                desk.rejoin(world.snapshot(), world.events())
                run.play_practice(world, desk)
            score = world.score()
        except BaseException:
            with contextlib.suppress(SpreadError):
                world.delete()
            raise
    events, roster, reveal = world.events(), world.roster(), world.reveal()
    desk = Desk(Atlas(client.map()), roster, Policy.of(overrides, seed=world.id), journal=f"journal-{world.id}.jsonl")
    desk.rejoin(world.snapshot(), events)  # the books of the week, from the log and the journal
    summary = summarise(seed, world.id, score, desk, events, time.time() - started)
    took = sorted(stage.answered.values())
    peak = max((sum(n for at, n in stage.batches if wall <= at < wall + 1) for wall, _ in stage.batches), default=0)
    summary.update({
        "speed": speed, "lag": lag, "trouble": trouble, "down": downtime,
        "unquoted": sum(1 for r in reveal["requests"] if r["outcome"] == "unquoted" and r["request"]["arrivedAt"] < ends_at),
        "quoted": len(took), "quoteP50": percentile(took, 0.5), "quoteP99": percentile(took, 0.99), "quoteMax": took[-1] if took else 0.0,
        "peak": peak, "batches": len(stage.batches), "actions": sum(n for _, n in stage.batches), **stage.count,
    })
    with gzip.open(f"{seed}.json.gz", "wt") as file:
        json.dump({"seed": seed, "level": level, "worldId": world.id, "policy": overrides, "summary": summary, "score": score, "quotes": desk.books.quotes,
                   "roster": roster, "events": events, "gigs": world.snapshot()["gigs"], "reveal": reveal}, file)
    return summary


def percentile(values: list[float], share: float) -> float:
    return values[min(len(values) - 1, int(len(values) * share))] if values else 0.0


def line(s: dict, base: dict) -> str:
    against = f"practice €{base['margin']:>9,.0f} {base['onTime']:6.1%}" if base else "practice        n/a"
    return (f"{s['seed']:<10} margin €{s['margin']:>9,.0f}  on time {s['onTime']:6.1%}  won {s['won']:>4}/{s['requests']:<4}  | {against}  | "
            f"unquoted {s['unquoted']:>3}  refused {s['refused']:>3}  quote ms p50 {s['quoteP50'] * 1000:>4.0f} p99 {s['quoteP99'] * 1000:>4.0f} max {s['quoteMax'] * 1000:>5.0f}  "
            f"peak {s['peak']:>2} actions/s  joins {s['joins']}  streams {s['streams']}  {s['seconds']}s")


def baseline(tag: str, seed: str) -> dict:
    path = os.path.join(RUNS, tag, f"{seed}.json.gz")
    if not os.path.exists(path):
        return {}
    with gzip.open(path, "rt") as file:
        return json.load(file)["summary"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--tag", required=True)
    parser.add_argument("--seeds", default="halal-01", help="a named set (tune, hold, wide, quick) or seeds separated by commas")
    parser.add_argument("--level", type=int, default=8)
    parser.add_argument("--policy", default="{}")
    parser.add_argument("--speed", type=float, default=1.0, help="1 is the final's clock: 18 real seconds per weekday hour")
    parser.add_argument("--lag", type=float, default=0, help="milliseconds added to every request")
    parser.add_argument("--trouble", default="", help="for example kill:3,dead:2,cut:2,fail:2")
    parser.add_argument("--down", type=float, default=18, help="real seconds a killed desk stays down")
    parser.add_argument("--until", type=int, default=10 ** 9, help="rehearse to this world minute; the rest of the week plays at once")
    parser.add_argument("--baseline", default="live-practice", help="the tag of the practice-loop runs to compare with")
    parser.add_argument("--workers", type=int, default=2)
    args = parser.parse_args()
    seeds = SEEDS.get(args.seeds) or args.seeds.split(",")
    trouble = {kind: int(times) for kind, times in (item.split(":") for item in args.trouble.split(",") if item)}
    results = []
    with ProcessPoolExecutor(max_workers=min(args.workers, len(seeds))) as pool:
        futures = {pool.submit(rehearse, args.tag, seed, args.level, json.loads(args.policy), args.speed, args.lag / 1000, trouble, args.down, args.until): seed for seed in seeds}
        for future in as_completed(futures):
            try:
                results.append(future.result())
                print(line(results[-1], baseline(args.baseline, futures[future])), flush=True)
            except Exception as error:
                print(f"{futures[future]:<10} FAILED: {type(error).__name__}: {error}", flush=True)
    if results:
        with open(os.path.join(RUNS, "log.jsonl"), "a") as file:
            file.write(json.dumps({"tag": args.tag, "policy": json.loads(args.policy), "level": args.level, "at": time.strftime("%m-%d %H:%M"), "results": results}) + "\n")


if __name__ == "__main__":
    main()
