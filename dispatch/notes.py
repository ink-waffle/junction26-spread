"""Reads a dealer's note into the facts the world will act on.

    note -> clauses -> words -> cues, clock times and days -> one statement per clause -> NoteFacts

A clause ends at punctuation. Each word is looked up in a small vocabulary of cues in Finnish, Swedish and English, one typo
forgiven. A clause with a clock time states one fact, and its cues say which. A correction replaces a time or a day, a denial deletes it."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from spread.types import Note

from .atlas import DAY, HOUR


@dataclass
class NoteFacts:
    """What a note changes: world minutes, or minutes of the day for opening hours; None when the note says nothing about it."""
    ready_at: Optional[int] = None  # the car is not ready before this minute
    released_at: Optional[int] = None  # the dealer hands the car over after payment, at this minute
    pickup_opens: Optional[int] = None  # real weekday hours of the pickup site
    pickup_closes: Optional[int] = None
    delivery_opens: Optional[int] = None  # real weekday hours of the delivery site
    delivery_closes: Optional[int] = None
    deadline: Optional[int] = None  # the car must arrive by this minute
    manual: bool = False
    plates: bool = False
    summer_tyres: bool = False


# The vocabulary: cue -> words, after lowercasing and dropping accents. "valmi-" is a stem, "klar" a whole word.
CUES = {
    "ready": "valmi- valmis valmiina klar klart ready",
    "collect": "nout- noud- noudettav- noutaa hake- haet- haettav- haku hakemaan collect- pickup- pick- hamt- hamtas hamtning luovut- luovutus lamnas",
    "pay": "maksu- maksun maksa- maksaa makse- maksettu rahoitu- payment pays paid financ- betal- betalning finans-",
    "open": "auki avoinna aukiolo- open opening oppet oppettid- paikalla taalla ketaan nobody ingen vastaanot- vastaanott- receiv- receiving mottag- mottagaren mottagning",
    "closed": "kiinni sulke- sulkee sulje- suljet- close closes closed closing stang- stanger",
    "there": "vastaanot- vastaanott- receiv- receiving mottag- mottagaren mottagning kohde kohtee- perill- toimitu- toimitus destinat- destination deliver- arriv- arrival framme plats",
    "customer": "asiakas customer kunden",
    "seller": "myyja saljare- seller kotona hemma",  # a private seller's booked slot, which the request already states
    "call": "soita- soitto call ring ilmoit-",  # a clause about phoning states nothing
    "from": "alkaen from aikaisint- earliest tidigast vasta forst forran framat",
    "after": "jalkeen after efter",
    "before": "ennen before fore innan",
    "by": "viim- viimeist- mennessa asti saakka latest later senast until till by",
    "not": "ei not no inte ej nobody ingen",
    "fix": "eikun eiku korjaus correction sorry mean forlat nej rattelse",
    "clock": "klo kl kello klockan at valilla mellan between",
    "half": "puoli puolta halv half",
    "manual": "manuaa- manuaali- manual manuell- kasivaih- kasivaihte- stick",
    "plates": "kilv- kilvet kilpi- kilpia plates skylt- skyltar skyltarna provskylt- rekkar- rekkareita rekisterikilv- rekisterikilve- rekisterist- unregistered siirtokilv- koekilv-",
    "summer": "kesarenk- kesarenka- kesareng- kesarenga- kesakum- kesakumi- summer summers sommardack- sommardacke-",
    "winter": "talvirenk- talvirenka- talvet winter winters vinterdack-",
    "cargo": "takakon- tavarati- trunk bakluck- vantei- lisaksi in i",  # tyres that travel in the car
    "day+0": "tanaan idag today",
    "day+1": "huomen- huomenna tomorr- tomorrow tmrw imorgon morgon",
    "day+2": "ylihuom- overmorgon iovermorgon",
    "weekday0": "ma maanant- maanantai- mon monday man mandag",
    "weekday1": "ti tiist- tiistai- tue tues tuesday tis tisdag",
    "weekday2": "ke keskiv- keskiviik- wed weds wednes- wednesday ons onsdag",
    "weekday3": "to torst- torstai- thu thur thurs thursday tors torsdag",
    "weekday4": "pe perjant- perjantai- fri friday fre fredag",
    "weekday5": "la lauant- lauantai- sat saturday lor lordag",
}
HOURS = {"yksi": 1, "yhde": 1, "yhte": 1, "yhta": 1, "kaksi": 2, "kahde": 2, "kahte": 2, "kahta": 2, "kolme": 3, "nelja": 4, "viisi": 5, "viide": 5, "viite": 5, "viitta": 5,
         "kuusi": 6, "kuude": 6, "kuute": 6, "kuutta": 6, "seitsema": 7, "kahdeksa": 8, "yhdeksa": 9, "kymmene": 10, "kymmenta": 10}  # Finnish stems, which take a case and "-toista"
HOUR_WORDS = {stem + case + teen: (hour + (10 if teen else 0), case == "lta") for stem, hour in HOURS.items()
              for case in ("", "lta", "sta", "n", "a", "en", "an", "een", "aan") for teen in ("", "toista")}  # word -> (hour, says "at" by itself)
HOUR_WORDS.update({word: (i % 12 + 1, word == "noon") for names in ("ett tva tre fyra fem sex sju atta nio tio elva tolv", "one two three four five six seven eight nine ten eleven noon")
                   for i, word in enumerate(names.split())}, twelve=(12, False))
ANCHORS = {"clock", "half", "from", "after", "before", "by", "not", "fix"}  # next to one of these, or to a day, a bare number is a clock time
ABBREVIATION = re.compile(rf"\b(?:(viim|klo?|n|ca)\.|(ma|ti|ke|to|pe|la)\.(?=\s*(?:\d|klo|kello|puol|{'|'.join(HOURS)})))")  # a period that ends no sentence
CLAUSE_END = re.compile(r"[.!?;]+\s+|\s/\s|[,()]\s*|:\s+")
WORD = re.compile(r"(?<!\d)(\d{1,2})(?:([.:])?(\d\d))?(?!\d)(?:\s?([ap])\.?m\b)?(:[a-z]+)?|[a-z]+(?:-[a-z]+)*|-")


def typo(written: str, word: str) -> bool:
    """`written` is `word` with one letter dropped, doubled or swapped with its neighbour."""
    i = 0
    while i < min(len(written), len(word)) and written[i] == word[i]:
        i += 1
    swapped = written[i:i + 2] == word[i:i + 2][::-1] and written[i + 2:] == word[i + 2:]
    return len(written) == len(word) and swapped or written[-1:] == word[-1:] and (written[i:] == word[i + 1:] or written[i + 1:] == word[i:])


@lru_cache(maxsize=None)
def cues_of(word: str) -> frozenset:
    """The cues a word carries: it is a vocabulary word or starts with a vocabulary stem. A word that is in no entry may be a typo of one of six letters or more."""
    exact, close = set(), set()
    for cue, entries in CUES.items():
        for entry in entries.split():
            stem = entry.rstrip("-")
            parts = [word] if stem == entry else [word[:len(stem) + d] for d in (0, -1, 1)]
            if parts[0] == stem:
                exact.add(cue)
            elif len(stem) >= 6 and any(typo(part, stem) for part in parts):
                close.add(cue)
    return frozenset(exact or close)


@lru_cache(maxsize=None)
def hour_of(word: str) -> Optional[tuple[int, bool]]:
    """The hour that a word names, as (minute of the day, says "at" by itself). An hour in words is a working hour: "two" is 14:00."""
    known = HOUR_WORDS.get(word) or next((HOUR_WORDS[w] for w in HOUR_WORDS if len(w) >= 6 and typo(word, w)), None)
    return known and ((known[0] + 12 if known[0] < 9 else known[0]) * HOUR, known[1])


@dataclass
class Word:
    text: str
    cues: frozenset = frozenset()
    minute: Optional[int] = None  # the clock time this word can be
    sure: bool = False  # written as a clock time: 14.30, 3pm, 15:een, kolmelta, noon

    @property
    def day(self) -> Optional[str]:
        return next((cue for cue in self.cues if cue.startswith(("day+", "weekday"))), None)


def words(part: str) -> list[Word]:
    out = []
    for match in WORD.finditer(part):
        text, (hour, separator, minute, meridiem, ending) = match[0], match.groups()
        if hour is None:
            word = Word(text, cues_of(text))
            if hour_of(text) and (text in HOUR_WORDS or not word.cues):
                word.minute, word.sure = hour_of(text)
        else:
            word = Word(text)
            if int(hour) <= 24 and int(minute or 0) < 60:  # 14, 14.30, 1430, 2pm, 15:een
                hour = int(hour) % 12 + (12 if meridiem == "p" else 0) if meridiem else int(hour)
                word.minute, word.sure = hour * HOUR + int(minute or 0), bool(separator or meridiem or ending)
        out.append(word)
    return out


def clauses_of(text: str) -> list[list[Word]]:
    """Cuts a note into clauses at its punctuation. A part that opens with a correction or a denial amends the last clause that named a time."""
    text = unicodedata.normalize("NFKD", text.lower().replace("\u2013", "-").replace("\u2014", "-"))
    text = re.sub(r"\bei kun\b", "eikun", "".join(c for c in text if not unicodedata.combining(c)))
    clauses, amended = [], None
    for part in CLAUSE_END.split(ABBREVIATION.sub(lambda m: m[1] or m[2], text)):
        ws = words(part)
        if not ws or any("call" in w.cues for w in ws):
            continue
        after_not = next((w for w in ws[1:] if "clock" not in w.cues), Word(""))
        denies = "not" in ws[0].cues and (after_not.minute is not None or after_not.day is not None)
        if clauses and amended is None and ("fix" in ws[0].cues or denies):
            amended = next((c for c in reversed(clauses) if any(w.minute is not None or w.day for w in c)), clauses[-1])
        if amended is None:
            clauses.append(ws)
        else:
            amended.extend(ws)
            if any(w.minute is not None or w.day for w in ws):  # "sorry," alone: the correction itself comes in the next part
                amended = None
    return clauses


@dataclass
class Clause:
    cues: set
    times: list[int]  # minutes of the day, in order
    day: int  # days after the arrival day


def clause_of(ws: list[Word], weekday: int) -> Clause:
    """Finds the clock times and the day of a clause, drops what it denies and applies its correction."""
    cues, found, fixed_from = set(), {}, None  # found: position -> ("time" or "day", value)
    at = lambda i: ws[i] if 0 <= i < len(ws) else Word("")
    for i, w in enumerate(ws):
        if w.minute is not None:  # a bare number is a clock time next to a clock word, a day or a relation, or in a range
            anchored = w.sure or any(at(j).cues & ANCHORS or at(j).day for j in (i - 1, i + 1))
            ranged = at(i + 1).text == "-" and at(i + 2).minute is not None or at(i - 1).text == "-" and at(i - 2).minute is not None
            half = "half" in at(i - 1).cues  # "half three" is 14:30
            if anchored or ranged:
                found[i] = ("time", (w.minute + 12 * HOUR if half and w.minute < 9 * HOUR else w.minute) - (30 if half else 0))
        elif w.day and (len(w.text) > 4 or w.day.startswith("day+") or at(i + 1).minute is not None or at(i + 1).cues & {"clock", "half"} or "fix" in at(i - 1).cues):
            if w.day.startswith("weekday"):  # that weekday 2 to 6 days ahead; a short name ("to") counts only before a time or in a correction
                found[i] = ("day", (int(w.day[7:]) - weekday - 2) % 7 + 2)
            else:
                found[i] = ("day", int(w.day[4:]) + ("after" in at(i - 1).cues))  # "the day after tomorrow"
                cues.discard("after" if "after" in at(i - 1).cues else None)
        elif "fix" in w.cues and fixed_from is None:
            fixed_from = i
        cues |= {cue for cue in w.cues if cue != "not" and not cue.startswith(("day+", "weekday"))}
    for i, w in enumerate(ws):
        if "not" in w.cues:
            j = i + 1
            while "clock" in at(j).cues or at(j).text in ("a", "en"):
                j += 1
            if j in found:  # "not 3pm", "not tomorrow": the note denies it
                del found[j]
            elif "manual" in at(j).cues:  # "automatic, not a manual"
                cues.discard("manual")
            else:  # "not before 3": any other "not" turns before into after
                cues.add("not")
    out = {}
    for kind in ("time", "day"):
        early = [v for i, (k, v) in sorted(found.items()) if k == kind and (fixed_from is None or i < fixed_from)]
        late = [v for i, (k, v) in sorted(found.items()) if k == kind and fixed_from is not None and i > fixed_from]
        out[kind] = early[:max(0, len(early) - len(late))] + late  # a correction replaces the last times or day before it
    return Clause(cues, out["time"], out["day"][-1] if out["day"] else 0)


def read(note: Optional[Note], arrived_at: int) -> NoteFacts:
    """The facts of a note that arrived at `arrived_at`: days count from the arrival day."""
    facts = NoteFacts()
    if not note or not note.get("text"):
        return facts
    today, paying = arrived_at // DAY, False
    for ws in clauses_of(note["text"]):
        clause = clause_of(ws, today % 7)
        cues, times = clause.cues, clause.times
        facts.manual |= "manual" in cues
        facts.plates |= "plates" in cues
        facts.summer_tyres |= ("summer" in cues or {"winter", "not"} <= cues) and "cargo" not in cues
        paid, paying = paying or "pay" in cues, "pay" in cues and not times  # "buyer pays first, pickup from 13": the payment clause names the next time
        if not times or "seller" in cues:
            continue
        at = (today + clause.day) * DAY + times[0]
        until = "by" in cues or bool(cues & {"before", "after"}) and ("not" in cues) == ("after" in cues)  # "before 3", "not after 3"
        if paid:
            facts.released_at = at
        elif len(times) > 1 or cues & {"open", "closed"}:  # opening hours, of the delivery site when the clause names it
            site = "delivery" if "there" in cues else "pickup"
            if len(times) > 1:
                setattr(facts, f"{site}_opens", times[0])
                setattr(facts, f"{site}_closes", times[1])
            elif "from" in cues and "closed" not in cues:
                setattr(facts, f"{site}_opens", times[0])
            else:
                setattr(facts, f"{site}_closes", times[0])
        elif cues & {"there", "customer"}:  # the car must be there, or the customer comes for it
            facts.deadline = at
        elif "collect" in cues and until:
            facts.pickup_closes = times[0]
        elif cues & {"ready", "collect"}:
            facts.ready_at = at
    return facts
