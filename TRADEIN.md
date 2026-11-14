# TRADEIN: does winning trade-ins pay now? (agent "tradein", Sunday night)

## 0. Verdict

**No. Play 8ae61c5 as frozen; `dispatch/` on this branch is 8ae61c5.** I tried three single changes (one number or one line each) against
8ae61c5 on the same weeks. None reaches the bar:

| Candidate (commit) | Weeks | Margin a week (se) | On time, points (se) | Late a week | Orders | Worst sample | < 93.5% | Ranked | Trade-ins won a week, on time |
|---|---|---|---|---|---|---|---|---|---|
| `trade_in` -3.35 -> **-1.54** (e58abd7) | **halal-161..192, s14 + s13** | **+55 (105)** | **-0.02 (0.08)** | -0.1 | -3 | 92.3% (main: 92.3%, the same halal-189) | 2 (main 2) | 64/64 | 0.33 -> 0.70; 31 of 45 |
| the same | tune+wide, s14 | -9 (164) | -0.16 (0.08) | +0.7 | -1 | 94.0% | 0 | 24/24 | 0.29 -> 0.62; 10 of 15 |
| `trade_in` -> **0** (the other bracket) | tune+wide, s14 | -293 (169) | -0.43 (0.12) | +1.8 | -6 | 94.1% | 0 | 24/24 | 0.29 -> 2.67; 39 of 64 |
| the timetable knows the new car's **booked hour** (fa0d0bb) | tune+wide, s14 | -182 (98) | +0.03 (0.08) | -0.3 | -4 | 94.0% | 0 | 24/24 | the same 7 trade-ins, the same ends |

Baselines: `orch-main161-s14`/`-s13` (8ae61c5, halal-161..192): EUR 14,964 a week, 96.4%, worst 92.3%, 429 orders; -1.54 there: EUR 15,019, on time 96.4% (s14 EUR 15,109 / 96.3%, s13 EUR 14,928 / 96.4%). `gap-main-s14` (8ae61c5,
tune+wide; halal-01 replayed to the cent, EUR 14,789): EUR 15,352, 96.8%. Commands: `python -m tools.ablations orch-main161 tradein-w154`,
`python -m tools.weekdays orch-main161 tradein-w154`, `python -m tools.ablations gap-main tradein-w154 tradein-w0 tradein-hour`.

**Why winning trade-ins does not pay.** It is not a wrong weight, and it is not the posting.

- **The weight -1.54 is right.** On weeks where we did win trade-ins, the weight comes out at -1.50 (se 0.20; `tradein-w0-s14`, 64 won) and
  -1.40 (se 0.25; `skeptic-notradein-s14`, 77 won). The baked -3.35 says 23% of those cars on time where 61% were; -1.50 says 61%
  (`python -m tools.tradein_study --fit tradein-w0-s14`). Selection had hidden this: at -3.35 we win one trade-in in three weeks.
- **But a trade-in that the model sees correctly is still a bad buy for us.** About 60-70% arrive on time, against 95% for a one-car order.
  The new car must arrive in the customer's booked hour + 30 minutes. After its own refunds a trade-in is worth about EUR 30 (`tradein-w0`:
  EUR 96 on time, -74 late, EUR 29.7 an order, +79 a week). Its late risk also takes room under the 97.5% target. A late order costs about
  EUR 120 there (a point of on-time costs EUR 512 on unseen weeks, SKEPTIC.md). At 0.39 late per trade-in, each one ends at about -EUR 17.
  The calibrated model prices them that way: it wins 0.7 a week, the ones whose other signs are good, and their margin is about zero
  (halal-161..192: -27 and +28 a week at the two strides). The weight 0 buys 2.7 a week and loses 293.
- **The leaders' slope is not causal for us.** The detective's figure is +EUR 280 of the leader's lead for each extra trade-in request a week.
  One trade-in is a EUR 150 sale with EUR 80-105 of margin when it is on time (three runs). That is less than the slope, so the slope cannot be
  the trade-ins' own money. With about 21 requests a week, even all of them won and on time is EUR 2,000 a week, and that is not possible at the
  share of late cars we measure.

**What would be needed instead:** more trade-ins on time, not more trade-ins. Half the late ones are a driver problem that no fee we tried moved
(section 1: no driver before the warning, a lost driver, a booked driver who comes late without a word). With 45 trade-ins on halal-161..192
and 141 won at the weight 0, we have no lever that would buy that. **Not for tonight.**

