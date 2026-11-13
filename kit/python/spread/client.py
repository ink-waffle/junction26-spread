"""The client for the Spread API (HANDBOOK.md, API.md). Answers are plain dicts in the shapes
of `spread.types`."""
from __future__ import annotations

import http.client
import json
import os
import time
from typing import Any, Iterator, Optional, Sequence
from urllib.parse import urlencode, urlsplit

from .stream import websocket
from .types import (
    Action, ActionResult, Advanced, DeskEvent, DeskEventKind, DeskSnapshot, DriverProfile, Final, PracticeBoard, Reveal,
    Score, WorldMap, WorldSummary,
)

ACTIONS_PER_CALL = 50


class SpreadError(Exception):
    """A request that failed. `status` is the HTTP status, 0 when the server did not answer;
    `field` names the part of the body that did not parse."""

    def __init__(self, status: int, error: str, field: Optional[str] = None):
        detail = ", ".join(([f"HTTP {status}"] if status else []) + ([f"field {field}"] if field else []))
        super().__init__(error + (f" ({detail})" if detail else ""))
        self.status, self.error, self.field = status, error, field


class Unreachable(SpreadError):
    """The server did not answer: it is down or restarting, or SPREAD_URL is wrong."""


def check_whole(value: Any, field: str = "") -> None:
    """Stops a body or query that holds a number with a fraction. Every number that the API takes is a
    whole number: minutes, cents, levels and legs. The server refuses others with 400."""
    if isinstance(value, float) and not value.is_integer():
        raise SpreadError(0, f"{value} is not a whole number. Minutes and cents are whole numbers: round them before you send", field or None)
    items = enumerate(value) if isinstance(value, (list, tuple)) else value.items() if isinstance(value, dict) else ()
    for key, item in items:
        check_whole(item, f"{field}[{key}]" if isinstance(value, (list, tuple)) else f"{field}.{key}" if field else str(key))


def failure(status: int, body: bytes, path: str) -> SpreadError:
    """The error for an answer other than 2xx, with what to do where the server's text does not say it."""
    if status in (502, 503, 504):  # while the server restarts, the proxy in front of it answers for it
        return Unreachable(0, f"The server is restarting (HTTP {status})")
    try:
        answer = json.loads(body)
    except ValueError:
        answer = None
    if not isinstance(answer, dict):
        answer = {"error": body.decode("utf-8", "replace").strip()[:200] or "no message"}
    error = answer.get("error", "no message")
    if status == 401:
        error = "The server does not accept this key. Set SPREAD_KEY to your team key"
    elif status == 409 and (path == "/v1/worlds" or path.endswith("/fork")) and "delete" in error:
        # Only where the server says to delete a world: a full set of practice slots, or a ranking run
        # that has not ended. A team that has played a ranking round's worlds waits for the next round.
        error += ". client.worlds() lists them; client.world(world_id).delete() deletes one"
    return SpreadError(status, error, answer.get("field"))


class Bucket:
    """The client's copy of one of the server's request buckets, from the RateLimit headers of
    the last answer. The client waits until the bucket holds the tokens for a request, so a system
    that runs at the limit gets almost no 429 answers."""

    def __init__(self, name: str, headers: Any):
        self.name = name
        self.per_second = float(headers["RateLimit-Limit"])
        next_token = int(headers["RateLimit-Reset"]) / 1000
        # The headers give whole tokens; the wait for the next token gives the fraction.
        self.tokens = int(headers["RateLimit-Remaining"]) + (1 - next_token * self.per_second if next_token else 0)
        self.at = time.monotonic()

    def take(self, actions: int) -> float:
        """Takes the tokens for a request that carries `actions` actions. Returns the seconds to
        wait until the bucket holds them. A final world takes one token for each action."""
        cost = max(1, actions) if self.name == "final-actions" else 1
        now = time.monotonic()
        tokens = self.tokens + (now - self.at) * self.per_second
        delay = max(0.0, (cost - tokens) / self.per_second)
        self.tokens, self.at = tokens + delay * self.per_second - cost, now + delay
        return delay


