# DETECTIVE: what Juhus does differently

Agent "detective", branch `research/detective` from `main` 2a36c05. Analysis of saved data only: no world was created, forked or played.
Data: the leaderboards (`runs/board-sat21.json`, the live board read at 00:50 for the closed 21:00 round and the open 00:00 round), the 20:00 test final
(`runs/lb-testfinal-sat20-end.txt`), our journals, and **the full event logs, rosters and scores of our 30 ranking worlds and both test finals**, read
with GET only (`world.events()`, `roster()`, `score()`). They are saved for anyone who wants real ranking weeks: `runs/detective/events/<world>.json.gz`.
Scripts and tables: `runs/detective/*.py`, `*.csv` (each script prints its summary; `fetch.py` is the read-only download).
Rounds here: 18:00 (season 8), 21:00 (season 9), 00:00 (season 10, still open when read: 42 ranked teams had 5 runs). "Top 10" = the median of the
ten best teams of the round other than Juhus, taken run by run.

## 0. Verdict

**Juhus wins more orders AND earns more on each, at the same on-time.** Over the 15 ranking runs it has +11% orders and +EUR 3.2 an order against
the top 10, +10% orders and +EUR 6.0 an order against us, on time 97.2% (top 10 97.3%, us 96.7%). In the test final, the only week with revenue on the
board, it delivered **45 more orders than we did for EUR 1,067 less in fees and refunds** (EUR 28,475 against 29,542): it sold at EUR 102.5 an order (top 10 102.4, us 106.8) and paid
EUR 60.7 (top 10 62.2, us 69.7). So the difference is on the driver side, and it is not a choice of fee level.

**The lead is stable, not a few worlds.** Juhus is 1st in 13 of 15 runs and never below 3rd. Its lead over the top-10 median is positive in all 15
runs: mean EUR 3,387 a run (sd 1,060, smallest +1,320). Its total is 1.19 / 1.16 / 1.26 times the top-10 median in the three rounds. Over us the
lead is +2,084 to +7,474 a run, positive in all 15.

**The fingerprint: Juhus's volume does not depend on how many drivers the world has.** Juhus wins about 470 orders whether the world has 641 or
933 drivers (slope 0.00 orders per driver). The top 10 gain 0.14 orders per driver. So Juhus's order lead over the top 10 is largest where drivers
are fewest (r = -0.72 with the driver count): +15% in the eight worlds with fewer than 780 drivers, +7.5% in the seven with more. Its per-order lead
is largest where drivers are many (r = +0.50). That is what you would see from **more cars moved per driver**. Where drivers are scarce, that
capacity becomes volume. Where they are plentiful, it becomes cheaper cars.

**None of our levers produces it.** Across 164 of our saved variants (gap, skeptic, orch, simple; 16 or more seeds each, paired against their
baseline), the change in margin per order follows **-0.13 x the % change in orders, minus 0.9**. Every lever that adds volume costs margin on each
order: at +10% orders the line predicts -EUR 2.2 an order, where Juhus is at +6.0. Only two variants are above +3% orders with a positive change
per order:

- **skeptic-flat300:** +3.8% orders and +2.14 an order, but -0.96 point of on-time.
- **skeptic-B975-s13:** +4.6% and +0.25, with on-time +0.45. That is the frozen 8ae61c5 against the older main, so it is the one step we have
  already taken in Juhus's direction. At stride 14 the same system gives +4.2% and -0.22.

The volume levers (a lower target, the recalibrated on-time model, nowaited, longer pairs) do add more orders in short worlds, as Juhus does, but
weakly: mean r = -0.20 against Juhus's -0.72. The closest in shape is orch-pair, where pairs wait 60 minutes and may drive 6 hours, so it is
itself a chain lever: r = -0.31 for orders and +0.52 for the per-order change. But it sits EUR 1.94 an order below its baseline and 0.89 point
lower on-time. **The match is weak in shape and absent in level.** Juhus is on a different frontier, not on ours with another knob. Making our
two-car pairs wait longer and drive further has the right shape and the wrong level.

**Ranked hypotheses** (section 4 has the evidence):

