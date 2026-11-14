"""Reads a dealer's note into the facts the world will act on. First version: the kit starter's keyword reader."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from spread.types import Note

from .atlas import DAY, HOUR


@dataclass
class NoteFacts:
    """What a note changes: all times are world minutes, None when the note says nothing about them."""
    ready_at: Optional[int] = None  # the car cannot be collected before this minute
    pickup_closes: Optional[int] = None  # minute of the day after which the pickup site hands over nothing
    pickup_opens: Optional[int] = None
    delivery_closes: Optional[int] = None  # minute of the day after which the delivery site receives nothing
    delivery_opens: Optional[int] = None
    deadline: Optional[int] = None  # a tighter delivery deadline
    manual: bool = False
    plates: bool = False
    summer_tyres: bool = False


AFTER = re.compile(r"jälkeen|alkaen|aikaisintaan|\bafter\b|\bfrom\b|earliest|not before|ei ennen|valmis|\bready\b|efter|tidigast|inte före|klar", re.ASCII)
BEFORE = re.compile(r"ennen|mennessä|viim|\bbefore\b|\bby\b|latest|före|senast", re.ASCII)
DELIVERY = re.compile(r"toimit|perillä|perille|vastaanot|kohde|deliver|arrive|destination|receiv|leverera|leverans|framme|mottag", re.ASCII)
CLOCK = re.compile(r"(?:klo|kl\.?)\s*(\d{1,2})(?:[.:](\d{2}))?|\b(\d{1,2})[.:](\d{2})\b", re.ASCII)
RANGE = re.compile(r"\b(\d{1,2})(?:[.:](\d{2}))?\s*[-–]\s*(\d{1,2})(?:[.:](\d{2}))?\b", re.ASCII)
MANUAL = re.compile(r"manuaal|manuuaal|manual|käsivaiht|manuell", re.ASCII)
PLATES = re.compile(r"kilv|plates|plaates|skyltar", re.ASCII)
TYRES = re.compile(r"kesärenkailla|kesärenkaat alla|summer tyres on|on su?mm?u?er tyres|sommardäck på", re.ASCII)


def read(note: Optional[Note], arrived_at: int) -> NoteFacts:
    """The facts of a note that arrived at `arrived_at`; times without a day are read on the arrival day."""
    facts = NoteFacts()
    if not note:
        return facts
    text = note["text"].lower()
    facts.manual, facts.plates, facts.summer_tyres = bool(MANUAL.search(text)), bool(PLATES.search(text)), bool(TYRES.search(text))
    at_delivery = bool(DELIVERY.search(text))
    day = arrived_at // DAY * DAY

    def minutes(hour: int, minute: int) -> Optional[int]:
        return None if hour > 24 or minute > 59 else hour * HOUR + minute

    for match in RANGE.finditer(text):
        opens, closes = minutes(int(match[1]), int(match[2] or 0)), minutes(int(match[3]), int(match[4] or 0))
        if opens is None or closes is None or opens >= closes:
            continue
        if at_delivery:
            facts.delivery_opens, facts.delivery_closes = opens, closes
        else:
            facts.pickup_opens, facts.pickup_closes = opens, closes
    text = RANGE.sub(" ", text)
    for match in CLOCK.finditer(text):
        m = minutes(int(match[1] or match[3]), int(match[2] or match[4] or 0))
        if m is None:
            continue
        around = text[max(0, match.start() - 16): match.end() + 16]
        if AFTER.search(around):
            if not at_delivery:
                facts.ready_at = max(facts.ready_at or 0, day + m)
        elif BEFORE.search(around):
            if at_delivery:
                facts.deadline = min(facts.deadline or 10 ** 9, day + m)
            else:
                facts.pickup_closes = min(facts.pickup_closes or DAY, m)
    return facts
