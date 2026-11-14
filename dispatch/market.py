"""The dealer side: learns from every yes and no what each dealer will pay, and quotes the price that earns most."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from spread.types import DeliveryOption, PriceRequest

from . import prior
from .atlas import DAY
from .books import Books
from .fleet import Fleet

DECLINE = 10.0  # times the list price: a quote that never wins, and costs no goodwill
STEPS = [i / 100 for i in range(80, 351)]  # the prices we consider, as multiples of the list price


def euros(cents: float) -> int:
    """Cents rounded to whole euros, as dealers' prices are."""
    return int(cents / 100 + 0.5) * 100


@dataclass
class MarketPolicy:
    slope: float = prior.SLOPE  # how fast a dealer's yes fades: logits per unit of log price (10% dearer is about one logit)
    speed: float = prior.SPEED  # log price a dealer gives up for each faster option we do not offer
    trust: float = prior.TRUST  # log price a dealer adds for each order we delivered to it on time
    level: float = prior.LEVEL  # the log price level of an average world
    spread: dict = field(default_factory=lambda: dict(prior.SPREAD))  # the parts of a level, and how far each strays from its prior (sd)
    options: str = "all"  # all: the option that earns most, and the others at the same margin; research: best (that one alone), first, each, random
    reserve: float = 0.0  # research: a margin every order must earn above the fleet's cost, as a share of it; the cost already prices risk and room
    explore: Optional[tuple[float, float]] = None  # research: draw each multiple from this range
    seed: str = ""


class Market:
    """Believes that a dealer says yes with a chance that is logistic in log price, around a level that is a sum of parts:
    the world, the day, the dealer, the two places, their lane, the pickup place today. Each answer moves every part it touched (one Kalman step)."""

    def __init__(self, policy: MarketPolicy, books: Books, fleet: Fleet, places: Optional[dict] = None):
        self.policy, self.books, self.fleet = policy, books, fleet
        self.places = prior.PLACES if places is None else places
        self.beliefs: dict[tuple, tuple[float, float]] = {}  # part -> mean and variance of its share of the log level

    def quote(self, request: PriceRequest) -> dict[str, int]:
        """A price in cents for each option we offer: the option and price with the highest expected margin over the fleet's cost."""
        policy, options = self.policy, request["options"]
        if policy.explore:
            return self.research(request)
        floors, offers = {}, {}  # per option: what it must earn, and its highest expected gain with the price that gives it
        for option in options[:1] if policy.options == "first" else options:
            cost = self.fleet.cost(request, option)
            if cost is not None:
                kind, prices = option["kind"], (euros(option["listPriceCents"] * step) for step in STEPS)
                floors[kind] = cost * (1 + policy.reserve)
                offers[kind] = max(((price - floors[kind]) * self.chance(request, option, price), price) for price in prices)
        best = max(offers, key=offers.get, default=None)
        if best is None or offers[best][0] <= 0:
            return {options[0]["kind"]: int(options[0]["listPriceCents"] * DECLINE)}
        margin = offers[best][1] - floors[best]
        if policy.options == "all":  # the dealer chooses its speed, and we earn the same whichever it takes
            return {kind: euros(floor + margin) for kind, floor in floors.items()}
        if policy.options == "each":
            return {kind: price for kind, (gain, price) in offers.items() if gain > 0}
        return {best: offers[best][1]}

    def parts(self, request: PriceRequest) -> list[tuple]:
        """The parts of the level that this request touches, of those the policy gives a spread."""
        leg, day, dealer = request["legs"][0], request["arrivedAt"] // DAY, request["dealerId"]
        pickup, delivery = leg["pickup"]["placeId"], leg["delivery"]["placeId"]
        keys = {"world": (), "day": (day,), "dealer": (dealer,), "from": (pickup,), "to": (delivery,), "lane": (pickup, delivery),
                "from today": (pickup, day), "to today": (delivery, day), "dealer today": (dealer, day)}
        return [(name, *keys[name]) for name in self.policy.spread]

    def belief(self, part: tuple) -> tuple[float, float]:
        if part in self.beliefs:
            return self.beliefs[part]
        mean = self.policy.level if part[0] == "world" else self.places.get(part[0], {}).get(part[1], 0.0)
        return mean, self.policy.spread[part[0]] ** 2  # a prior is not kept: only what an answer taught is, so a replay of the answers rebuilds it all

    def level(self, request: PriceRequest, option: DeliveryOption) -> tuple[float, float]:
        """Mean and variance of the log multiple of the list price at which this dealer buys this option half the time."""
        policy, beliefs = self.policy, [self.belief(part) for part in self.parts(request)]
        known = policy.trust * self.books.on_time[request["dealerId"]] - policy.speed * request["options"].index(option)
        return known + sum(mean for mean, _ in beliefs), sum(variance for _, variance in beliefs)

    def chance(self, request: PriceRequest, option: DeliveryOption, price: int) -> float:
        """The chance that the dealer buys this option at this price, when it is the only one we offer."""
        mean, variance = self.level(request, option)
        logit = self.policy.slope * (mean - math.log(price / option["listPriceCents"]))
        return 1 / (1 + math.exp(-logit / math.sqrt(1 + math.pi * self.policy.slope ** 2 * variance / 8)))

    def learn(self, request_id: str, won: Optional[str]) -> None:
        """The dealer's answer to our quote: the option it bought from us, or None. A pure function of the ordered history."""
        request, prices = self.books.requests.get(request_id), self.books.quotes.get(request_id)
        if not request or not prices:
            return
        option = self.weighed(request, prices, won)
        slope, (mean, variance) = self.policy.slope, self.level(request, option)
        p = 1 / (1 + math.exp(-slope * (mean - math.log(prices[option["kind"]] / option["listPriceCents"]))))
        weight = slope * slope * p * (1 - p)
        push, shrink = slope * ((won is not None) - p) / (1 + weight * variance), weight / (1 + weight * variance)
        for part in self.parts(request):
            m, v = self.belief(part)
            self.beliefs[part] = (m + v * push, v - v * v * shrink)

    def weighed(self, request: PriceRequest, prices: dict[str, int], won: Optional[str]) -> DeliveryOption:
        """The option of our quote that the dealer set against the competitor: the one it bought, else our best offer in its eyes."""
        offered = [option for option in request["options"] if option["kind"] in prices]
        return next((o for o in offered if o["kind"] == won), None) or max(offered, key=lambda o: self.chance(request, o, prices[o["kind"]]))

    def research(self, request: PriceRequest) -> dict[str, int]:
        """Random multiples on a random subset of the options, to measure dealers."""
        policy, rng, options = self.policy, random.Random(f"{self.policy.seed}:{request['id']}"), request["options"]
        chosen = {"first": options[:1], "best": options}.get(policy.options) or rng.choice([options[:1], options[-1:], options])
        prices = {o["kind"]: euros(o["listPriceCents"] * rng.uniform(*policy.explore)) for o in chosen if self.fleet.cost(request, o) is not None}
        return prices or {options[0]["kind"]: int(options[0]["listPriceCents"] * DECLINE)}
