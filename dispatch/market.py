"""The dealer side: what to quote for each option of a price request."""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

from spread.types import PriceRequest

from .books import Books

DECLINE = 4.0  # times the list price: a quote that never wins, and costs no goodwill


@dataclass
class MarketPolicy:
    price: float = 1.3  # quote, as a multiple of the list price
    explore: Optional[tuple[float, float]] = None  # research: draw each multiple from this range
    options: str = "first"  # which options to quote: first, last, all, or random (research)
    seed: str = ""


class Market:
    def __init__(self, policy: MarketPolicy, books: Books):
        self.policy, self.books = policy, books

    def quote(self, request: PriceRequest) -> dict[str, int]:
        """A price in cents for each option we offer."""
        policy, rng = self.policy, random.Random(f"{self.policy.seed}:{request['id']}")
        options = request["options"]
        chosen = {"first": options[:1], "last": options[-1:], "all": options}.get(policy.options) or rng.choice([options[:1], options[-1:], options])
        prices = {}
        for option in chosen:
            multiple = rng.uniform(*policy.explore) if policy.explore else policy.price
            prices[option["kind"]] = int(option["listPriceCents"] * multiple / 100 + 0.5) * 100
        return prices

    def learn(self, request_id: str, option: Optional[str]) -> None:
        """The dealer's answer to our quote: the option it bought from us, or None."""
