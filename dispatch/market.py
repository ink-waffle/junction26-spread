"""The dealer side: learns from every yes and no what each dealer will pay, and quotes the price that earns most."""
from __future__ import annotations

import math
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Optional

from spread.types import DeliveryOption, PriceRequest

from . import prior
from .atlas import DAY, HOUR
from .books import Books
from .fleet import Fleet

DECLINE = 10.0  # times the list price: a quote that never wins, and costs no goodwill
STEPS = [i / 100 for i in range(80, 351)]  # the prices we consider, as multiples of the list price
WAR, OUTAGE = math.log(0.8), math.log(1.3)  # the week's two unannounced events, as the rules state them: the competitor 20% under its prices, its backup 30% over them
REACH, OPENS, CLOSES, WORKDAYS = 80, 8 * HOUR, 18 * HOUR, 5  # an outage's region (km around a town), the hours of both events, the days they can fall on
SURE = 200.0  # log-likelihood beyond which an event's day is settled


def euros(cents: float) -> int:
    """Cents rounded to whole euros, as dealers' prices are."""
    return int(cents / 100 + 0.5) * 100


def decline(request: PriceRequest) -> dict[str, int]:
    """The answer to a request we do not want: one option at a price no dealer pays."""
    first = request["options"][0]
    return {first["kind"]: int(first["listPriceCents"] * DECLINE)}


@dataclass
class MarketPolicy:
    slope: float = prior.SLOPE  # how fast a dealer's yes fades: logits per unit of log price (10% dearer is about one logit)
    speed: float = prior.SPEED  # log price by which a dealer's level for an option is lower, for each faster option of the request
    trust: float = prior.TRUST  # log price a dealer adds for each order we delivered to it on time
    level: float = prior.LEVEL  # the log price level of an average world
    spread: dict = field(default_factory=lambda: dict(prior.SPREAD))  # the parts of a level, and how far each strays from its prior (sd)
    surprises: bool = True  # False leaves the war day and the outage day to the day and place parts: the market before idea 13, which tools/surprises.py replays
    explore: Optional[tuple[float, float]] = None  # draw each multiple of the list price from this range: the random weeks that prior.py is fitted on
    seed: str = ""  # of those draws


