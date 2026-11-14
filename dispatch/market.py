"""The dealer side: learns from every yes and no what each dealer will pay, and quotes the price that earns most."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Optional

from spread.types import DeliveryOption, PriceRequest

from .atlas import DAY
from .books import Books
from .fleet import Fleet
from . import prior

DECLINE = 10.0  # times the list price: a quote that never wins, and costs no goodwill
STEPS = [i / 100 for i in range(80, 351)]  # the prices we consider, as multiples of the list price
FULL_TRUST, DEALERS = 25, 40  # a dealer counts at most 25 orders on time (RULES.md); a world has about 40 dealers


@dataclass
class MarketPolicy:
    reserve: float = 0.3  # the least a booking must earn above its cost, as a share of that cost
    orders: Optional[float] = None  # the orders a day that drivers can carry: when we expect to win more, a booking must earn more
    pace: float = 0.02  # how fast it then rises: its relative step per quote, per unit of chance above the target
    invest: float = 0.0  # research: how much of the future worth of a dealer's trust the price counts (0 none, 1 all)
    slope: float = prior.SLOPE  # how fast a dealer's yes fades: logits per unit of log price (10% dearer is about one logit)
    speed: float = prior.SPEED  # log price a dealer gives up for each faster option we do not offer
    trust: float = prior.TRUST  # log price a dealer adds for each order we delivered to it on time
    level: float = prior.LEVEL  # the log price level of an average world
    spread: dict = field(default_factory=lambda: dict(prior.SPREAD))  # the parts of a level, and how far each strays from its prior (sd)
    explore: Optional[tuple[float, float]] = None  # research: draw each multiple from this range
    options: str = "best"  # the options we consider: best (all, and we offer the one that earns most); research: first, last, random
    seed: str = ""


class Market:
    """Believes that a dealer says yes with a chance that is logistic in log price, around a level that is a sum of parts:
    the world, the day, the dealer, the pickup place and the delivery place. Each answer moves every part it touched (one Kalman step)."""

    def __init__(self, policy: MarketPolicy, books: Books, fleet: Fleet, places: Optional[dict] = None):
        self.policy, self.books, self.fleet = policy, books, fleet
        self.places = prior.PLACES if places is None else places
        self.beliefs: dict[tuple, tuple[float, float]] = {}  # part -> mean and variance of its share of the log level
        self.booking = policy.reserve  # what a booking must earn now: the shadow price of a driver, as a share of the order's cost

    def quote(self, request: PriceRequest) -> dict[str, int]:
        """A price in cents for the one option, and at the price, with the highest expected margin over what the booking is worth."""
        policy, options = self.policy, request["options"]
        if policy.explore:
            return self.research(request)
        worth = 1 + policy.invest * policy.trust * self.lifted(request["dealerId"])  # a euro from a dealer whose trust still grows is worth more
        offers = {}  # option -> the highest expected gain, and its price
        for option in {"first": options[:1], "last": options[-1:]}.get(policy.options, options):
            cost = self.fleet.cost(request, option)
            if cost is not None:
                floor = cost * (1 + self.booking)
                prices = [int(option["listPriceCents"] * step / 100 + 0.5) * 100 for step in STEPS]
                offers[option["kind"]] = max(((price * worth - floor) * self.chance(request, option, price), price) for price in prices)
        offers = {kind: price for kind, (gain, price) in offers.items() if gain > 0 and (policy.options == "each" or gain == max(offers.values())[0])}
        return offers or {options[0]["kind"]: int(options[0]["listPriceCents"] * DECLINE)}

    def lifted(self, dealer: str) -> float:
        """How many of our coming orders one more on-time order to this dealer will lift by a trust step: those until its trust is full or the week ends."""
        books = self.books
        share = (sum(1 for r in books.requests.values() if r["dealerId"] == dealer) + 1) / (len(books.requests) + DEALERS)
        rate = (sum(1 for won in books.outcomes.values() if won) + 3) / (len(books.outcomes) + 10)
        left = prior.REQUESTS * max(0.0, 1 - (books.now // DAY * 600 + min(600, max(0, books.now % DAY - 480))) / 3000)
        coming = sum(1 for state in books.orders.values() if state.request["dealerId"] == dealer and state.undelivered() and state.id not in books.refunded)
        return max(0.0, min(FULL_TRUST - books.on_time[dealer] - coming, share * left * rate))

    def parts(self, request: PriceRequest) -> list[tuple]:
        """The parts of the level that this request touches, of those the policy gives a spread."""
        leg, day, dealer = request["legs"][0], request["arrivedAt"] // DAY, request["dealerId"]
        pickup, delivery = leg["pickup"]["placeId"], leg["delivery"]["placeId"]
        keys = {"world": (), "day": (day,), "dealer": (dealer,), "from": (pickup,), "to": (delivery,),
                "from today": (pickup, day), "to today": (delivery, day), "dealer today": (dealer, day)}
        return [(name, *keys[name]) for name in self.policy.spread]

    def belief(self, part: tuple) -> tuple[float, float]:
        if part not in self.beliefs:
            mean = self.policy.level if part[0] == "world" else self.places.get(part[0], {}).get(part[1], 0.0)
            self.beliefs[part] = (mean, self.policy.spread[part[0]] ** 2)
        return self.beliefs[part]

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
        if self.policy.orders:  # dual ascent on the drivers' capacity: dearer while we expect more orders a day than they carry
            excess = self.chance(request, option, prices[option["kind"]]) - self.policy.orders / (prior.REQUESTS / 5)
            self.booking = max(self.policy.reserve, self.booking * math.exp(self.policy.pace * excess))
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
        chosen = {"first": options[:1], "last": options[-1:], "best": options}.get(policy.options) or rng.choice([options[:1], options[-1:], options])
        prices = {o["kind"]: int(o["listPriceCents"] * rng.uniform(*policy.explore) / 100 + 0.5) * 100 for o in chosen if self.fleet.cost(request, o) is not None}
        return prices or {options[0]["kind"]: int(options[0]["listPriceCents"] * DECLINE)}