class Client:
    """One team key on one server. `url` and `key` default to the SPREAD_URL and SPREAD_KEY variables."""

    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        self.url = (url or os.environ.get("SPREAD_URL") or "http://127.0.0.1:8080").rstrip("/")
        self.key = key or os.environ.get("SPREAD_KEY") or ""
        self._parts = urlsplit(self.url)
        if self._parts.scheme not in ("http", "https") or not self._parts.netloc:
            raise SpreadError(0, f'SPREAD_URL is "{self.url}". Set it to the server address, for example http://127.0.0.1:8080')
        if not self.key:
            raise SpreadError(0, "SPREAD_KEY is not set. Set it to your team key")
        self._connection: Optional[http.client.HTTPConnection] = None
        self._buckets: dict[str, Bucket] = {}  # bucket name -> the client's copy
        self._bucket_of: dict[str, str] = {}  # "METHOD /path" -> the bucket that the server charges

    def worlds(self) -> list[WorldSummary]:
        return self.call("GET", "/v1/worlds")

    def create(self, level: int = 8, seed: Optional[str] = None, board: bool = False) -> World:
        """A new practice world. It stands still until you call `advance`. With `board=True`, your
        next ranking run at the level, on a seed that the server chooses."""
        body: dict = {"level": level, "board": board}
        if seed is not None:
            body["seed"] = seed
        return World(self, self.call("POST", "/v1/worlds", body)["worldId"])

    def board(self, level: int = 8) -> PracticeBoard:
        """The practice rankings of a level: the current ranking round and the previous one."""
        return self.call("GET", f"/v1/leaderboards/practice?level={level}")

    def world(self, world_id: str) -> World:
        return World(self, world_id)

    def map(self) -> WorldMap:
        """The places, and the road km and minutes between every pair."""
        return self.call("GET", "/v1/map")

    def final(self) -> Final:
        """Your copy of the final world: `worldId`, `startsAt` (wall clock) and `now`. 404 before one is scheduled."""
        return self.call("GET", "/v1/final")

    def call(self, method: str, path: str, body: Any = None, actions: int = 0) -> Any:
        """One request. Waits until the server's bucket for the request has the tokens for it, and
        waits out 429 answers for the time the server names. `actions` is the number of actions
        that the request carries."""
        route = f"{method} {path.split('?')[0]}"
        check_whole(body)
        payload = None if body is None else json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"}
        while True:
            bucket = self._buckets.get(self._bucket_of.get(route, ""))
            time.sleep(bucket.take(actions) if bucket else 0)
            status, answer, data = self._send(method, path, payload, headers)
            policy = answer.get("RateLimit-Policy")
            if policy:
                name = policy.split(";")[0].strip('"')
                self._bucket_of[route], self._buckets[name] = name, Bucket(name, answer)
            if status == 429:
                time.sleep(int(answer.get("Retry-After") or 100) / 1000)
            elif status >= 300:
                raise failure(status, data, path.split("?")[0])
            else:
                return json.loads(data) if data else None

    def _send(self, method: str, path: str, payload: Optional[bytes], headers: dict):
        # One kept-alive connection. When the server closed it while it was idle, the request
        # never arrived, so it is safe to send it again on a new connection.
        while True:
            reused = self._connection is not None
            if self._connection is None:
                kind = http.client.HTTPSConnection if self._parts.scheme == "https" else http.client.HTTPConnection
                # A request lost on the network never gets an answer. After 20 seconds without a byte
                # from the server, it counts as unreachable, and a final desk rebuilds and goes on.
                self._connection = kind(self._parts.netloc, timeout=20)
            try:
                self._connection.request(method, self._parts.path + path, payload, headers)
                response = self._connection.getresponse()
                return response.status, response.headers, response.read()
            except BaseException as error:
                self._connection.close()
                self._connection = None
                if reused and isinstance(error, (ConnectionResetError, BrokenPipeError)):
                    continue
                # An answer that breaks off after its first bytes comes from a server that stopped.
                if isinstance(error, (OSError, http.client.HTTPException)):
                    raise Unreachable(0, f"Cannot reach {self.url}: {error}. Check SPREAD_URL, and that the server runs") from error
                raise