class Market:
    """Believes that a dealer says yes with a chance that is logistic in log price, around a level that is a sum of parts:
    the world, the day, the dealer, the two places, their lane, the pickup place today. Each answer moves every part it touched (one Kalman step).
    A week also has one price war day and one outage day and region: each answer weighs every such week, and today's level is the mix they leave.
    The day part has two beliefs, one if today is the war day and one if not: a war and a low calm day differ only in what they ask of it."""

    def __init__(self, policy: MarketPolicy, books: Books, fleet: Fleet, places: Optional[dict] = None):
        self.policy, self.books, self.fleet = policy, books, fleet
        self.places = prior.PLACES if places is None else places  # tools/winmodel.py fits this table through here
        self.beliefs: dict[tuple, tuple[float, float]] = {}  # part -> mean and variance of its share of the log level
        atlas = fleet.atlas if fleet and policy.surprises else None
        self.regions = {town: frozenset(place for place in atlas.places if atlas.crow_km(town, place) <= REACH) for town in sorted(atlas.places)} if atlas else {}  # town -> the places an outage around it reaches; none when the events are not weighed
        self.heard: dict[int, dict[str, float]] = {}  # day -> event ("war", or the town an outage is around) -> log-likelihood of the day's answers against a calm day
        self.cars: dict[str, int] = defaultdict(int)  # pickup place -> answers so far: how busy its dealers are

    def quote(self, request: PriceRequest) -> dict[str, int]:
        """A price in cents for each option the fleet can move: the option and price with the highest expected margin over its cost, and every other option at that margin."""
        if self.policy.explore:
            return self.research(request)
        costs, offers = {}, {}  # per option: what the car costs us, and its highest expected margin with the price that gives it
        for option in request["options"]:
            cost = self.fleet.cost(request, option)
            if cost is not None:
                kind, prices = option["kind"], (euros(option["listPriceCents"] * step) for step in STEPS)
                costs[kind] = cost
                yes = self.curve(request, option)
                offers[kind] = max(((price - cost) * yes(price), price) for price in prices)
        best = max(offers, key=offers.get, default=None)
        if best is None or offers[best][0] <= 0:
            return decline(request)
        margin = offers[best][1] - costs[best]
        return {kind: euros(cost + margin) for kind, cost in costs.items()}  # the dealer chooses its speed, and we earn the same whichever it takes

    def learn(self, request_id: str, won: Optional[str]) -> None:
        """The dealer's answer to our quote: the option it bought from us, or None. A pure function of the ordered history."""
        request, prices = self.books.requests.get(request_id), self.books.quotes.get(request_id)
        if not request or not prices:
            return
        option = self.weighed(request, prices, won)
        asked = math.log(prices[option["kind"]] / option["listPriceCents"])
        levels = {war: self.level(request, option, war) for war in (False, True)}  # as they were when the dealer answered
        self.hear(request, levels, asked, won)
        mix = self.mix(request)  # with this answer heard
        self.step([part for part in self.parts(request) if part[0] != "day"], levels, mix, asked, won)
        for war in (False, True):  # the day part learns twice: as it is if today is the war day, and if it is not
            self.step([part for part in self.parts(request, war) if part[0] == "day"], levels, [component for component in mix if component[2] == war], asked, won)
        self.cars[request["legs"][0]["pickup"]["placeId"]] += 1

    # What the market believes: the chance of a yes at a price.

    def curve(self, request: PriceRequest, option: DeliveryOption) -> Callable[[int], float]:
        """The chance that the dealer buys this option, when it is the only one we offer, as a function of our price."""
        levels, mix, list_price = {war: self.level(request, option, war) for war in (False, True)}, self.mix(request), option["listPriceCents"]
        return lambda price: sum(chance * self.yes(levels[war][0] + shift - math.log(price / list_price), levels[war][1]) for chance, shift, war in mix)

    def chance(self, request: PriceRequest, option: DeliveryOption, price: int) -> float:
        """The same chance at one price."""
        return self.curve(request, option)(price)

    def yes(self, above: float, variance: float) -> float:
        """The chance of a yes at a log price this far under a level known with this variance: a logistic, flatter the less we know the level."""
        return 1 / (1 + math.exp(-self.policy.slope * above / math.sqrt(1 + math.pi * self.policy.slope ** 2 * variance / 8)))

    def level(self, request: PriceRequest, option: DeliveryOption, war: bool = False) -> tuple[float, float]:
        """Mean and variance of the log multiple of the list price at which this dealer buys this option half the time, before today's event:
        with the day part as it is if today is the war day, or if it is not."""
        policy, beliefs = self.policy, [self.belief(part) for part in self.parts(request, war)]
        known = policy.trust * self.books.on_time[request["dealerId"]] - policy.speed * request["options"].index(option)
        return known + sum(mean for mean, _ in beliefs), sum(variance for _, variance in beliefs)

    def parts(self, request: PriceRequest, war: bool = False) -> list[tuple]:
        """The parts of the level that this request touches, of those the policy gives a spread. With `war`, the day part is its belief for a war day."""
        leg, day = request["legs"][0], request["arrivedAt"] // DAY
        pickup, delivery = leg["pickup"]["placeId"], leg["delivery"]["placeId"]
        keys = {"world": (), "day": (day, "war") if war else (day,), "dealer": (request["dealerId"],), "from": (pickup,), "to": (delivery,), "lane": (pickup, delivery), "from today": (pickup, day)}
        return [(name, *keys[name]) for name in self.policy.spread]

    def belief(self, part: tuple) -> tuple[float, float]:
        """Mean and variance of one part: what the answers taught, or its prior (the average world's level, a place's level in other weeks, else zero)."""
        if part in self.beliefs:
            return self.beliefs[part]
        mean = self.policy.level if part[0] == "world" else self.places.get(part[0], {}).get(part[1], 0.0)
        return mean, self.policy.spread[part[0]] ** 2  # a prior is not kept: only what an answer taught is, so a replay of the answers rebuilds it all

    # The week's two events: which of them today can be, and what each does to a level.

    def mix(self, request: PriceRequest) -> list[tuple[float, float, bool]]:
        """What today's possible events do to this request's level: (chance, shift, whether it is the war's), a calm day among them."""
        mix: dict[tuple[float, bool], float] = defaultdict(float)
        for event, chance in self.odds(request["arrivedAt"] // DAY).items():
            mix[(self.shift(request, event), event == "war")] += chance
        mix[(0.0, False)] = max(0.0, 1 - sum(chance for key, chance in mix.items() if key != (0.0, False)))
        return [(chance, shift, war) for (shift, war), chance in mix.items()]

    def odds(self, day: int) -> dict[str, float]:
        """The chance of each event today. The weeks we weigh: one war day, one outage day and town (a busy region more often), never both on one day.
        Every answer so far weighs each such week; a day not heard yet says nothing."""
        if not self.regions or day >= WORKDAYS:
            return {}
        busy = {town: 1 + sum(self.cars[place] for place in region) for town, region in self.regions.items()}
        heard = [self.heard.get(d, {}) for d in range(WORKDAYS)]
        war = [math.exp(h.get("war", 0.0)) for h in heard]
        outage = [sum(cars * math.exp(h.get(town, 0.0)) for town, cars in busy.items()) for h in heard]
        others = [d for d in range(WORKDAYS) if d != day]
        odds = {town: cars * math.exp(heard[day].get(town, 0.0)) * sum(war[d] for d in others) for town, cars in busy.items()}
        odds["war"] = war[day] * sum(outage[d] for d in others)
        calm = sum(war[w] * outage[d] for w in others for d in others if d != w)
        return {event: weight / (calm + sum(odds.values())) for event, weight in odds.items()}

    def shift(self, request: PriceRequest, event: str) -> float:
        """The log price an event adds to this request's level: a war lowers every dealer's, an outage raises it for the cars that leave its region."""
        if not OPENS <= request["arrivedAt"] % DAY < CLOSES:
            return 0.0
        return WAR if event == "war" else OUTAGE if request["legs"][0]["pickup"]["placeId"] in self.regions[event] else 0.0

    # The three steps of learn.

    def weighed(self, request: PriceRequest, prices: dict[str, int], won: Optional[str]) -> DeliveryOption:
        """The option of our quote that the dealer set against the competitor: the one it bought, else our best offer in its eyes."""
        offered = [option for option in request["options"] if option["kind"] in prices]
        return next((o for o in offered if o["kind"] == won), None) or max(offered, key=lambda o: self.chance(request, o, prices[o["kind"]]))

    def hear(self, request: PriceRequest, levels: dict[bool, tuple[float, float]], asked: float, won: Optional[str]) -> None:
        """Adds to each event that today can be how much better than a calm day it foretold this answer, as a log-likelihood."""
        said = lambda shift, war: math.log(self.yes((levels[war][0] + shift - asked) * (1 if won else -1), levels[war][1]))
        for event in ["war", *self.regions] if self.regions else []:
            gain = said(self.shift(request, event), event == "war") - said(0.0, False)
            if gain:
                heard = self.heard.setdefault(request["arrivedAt"] // DAY, {})
                heard[event] = max(-SURE, min(SURE, heard.get(event, 0.0) + gain))

    def step(self, parts: list[tuple], levels: dict[bool, tuple[float, float]], mix: list[tuple[float, float, bool]], asked: float, won: Optional[str]) -> None:
        """One Kalman step of these parts towards the answer, when the level is this mix."""
        slope, total = self.policy.slope, sum(chance for chance, _, _ in mix)
        if total <= 0:
            return
        mean = sum(chance * (levels[war][0] + shift) for chance, shift, war in mix) / total
        variance = sum(chance * (levels[war][1] + (levels[war][0] + shift - mean) ** 2) for chance, shift, war in mix) / total
        p = 1 / (1 + math.exp(-slope * (mean - asked)))
        weight = slope * slope * p * (1 - p)
        push, shrink = slope * ((won is not None) - p) / (1 + weight * variance), weight / (1 + weight * variance)
        for part in parts:
            m, v = self.belief(part)
            self.beliefs[part] = (m + v * push, v - v * v * shrink)

    def research(self, request: PriceRequest) -> dict[str, int]:
        """Random multiples on a random subset of the options, to measure dealers."""
        policy, rng, options = self.policy, random.Random(f"{self.policy.seed}:{request['id']}"), request["options"]
        chosen = rng.choice([options[:1], options[-1:], options])
        prices = {o["kind"]: euros(o["listPriceCents"] * rng.uniform(*policy.explore)) for o in chosen if self.fleet.cost(request, o) is not None}
        return prices or decline(request)