**Optional, not a margin candidate:** e58abd7 (-1.54) makes the model honest about trade-ins at no measured cost. That is +55 (se 105) and
-0.02 point (se 0.08) on 64 unseen samples, with the same worst week. It is a choice between equals, like research/simple's D. It has not had the
restart test (only a winner gets one). It differs from 8ae61c5 in one number and one comment line. If the team wants the jury to see a correct number, take it. Otherwise
-3.35 stays, with SKEPTIC.md's "undecided" now decided at -1.5.

## 1. What the saved runs say

`python -m tools.tradein_study orch-head-record gap-main-s14 skeptic-notradein-s14 orch-main161-s14 tradein-w154-s14 tradein-w0-s14`

- **How many, and what they pay.** 20.8 trade-in requests a week (`orch-head-record` = 8ae61c5 on halal-129..160, no stride; 21.0 on
  tune+wide). Their typical fee is 0.53 x list (one car 0.90 x): list EUR 110, typical EUR 54 at the median, lanes 170 km. Every one has a
  private delivery: the new car's deadline is the end of the customer's booked hour + 30 minutes (RULES.md rule 5). The order's own deadline
  is the old car's, a median 4-6 h later.
- **What we do with them.** We quote a median 10 x list (the decline) and win 0.28 a week (9 of 666): 4 of 9 on time. 8 of 9 were first
  posted at the urgent 1.6 x because the deadline warning came before any driver booked. Most were won on Monday morning, when the price of a
  late order is still near zero. On halal-161..192 at stride 14 we won 12 of 654, 5 on time, -EUR 64 a week.
- **With the weight at 0** (`skeptic-notradein-s14`: the older system of 22:16, halal-65..96, stride 14): 2.4 won a week at 1.48 x list,
  EUR 47.8 an order, but 45 of 77 on time. Those first posted at 1.5 x or less were 44 of 60 on time; those posted after the warning
  (1.6 x), 1 of 17. Its paired effect was +26 (se 194). On 8ae61c5 (`tradein-w0-s14`): 2.7 a week at 1.38 x list, 39 of 64 on time,
  EUR 29.7 an order.
- **Why they are late** (`skeptic-notradein-s14`, 32 of 77 late; `tradein-w0-s14`, 25 of 64): the warning before any driver booked (10; 9),
  the driver lost to a drop or a no-show (10; 5), a booked driver who collected the new car after `lastPickupAt` without a word (11; 11), never
  delivered (1; 0). In every late one, the new car missed the booked hour.
- **History.** `explore1` (random quotes and fees, 8 tune weeks): 29 of 88 won trade-ins on time. NIGHT_LOG: 17% / 38% / 61% on time at
  <= 1.0 / 1.15-1.3 / 1.5-2.0 x typical (83 orders, an older system).

## 2. The posting: as the rules advise, with one blind spot

- **The gig is right.** `Timetable.gigs` posts a trade-in as one gig, p0 > d0 > p1 > d1: the old car's pickup comes right after the new car's
  delivery. It splits the gig only past 12 hours of driving (RULES.md, "Rules for gigs"). 94-96% of the trade-ins we won rode in one gig from
  their first posting at the weight 0 (83-100% in every run); the rest were posted again as one gig, and three as single cars
  (`skeptic-notradein-s14`).
- **The room is measured to the wrong deadline.** `arrive_by` takes a private delivery's window start and the order's deadline. For a one-car
  private delivery that deadline is the booked hour + 30 (307 of 307 requests, to the minute). For a trade-in it is the old car's, so the
  model sees more room than the new car has: 30.5 h against 26.1 h at the median quote. At the quote that is only 0.17 logit (quartiles 0.10-0.27, at most 0.73), because
  room enters as log(1 + hours). With the hour known (fa0d0bb, one line, reverted in 6b2089d), the 7 trade-ins won on tune+wide are the same
  orders with the same ends, and the week is -182 (se 98) through the change in the queue. The -3.35 was therefore not covering for this error.
  It is right to fix only together with the weight, and that is two changes.
- **A booked driver who will be late says nothing.** The new car's pickup is a dealer site whose window runs to the option's deadline. A
  driver whose day slips is still "inside the window" for the pickup, so no `driver_late` comes, and the booked hour is missed (11 of 25-32
  late ones). A pickup window that ends at `lastPickupAt` would bring the warning. It would not bring a driver, and late trade-ins posted at
  the urgent fee were on time 1 in 17. Untested.

## 3. Proofs

- Python 3.9: `python3 -c "import ast,sys; [ast.parse(open(f).read(), feature_version=(3,9)) for f in sys.argv[1:]]" dispatch/*.py tools/tradein_study.py` passes.
- Restart test: not run. No candidate won.
- `dispatch/` at the head of `research/tradein` = 8ae61c5 (`git diff 8ae61c5 -- dispatch/` is empty). The branch adds `tools/tradein_study.py` and this file.