1. **More cars per driver trip, committed when the driver books: multi-car gigs, chains and back-hauls. Supported.** It is the only explanation that
   fits all four facts: more volume, a lower cost per car, no loss of on-time, and volume that does not depend on the driver count. The cheaper
   teams of the test final are also the more punctual ones (r = -0.65 between the cost residual and on-time). A fee level would trade those two
   against each other, as it does in our system. A capacity advantage does not. Juhus's lead over the top 10 also grows with the share of long
   (> 300 km) requests (r = +0.64). Those are the lanes where the trip home is the largest part of a driver's cost, and where we share almost no
   cars: 2% of our long-lane cars ride in a two-car gig, against 38% under 100 km.
2. **Cheaper fees through direct offers (offers2). Not supported.** offers2 measured that drivers almost never take another car after delivering
   one: 1 of 210 offers taken, 0.9 next bookings a week. Played, it lost -183 and -207. Our ranking worlds agree: only 1.6% of our bookings come
   from a driver who had delivered for us within 30 km in the 4 hours before, and we paid those the same 0.85x as anyone. Re-use has to be
   committed when the driver books, so it means gigs with several cars, not offers afterwards.
3. **Trade-ins. Weak, but cheap to test.** We decline 99% of them: we quote 4.0x list, because of the -3.35 trade-in weight in the on-time model.
   Yet a trade-in's typical fee is only 0.53x its list price (0.93x for one car), and its two legs are a natural out-and-back for one driver. Juhus's,
   the top 10's and the median team's margins all rise with a world's trade-in count (r = +0.57, +0.52, +0.62). Ours does not (+0.25). Each extra
   trade-in request goes with +EUR 280 of Juhus's lead over us, which is too large to be all causal. There are about 19 trade-ins a week.
4. **Selling slower options or other lanes. No evidence.** Juhus's revenue per order equals the top 10's (102.5 against 102.4), so there is no sign
   of a different price or option mix against the pack. Against us, it sells EUR 4.3 cheaper an order, which is consistent with its volume.
5. **A lower on-time target. Rejected.** Juhus is more on time than we are on average (97.2% against 96.7%). It does not hold a fixed target,
   though. Its on-time varies more (sd 1.5 points against 0.9) and falls in its biggest-volume runs (r = -0.64 with its own orders; 93.0% with 517
   orders in 21:00 run 4). GAP.md already showed that a lower target does not pay for us (96%: +290, with 8 of 24 weeks under 93.5%).

**What we would change first: chains, aimed where the evidence points.** That means gigs of 3 or more cars and back-hauls on long lanes, within the
rules' 12 hours, for cars that can wait for a partner (next-day and within-3-days cars). It does not mean more of our 30-minute, 5-hour,
two-car pairs: every pair knob GAP.md tried is inside the noise.

- **The bar a candidate must clear is to land above our frontier**, not just to add margin. +5% orders with a change per order of zero or better
  would be the first point of ours on Juhus's side of the line.
- **The size of the prize.** At equal lane mix, Juhus pays about EUR 3.9 an order less in fees than our 0.94x of typical. This assumes that its
  typical fee per order scales with its revenue per order and that it refunds about EUR 1.2 an order. Our shared cars cost
  about 0.18x typical (EUR 12-13) less than lone ones. So chains explain the gap if Juhus carries about 60% of its cars in shared gigs, against our 31%.
- **The upper bound from "chains".** The chains agent's upper bound on our weeks is about 265 cars a week sharing a trip, against 115 now, with
  45 chains of 3 or more cars. That covers only part of it, so the long-lane back-haul, which our 5 h limit excludes, is the part to add.

Second: a one-knob trade-in test (the trade-in weight halved, posted as one out-and-back gig), watching on-time. Do not lower the target, do not
build offers, and do not cut prices for volume: our frontier says each of these buys orders at a loss.

## 1. Juhus's signature, run by run

The money columns are EUR, orders and EUR a won order. "Drivers" is the roster size. "Level" is the price multiple of list at which we win half of
our quotes, fitted per world from our own quotes (logistic, slope fixed at -10).