class World:
    """One world of the team: a practice world, a fork, or the team's copy of the final."""

    def __init__(self, client: Client, world_id: str):
        self.client, self.id = client, world_id
        self._last_seq = -1

    def _path(self, tail: str = "", **query: Any) -> str:
        query = {k: v for k, v in query.items() if v is not None}
        check_whole(query)
        return f"/v1/worlds/{self.id}{tail}" + (f"?{urlencode(query)}" if query else "")

    def snapshot(self) -> DeskSnapshot:
        return self.client.call("GET", self._path())

    def act(self, actions: Sequence[Action]) -> list[ActionResult]:
        """Sends actions in batches of 50. Results come back in the order of the actions."""
        results: list[ActionResult] = []
        for i in range(0, len(actions), ACTIONS_PER_CALL):
            batch = list(actions[i : i + ACTIONS_PER_CALL])
            results += self.client.call("POST", self._path("/actions"), batch, actions=len(batch))
        return results

    def advance(self, to: Optional[int] = None, by: Optional[int] = None, until: Optional[Sequence[DeskEventKind]] = None,
                max: Optional[int] = None, actions: Sequence[Action] = ()) -> Advanced:
        """Practice worlds only. Applies `actions` at the current minute, then moves the clock
        `to` a minute, `by` minutes, or `until` the first event of one of the kinds, but not
        past `max`. One request does both. Returns the minute reached, every event since the
        last advance without repeats, and the `results` of the actions in their order."""
        if until is not None:
            body: dict = {"untilEvent": list(until), "max": max}
        else:
            body = {"to": to} if to is not None else {"by": by}
        # A request carries at most 50 actions. The ones before the last 50 go first, in batches.
        early, last = actions[:-ACTIONS_PER_CALL], actions[-ACTIONS_PER_CALL:]
        results = self.act(early)
        if last:
            body["actions"] = list(last)
        step: Advanced = self.client.call("POST", self._path("/advance"), body)
        events = [e for e in step["events"] if e["seq"] > self._last_seq]
        if events:
            self._last_seq = events[-1]["seq"]
        return {"now": step["now"], "events": events, "results": results + step.get("results", [])}

    def events(self, after: int = -1, limit: Optional[int] = None) -> list[DeskEvent]:
        """Events with a sequence number above `after`, oldest first."""
        return self.client.call("GET", self._path("/events", after=after, limit=limit))

    def stream(self, after: Optional[int] = None, idle: Optional[float] = None) -> Iterator[Optional[DeskEvent]]:
        """Events as they happen, over the WebSocket. With `after`, first every event above that
        sequence number. Reconnects by itself and misses nothing. With `idle`, yields None after
        that many seconds without an event, so a loop can check the clock."""
        last, failures = after, 0
        while True:
            try:
                for event in websocket(self.client.url, self._path("/stream", after=last), self.client.key, idle):
                    failures = 0
                    if event is not None:
                        last = event["seq"]
                    yield event
                return  # the world was deleted
            except (OSError, Unreachable) as error:  # also the 502 of a server that restarts
                failures += 1
                if failures == 60:
                    raise Unreachable(0, f"The stream of world {self.id} failed 60 times in a row: {error}") from error
            time.sleep(1)

    def roster(self) -> list[DriverProfile]:
        """Every driver's public profile. It can be up to 5 seconds old while the world moves."""
        return self.client.call("GET", self._path("/drivers"))

    def fork(self) -> World:
        """A copy at the same minute with the same future draws. Practice worlds only."""
        return World(self.client, self.client.call("POST", self._path("/fork"))["worldId"])

    def score(self) -> Score:
        return self.client.call("GET", self._path("/score"))

    def reveal(self) -> Reveal:
        """After the world has ended: your quotes and their outcomes, the truth of the cars you won, and the views of your gigs."""
        return self.client.call("GET", self._path("/reveal"))

    def delete(self) -> None:
        """Deletes a practice world and frees its slot."""
        self.client.call("DELETE", self._path())
