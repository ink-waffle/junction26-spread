"""The dealer side: what to quote for each option of a price request."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from spread.types import PriceRequest

from .books import Books
from .fleet import Fleet

DECLINE = 4.0  # times the list price: a quote that never wins, and costs no goodwill


@dataclass
class MarketPolicy:
    price: float = 1.45  # quote, as a multiple of the list price
    margin: float = 0.15  # never quote below our expected cost plus this share of it
    explore: Optional[tuple[float, float]] = None  # research: draw each multiple from this range
    options: str = "first"  # which options to quote: first, last, all, or random (research)
    seed: str = ""


class Market:
    def __init__(self, policy: MarketPolicy, books: Books, fleet: Fleet):
        self.policy, self.books, self.fleet = policy, books, fleet

    def quote(self, request: PriceRequest) -> dict[str, int]:
        """A price in cents for each option we offer."""
        policy, rng = self.policy, random.Random(f"{self.policy.seed}:{request['id']}")
        options = request["options"]
        chosen = {"first": options[:1], "last": options[-1:], "all": options}.get(policy.options) or rng.choice([options[:1], options[-1:], options])
        prices = {}
        for option in chosen:
            cost = self.fleet.cost(request, option)
            if cost is None:
                continue
            multiple = rng.uniform(*policy.explore) if policy.explore else policy.price
            prices[option["kind"]] = int(max(option["listPriceCents"] * multiple, cost * (1 + policy.margin)) / 100 + 0.5) * 100
        return prices or {options[0]["kind"]: int(options[0]["listPriceCents"] * DECLINE)}

    def learn(self, request_id: str, option: Optional[str]) -> None:
        """The dealer's answer to our quote: the option it bought from us, or None."""