| Round, run | Drivers | Level | Juhus margin / orders / per order / on time | Top-10 median | Us | Juhus minus top 10 | Juhus minus us |
|---|---|---|---|---|---|---|---|
| 18:00 #1 | 824 | 1.48 | 20,208 / 448 / 45.1 / 98.0 | 16,260 / 431 / 37.8 / 97.2 | 15,007 / 379 / 39.6 / 96.3 | +3,948 | +5,200 |
| 18:00 #2 | 810 | 1.39 | 23,264 / 504 / 46.2 / 96.8 | 19,647 / 467 / 40.9 / 97.6 | 18,119 / 467 / 38.8 / 97.2 | +3,618 | +5,145 |
| 18:00 #3 | 705 | 1.40 | 18,965 / 467 / 40.6 / 95.3 | 15,740 / 396 / 38.4 / 95.3 | 14,575 / 381 / 38.3 / 95.3 | +3,225 | +4,390 |
| 18:00 #4 | 933 | 1.31 | 14,875 / 439 / 33.9 / 98.6 | 12,988 / 407 / 29.7 / 97.7 | 12,791 / 430 / 29.7 / 97.0 | +1,887 | +2,084 |
| 18:00 #5 | 782 | 1.39 | 17,133 / 441 / 38.8 / 98.4 | 14,947 / 409 / 37.4 / 98.8 | 14,911 / 424 / 35.2 / 97.6 | +2,186 | +2,221 |
| 21:00 #1 | 923 | 1.39 | 19,096 / 487 / 39.2 / 99.0 (3rd) | 16,822 / 453 / 36.9 / 98.6 | 15,642 / 439 / 35.6 / 97.7 | +2,275 | +3,455 |
| 21:00 #2 | 641 | 1.58 | 23,792 / 491 / 48.5 / 96.1 | 20,536 / 431 / 47.0 / 95.9 | 17,339 / 447 / 38.8 / 96.0 | +3,256 | +6,453 |
| 21:00 #3 | 878 | 1.36 | 20,731 / 461 / 45.0 / 97.4 | 16,689 / 415 / 40.0 / 97.2 | 13,258 / 369 / 35.9 / 97.0 | +4,042 | +7,474 |
| 21:00 #4 | 923 | 1.52 | 24,529 / 517 / 47.4 / 93.0 | 20,775 / 488 / 43.6 / 96.8 | 18,441 / 478 / 38.6 / 95.4 | +3,754 | +6,088 |
| 21:00 #5 | 713 | 1.45 | 17,275 / 463 / 37.3 / 98.1 (2nd) | 15,956 / 426 / 36.9 / 97.8 | 14,712 / 433 / 34.0 / 97.9 | +1,320 | +2,563 |
| 00:00 #1 | 775 | 1.42 | 20,276 / 486 / 41.7 / 96.7 | 16,769 / 445 / 37.9 / 96.9 | 16,720 / 503 / 33.2 / 97.2 | +3,507 | +3,556 |
| 00:00 #2 | 761 | 1.43 | 20,853 / 473 / 44.1 / 98.3 | 16,298 / 419 / 39.3 / 97.4 | 17,410 / 463 / 37.6 / 97.0 | +4,555 | +3,443 |
| 00:00 #3 | 690 | 1.40 | 18,898 / 454 / 41.6 / 97.6 | 14,738 / 383 / 40.2 / 98.0 | 14,461 / 402 / 36.0 / 95.8 | +4,160 | +4,437 |
| 00:00 #4 | 662 | 1.48 | 23,087 / 497 / 46.5 / 96.8 | 17,869 / 421 / 43.3 / 96.7 | 16,987 / 434 / 39.1 / 96.3 | +5,218 | +6,100 |
| 00:00 #5 | 717 | 1.35 | 19,468 / 457 / 42.6 / 97.2 | 15,612 / 385 / 40.9 / 97.8 | 15,468 / 414 / 37.4 / 97.3 | +3,857 | +4,000 |

Split by drivers, as the mean over runs:

| Worlds | Drivers | Juhus orders | Top-10 orders | Our orders | Juhus per order | Top-10 per order | Our per order |
|---|---|---|---|---|---|---|---|
| Fewer than 780 drivers (8) | 708 | 474 | 413 | 435 | 42.9 | 40.5 | 36.8 |
| 780 or more (7) | 868 | 471 | 438 | 427 | 42.2 | 38.0 | 36.2 |

Test final 20:00 (one world, 859 drivers, 75 ranked teams):

| | Orders | Revenue per order | Cost per order (fees + refunds) | Margin per order | Margin share | On time |
|---|---|---|---|---|---|---|
| Juhus | 469 | 102.5 | 60.7 | 41.8 | 40.8% | 97.7% |
| Top-10 median (other teams) | 432 | 102.4 | 62.2 | 39.2 | 38-40% | 97.6% |
| Us (18th) | 424 | 106.8 | 69.7 | 37.2 | 34.8% | 97.2% |

- **Cost against revenue.** Across the 51 ranked teams with 300 or more orders, cost per order = 0.60 x revenue per order + 3.4. Juhus sits
  EUR 4.5 under that line, progresful 4.4 under, team-moonshot 7.1 under. We sit 1.8 above it: of the top 20, only we, mathnet1 and elysa are above.
- **What the residual goes with.** It goes with margin (r = -0.87) and with on-time (r = -0.65). Being cheap and being on time go together across
  teams, and orders barely move it (r = -0.23).

## 2. Which world traits go with the lead

These are traits of each ranking world from its events. Every team gets the same requests and drivers. The table gives Pearson r over 15
worlds: |r| > 0.51 is about p < 0.05, and 26 traits were tried, so expect one false hit (`runs/detective/corr.py`).

| Trait | Juhus minus top 10 (EUR) | Juhus orders / top-10 orders | Juhus minus top 10, per order | Juhus minus us (EUR) |
|---|---|---|---|---|
| Drivers in the roster | -0.29 | **-0.72** | +0.50 | -0.10 |
| Requests per driver | +0.27 | **+0.73** | -0.52 | +0.13 |
| Share of long requests (> 300 km) | **+0.64** | +0.31 | +0.18 | +0.51 |
| Market level (our m50) | +0.25 | -0.04 | -0.05 | +0.48 |
| Trade-in requests | +0.41 | +0.07 | +0.06 | **+0.70** |
| Share of our cars in two-car gigs | -0.46 | -0.14 | -0.18 | -0.42 (per order: -0.48) |
| Our fee / typical | +0.28 | -0.25 | +0.49 | +0.56 |
| Chance of a chain (another request picks up near this delivery soon) | +0.06 | +0.16 | +0.04 | +0.10 |
| Snow, bulk batch size, private stops, premium, same-day offered | small | small | small | small, except private +0.59 |

- **Against us, the lead also grows in rich worlds.** Our margin per order follows the top 10's at a slope of 0.54; Juhus's follows it at 0.93.
  Our per-order shortfall against the top 10 therefore grows with how much the pack earns per order (r = -0.73).
- **That part is confounded with our version.** The rich worlds sit in the 21:00 round, which we played with 3e1e0ef. Inside the 00:00 round,
  played with frozen 8ae61c5, there is no such pattern. Treat it as a weak lead on pricing in dear weeks.

## 3. Our levers against the fingerprint

`runs/detective/variants.py` and `levers.py` read `runs/log.jsonl` and pair each tag with its baseline on the same seeds and stride. The tags are
gap-*, skeptic-*, orch-* and simple-*, 164 of them with 16 or more seeds. For each it gives the change in orders (%), margin per order, revenue and
cost per order, and on-time. `levers.py` also gives how the per-seed change in orders and per order correlates with the seed's driver count
(seeds of 637-946 drivers).

| Lever (examples) | Orders | Per order | On time | r(orders, drivers) | r(per order, drivers) |
|---|---|---|---|---|---|
| Juhus against the top 10 | **+11.4%** | **+3.22** | -0.2 | **-0.72** | **+0.50** |
| Target 96% (gap-t96-s14) | +12.5% | -3.20 | -1.91 | -0.07 | +0.53 |
| Target 95% (gap-t95-s14) | +18.9% | -5.16 | -3.06 | -0.29 | +0.32 |
| On-time model recalibrated, no in-week learner (skeptic-calnw-s14) | +8.7% | -1.44 | -0.03 | -0.17 | -0.04 |
| No 'waited' (skeptic-nowaited-s13) | +5.7% | -0.15 | -0.28 | -0.32 | -0.22 |
| Pairs wait 60 min and drive up to 6 h (orch-pair-s14) | +5.3% | -1.94 | -0.89 | -0.31 | **+0.52** |
| Frozen 8ae61c5 against the older main (skeptic-B975-s13) | +4.6% | +0.25 | +0.45 | -0.04 | -0.31 |
| Fee floor 1.0x and target 95% (gap-f100t95) | +12.3% | -6.14 | -3.09 | -0.32 | +0.40 |
| Flat EUR 300 harm (skeptic-flat300) | +3.8% | **+2.14** | -0.96 | -0.09 | +0.01 |
| Fit over all 164 | | **= -0.13 x orders% - 0.9** | | mean -0.20 for the levers with +3% or more | |

- **Shape.** The volume levers move orders in the right direction across worlds, but at less than a third of Juhus's strength.
- **Level.** No lever reaches Juhus's level: not one adds 5% or more of orders with a positive change per order at equal on-time. The nearest is
  the system we already froze.
- **The two pair levers in GAP.md** (reach 50 km +220, drive 6 h +103) stay inside the noise.

## 4. The hypotheses, with the evidence

| # | Hypothesis | For | Against | Verdict |
|---|---|---|---|---|
| 1 | More cars per driver trip, committed when the driver books (multi-car gigs, chains, back-hauls) | Volume does not depend on drivers (slope 0.00, top 10 0.14); lead largest in short worlds (r -0.72); cheaper per car AND as punctual (test final; cheap teams more on time, r -0.65); lead grows with long-lane share (r +0.64), where we share 2% of cars; our two-car gigs cost 0.80x against 0.98x in the ranking weeks, and NIGHT_LOG idea 9 measured them at 0.71x typical and 99.6% on time (85% booked at 0.70x in a median 4 min): our shared cars already show Juhus's signature, cheaper AND more punctual; idea 9 also notes that the trip home is half a driver's cost; where we pair more, Juhus's per-order lead over us is smaller (r -0.48) | We cannot see their gigs; the chance of a chain in the request stream does not go with the lead (r 0.06) | **Supported: ranked first** |
| 2 | Cheaper drivers through direct offers | The handbook says a driver near the pickup after another gig "needs much less" | offers2: 1 of 210 offers taken, 0.9 next bookings a week, played -183 / -207; here, 1.6% of our bookings come from a driver who had just delivered for us within 30 km | **Not supported** |
| 3 | Win the trade-ins | We decline 99% (quote 4.0x list, weight -3.35); typical fee 0.53x list; every team's margin rises with the trade-in count, ours does not | Our past trade-ins were 17-61% on time (NIGHT_LOG); the slope is too large to be all causal; 21:00-round confound | **Weak; cheap to test** |
| 4 | Slower options or lane selection | Juhus sells EUR 4.3 cheaper an order than us | Revenue per order equal to the top 10's | **No evidence** |
| 5 | A lower on-time target | On-time varies more and falls in its biggest-volume runs (93.0% at 517 orders) | Mean 97.2%, above ours; a lower target loses for us (GAP.md) | **Rejected as the mechanism** |
| 6 | Dearer pricing in rich weeks | Our margin per order follows the pack's at 0.54 | Confounded with our 21:00 version; no pattern inside the 00:00 round | **Weak** |

## 5. Chains and offers2, in one line each

- **chains: supported.** Juhus's fingerprint (volume independent of drivers, cheap and punctual cars, a lead that grows with long lanes) is what
  committed multi-car gigs would produce. Aim beyond our two-car pairs: 3+ cars, and back-hauls on long lanes past our 5 h limit (the rules allow 12 h).
- **offers2: not supported.** Its own measurement (drivers stop after delivering) and our ranking weeks (1.6% natural re-use) say that re-use cannot
  be bought after the fact. It is consistent with Juhus only if Juhus's offers go to drivers who still hold a gig of theirs (offers2's 5.3% group),
  and that is too small to explain about 50 extra cars a week.

## 6. Caveats

- **Few worlds.** 15 ranking worlds and one test final.
- **Moving comparators.** The top-10 composition changes by round, and the 00:00 round was still open, so its top 10 is weaker.
- **Our own version changed by round:** 5bcf641, then 3e1e0ef, then e2d1862 = 8ae61c5.
- **The market level is ours.** It is fitted from our own quotes with a fixed slope.
- **Revenue is known for one week only:** the test final.
- **Nothing here was played.** The levers' paired deltas come from saved runs.
