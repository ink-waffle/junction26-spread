# A simpler system that starts the week at full speed (Saturday 20:30–22:40, branch `research/simple`)

The question: is the slow Monday ours, which numbers can go or be learned in the week, and what does that cost on weeks nobody has played?
Everything below prints again:

```sh
python -m tools.weekdays final-fresh skeptic-base-s14          # orders won by weekday, saved runs
python -m tools.start_study final-fresh                        # the price of a late order hour by hour, Monday against the other days
python -m tools.trust_study final-fresh                        # dealers' trust through the week
python -m tools.replicates simple-main-s14,simple-main-s13 simple-D-s14,simple-D-s13   # the candidate against the frozen main, halal-97..128
```

## 0. Verdict

**Recommend D, commit 892fdaf on `research/simple`: `main` minus 64 fitted numbers, nothing added.** The 60-number place table of the prior, `known`/`KNOWN` of the on-time model, and the dealer and pickup-today parts of the level are deleted; 65 numbers remain of 129.

| On halal-97..128 (never played before), strides 14 and 13, 64 samples a side | frozen main | D | difference (paired se) |
|---|---|---|---|
| margin a week | €15,798 | €15,755 | −43 (189) |
| on time, mean | 96.28% | 96.42% | +0.14 point (0.09) |
| on time, worst sample | 93.9% | 94.5% | |
| ranked | 64 of 64 | 64 of 64 | |
| orders Monday / Wednesday | 72 / 89 (0.81) | 76 / 90 (0.85) | |

- **Proven for D:** the table above; restart test on halal-02 with 12 restarts: the same week to the cent (€20,906.24 with and without restarts; 11 of 12 rebuilt desks identical, the twelfth differs in one unsent quote by €1, 34,600 → 34,500: a quote still in the outbox is priced again at the restart, after the events of its batch; not looked into further, the week's money is the same); `dispatch/` parses as Python 3.9; the judged tree is the committed tree (`diff -r`).
- **Not proven for D:** a no-stride play of the 32 weeks (strides 14 and 13 only); a rehearsal of the live loop on this commit. D changes no code path of the live loop (`desk.py`, `run.py`, `books.py` are `main`'s).
- **It is a choice between equals.** D does not earn more than `main`; it is the same result with half the numbers, and a jury reads less. If the orchestrator prefers not to touch a system that ran three rounds, `main` as frozen loses nothing measurable.

**Do not take the two changes that look like free money on our own weeks:**

- **Deleting the learner** (`Fleet.learned`; +€509, se 221, here; +€778 on halal-65..96): it costs 0.33 point of on-time in weeks like ours, and in a world one logit harder than the model it is the difference between −1.0 and −2.8 points of on-time, with a week at 90.5% (section 4). It is the part that answers the fear behind this task.
- **Centring the model's level** (+0.88): no gain at equal on-time (−€195, se 184, with the target at 97.5% and the learner unclamped; 64 samples), and with the clamp kept the worst week of a world two logits harder falls from 92.6% to 91.3%.

**What the question's premises turned out to be:**

- *"Mega overfitting."* Not in the level: the frozen system earns €14.4k, €15.2k and €15.8k a week on three sets of 32 weeks it never saw (160 plays, all ranked, worst 92.8%). Half of its numbers can be deleted without a measurable loss, which is what D does.
- *"The week starts slowly."* True as −15 to −20% on Monday (not a half), and mostly not ours: Monday's dealers have no trust in us yet and pay 12% less (section 1). A Monday as fast as a Wednesday can be had in three ways (count the order's worth in trust; centre the model's level; the same with the learner): each buys 10–20 orders on Monday and none buys margin at equal on-time (sections 2 and 4).
- *"Next time they move something we end up at the bottom."* Measured by making the model wrong about the world: with the learner, a model one logit too easy costs 1.0 point of on-time; the frozen main with its own level moved two logits loses 1.1 points and every week stays ranked. The 20:00 test final ended 18th of 75 (€15,752 by the night log; on the saved board at world minute 10,800 €13,666 against €13,968–15,892 for ranks 2–12): one week's spread (sd of a week €4,000), not a fall.

## 1. Where Monday's orders go (saved runs, no new plays)

| Weeks | Mon | Tue | Wed | Thu | Fri | Mon / Wed |
|---|---|---|---|---|---|---|
| frozen main, halal-33..64, no stride (`final-fresh`) | 72.5 | 81.2 | 84.4 | 90.0 | 77.3 | 0.86 |
| frozen main, halal-65..96, stride 14 / 13 (`skeptic-base`) | 72.5 / 71.3 | 89.1 | 89.8 / 88.7 | 90.4 | 75.9 | 0.81 / 0.80 |
| frozen main, tune + wide, stride 14 / 13 (`orch-base`) | 75.0 / 76.2 | | 90.3 / 90.3 | | | 0.83 / 0.84 |
| the 20:00 test final (live clock, one week) | 49 | 99 | 73 | 109 | 94 | 0.67 |

- **The slow Monday is in practice weeks too, as −15 to −20%, not as a half.** Monday is the week's lowest day in 34 of 64 unseen weeks, and its spread is wide: in 11 of 64 weeks Monday is at 0.55 × the week's median day or under. The test final's 49 is an ordinary bad Monday.
- **Most of it is the world.** A dealer accepts 1% more for each order we delivered to it on time, up to 25 (the rules of level 8). The dealers' level fitted per weekday on the 32 fresh weeks (slope held): × 1.33 of the list price on Monday, × 1.38 on Tuesday, × 1.50 from Wednesday; net of trust it is the same on all three days. Monday's dealers pay 12% less, so fewer requests clear our cost: we win 32% of Monday's requests at 1.30 × list and 42–45% of Wednesday's at 1.45–1.49 ×.
- **A part is ours: the price of a late order in the week's first hours.** `late_price` divides the late orders the books expect by 20 + the orders so far. On Monday at 10:00 the week has 13 orders, 6 of them without a driver yet, each counted as a fifth of a late order: the price of a late order is €2,356 in the mean and €1,500 or more in 53% of weeks (Tuesday to Friday: €465–789, 1–11% of hours), and a quarter of that hour's quotes are above 2.9 × list (Tuesday: 1.64 ×). In the test final the desk sold nothing between 12:00 and 15:00 on Monday (0 of 75 requests; median cheapest quote €200–242 against €80–100 before and after) with 13 orders in the books and 3 without a driver. Without `known` (which makes the model 1.15 logits more pessimistic on the week's first bookings) the same replay gives €1,246 and 31% at 10:00, and the rest of Monday as any other day (`tools.start_study`).
- **What it is worth:** a flat price (`skeptic-flat300`) wins 80 orders on Monday, no `known` 78, against 72.5: 6–8 orders, about €200–300 a week. The larger sum is in the trust itself (section 2).

## 2. Trust is bought on Monday and Tuesday, and the desk does not count it

`python -m tools.trust_study final-fresh` (frozen main, 32 fresh weeks):

- Requests are concentrated: about 40 dealers a week, the largest sends 30% of all requests, the five largest 62%.
- A request from a dealer at 25 is won 51.5% of the time at 1.57 × list; one from a dealer under 5 orders 34.5% at 1.31 ×. 57% of the week's requests arrive at trust under 5, 13% at 25.
- The largest dealer ends Monday at 2.8 counted orders, Tuesday at 16, and is at 25 by Wednesday night in 59% of weeks; the second and third largest are at 14 and 12 on Wednesday night and never reach 25.

The quote maximises this order's margin only. So we tried the rule that counts the trust: an order is worth, beyond its margin, 1% of its price on each later request we expect to win from that dealer this week (the dealer's rate of requests so far; at most the orders until its 25th), and the quote maximises margin plus that worth. No number in it is fitted. Tune + wide weeks, stride 14, one sample against the frozen main (`simple-T-s14`, `simple-T-half-s14`, `simple-T-floor-s14`):

| Rule | margin (se) | on time | Monday orders | Monday / Wednesday |
|---|---|---|---|---|
| frozen main | | | 75 | 0.83 |
| the whole worth counted | −€479 (283) | +0.08 | 91 | 1.02 |
| the same, never under cost | −€323 (276) | +0.04 | 89 | 0.99 |
| half the worth counted | +€122 (210) | −0.03 | 81 | 0.89 |

- **Monday can be bought to full speed, and it does not pay.** Sixteen more orders on Monday move the largest dealer from 3.4 to 4.4 counted orders on Monday night and from 16 to 19 on Tuesday night: trust arrives with the delivery, a late order halves it, and the drivers of a Monday are the same whatever we quote. The team's own earlier trial said the same (night log, "Trust as an asset": 27 more orders, margin unchanged). **The rule is not in the candidate.**
- So a Monday at 0.8–0.85 of a Wednesday is, for the most part, the right price for Monday. "As many orders on Monday as mid-week" is not a goal that earns: section 4 shows the second way to reach it (a model that is not pessimistic on Monday) buys volume and gives the money back in on-time.

## 3. The parts, and what was deleted

Candidate **D** (commit 892fdaf) is `main` minus 64 of its 129 fitted or hand-set numbers. Nothing was added to `dispatch/`.

| Deleted | Numbers | Why it can go | What the deletion costs |
|---|---|---|---|
| the place table of the prior (`prior.PLACES`) | 60 | a level per pickup and delivery place, fitted on 8 worlds; the week's own answers teach the same parts (`from`, `to`, `lane`) from zero | the skeptic's single sample: −€122 (se 259); in D below |
| `known` and `KNOWN` in the on-time model | 2 | wrong sign on 64 unseen weeks (baked +0.25, they say −0.17 ± 0.06); it makes the week's first bookings 1.15 logits more pessimistic and the late price at Monday 10:00 twice what it is without | +€200 (se 232), six more orders on Monday (the skeptic) |
| the dealer part and the pickup-today part of the level | 2 | they foretell nothing on unseen weeks (−0.3 and +1.2 per mille of log-likelihood) | −€98 (se 166) and −€28 (se 209) (the skeptic) |
| **all four together = D** | **64** | | **−€43 (se 189), on time +0.14 point (se 0.09)** on halal-97..128, two strides (section 4) |

What stays, and why (one sentence each):

- **The dealer side** (`market.py`, 14 numbers): a dealer's yes is logistic in log price around a level (slope 11.92), the level is a sum of five parts learned from every answer of the week (world, day, pickup place, delivery place, lane: one prior level 0.322 and five spreads), lowered for each faster option skipped (0.085) and raised by the rules' trust (0.0105 an order); the war day and the outage day are weighed as the rules state them (−20%, +30%, 80 km); every option is quoted at the same margin. Each part foretells unseen answers in 55–64 of 64 weeks (the skeptic's replay); the prior level and the spreads only start the learning.
- **The on-time model** (`fleet.ON_TIME`, 15 weights): the chance that a car arrives on time from its room, lane length, the queue, the fee against our other fees, pay, premium, supply near both places, private delivery, an hour waited, the flu night. Without the pickup-side signs the system loses €1,702 (se 298) on unseen weeks; three signs (room, lane length, queue) carry the discrimination and the rest set whom we refuse.
- **The week's learned intercept** (`Fleet.learned`, `DOUBT`, the clamp): the one number of the driver side that a week teaches. Section 4 asks what it is for.
- **Cost = fee + risk, and the barrier** (`REFUND`, `BOOKED_LATE`, €300, `GRIP`, `CALM`, the cap): the price of a late order rises with the week's own share of late orders; it is the part that keeps the floor (a flat €300: one week at 90.3%; a flat €100: 24 of 32 weeks unranked) and it is learned in the week by construction. **The harm to the cars that wait** stays: −€2,967 without it.
- **One fee, chosen again at few moments** (5 fee steps, the urgent and late fees, the six-hour look, the last-day look): −€1,394 without the six-hour look, −€403 without the last-day look.
- **Two-car gigs** (7 numbers): −€1,444 without them. **The note grammar**: −€998 with the kit's reader. **The flu night** (`SICK`, `WELL`, one weight): +0.2–0.4 point of on-time in the hard weeks, under 2 se; it stays because it protects the floor, not the mean.

## 4. The candidates against the frozen main

**Untouched weeks halal-97..128** (nobody had played them; frozen main = `simple-main-s14`, `-s13`, from the switches tree at its defaults, three weeks checked against `orch-base-s14` to the cent). Differences are paired per week, the samples of a week averaged, se over the 32 weeks.

| System | weeks × samples | margin | against main (se) | on time | against main (se) | worst sample | samples < 93.5% | ranked | orders | Monday / Wednesday | Mon..Fri |
|---|---|---|---|---|---|---|---|---|---|---|---|
| frozen main | 32×2 | €15,798 | | 96.28% | | 93.9% | 0 | 64/64 | 430 | 72 / 89 (0.81) | 72 93 89 99 81 |
| **D** = main − 64 numbers (892fdaf) | 32×2 | €15,755 | **−43 (189)** | 96.42% | **+0.14 (0.09)** | 94.5% | 0 | 64/64 | 431 | 76 / 90 (0.85) | 76 88 90 99 83 |
| E = D + the level centred (+0.88), no learner | 32×2 | €16,307 | +509 (221) | 95.95% | −0.33 (0.11) | 92.4% | 2 | 64/64 | 473 | 94 / 95 (1.00) | 94 101 95 103 86 |
| H = D + the level centred, learner kept without its ±1 clamp, target 97.5% | 32×2 | €15,603 | −195 (184) | 96.42% | +0.13 (0.10) | 94.2% | 0 | 64/64 | 449 | 83 / 94 (0.88) | 83 97 94 100 81 |
| G = H with the clamp (stride 14 only) | 32×1 | | identical to H to the cent in 32 of 32 weeks: the clamp never binds once the level is centred | | | | | | | | |

**Tune + wide weeks** (exploration; stride 14, one sample unless said; against `orch-base`):

| System | margin against main (se) | on time (se) | worst sample | Monday / Wednesday |
|---|---|---|---|---|
| frozen main (€14,819, 96.35%) | | | 93.4% | 75 / 90 (0.83) |
| E (two samples) | +453 (234) | −0.36 (0.15) | 93.1% | 95 / 92 (1.03) |
| B = E with the learner kept | +335 (231) | −0.41 (0.21) | 94.0% | 93 / 94 (0.98) |
| E with the target at 97.5% | +244 (268) | +0.23 (0.21) | 94.1% | 89 / 90 (0.99) |
| **E, the model one logit too easy** | −40 (312) | **−2.80 (0.31)** | **90.5%** (9 of 24 weeks under 93.5%) | 124 / 108 |
| **B, the model one logit too easy** | +379 (318) | **−0.97 (0.28)** | 93.0% (3 of 24) | 118 / 102 |
| frozen main, its model two logits too easy | +152 (299) | −1.12 (0.25) | 92.6% (2 of 24) | 119 / 100 |
| G, its model two logits too easy | −837 (366) | **−1.91 (0.27)** | **91.3%** (6 of 24) | 136 / 100 |
| G without the learner's ±1 clamp, two logits too easy | −1,046 (407) | −0.92 (0.25) | 93.3% (1 of 24) | 136 / 93 |
| D, its model two logits too easy | −157 (311) | −1.09 (0.28) | 91.6% (2 of 24) | 120 / 100 |
| H = G without the clamp, in our weeks | +200 (283) | +0.28 (0.19) | 92.9% | 87 / 89 (0.97) |

"One logit too easy" stands for a world whose drivers are one logit harder than the model believes (the odds of a late car 2.7 times the model's): the weight `one` is moved, everything else plays as it is. For E, B and G the starting point is the calibrated level; for main its own fitted level, which sits 0.88 under it.

What the tables say:

1. **D is as good as main on weeks nobody had seen, with half the numbers.** Margin −€43 (se 189), on time +0.14 point (se 0.09), worst sample 93.9% → 94.5%, 64 of 64 ranked, Monday 72 → 76 orders. This is the candidate.
2. **A week can start at full speed, and it is a move along the target's own trade, not a gain.** With the model's level where unseen weeks put it (E), Monday wins as many orders as Wednesday (94 / 95) and the week 43 more; the margin is +€509 and on time −0.33 point, two samples under 93.5% where main has none. The team's own exchange rate (97% → 96.5%: +€473 for −0.5 point) makes that about +€200 at equal on-time. With the target raised to 97.5% to give the on-time back and the learner kept (H) the result is main's and D's: −€195 (se 184), +0.13 point, Monday 83 against 72, eighteen more orders a week that earn nothing. The fitted pessimism of the model's level was a safety margin under another name, as the night log found once before ("A better-calibrated on-time model").
3. **The learner is not a free deletion: it is the insurance against a week unlike ours.** In weeks like ours it earns nothing measurable (B against E). When the model is one logit too easy for the world it meets, the system without the learner loses 2.8 points of on-time (one week at 90.5%, nine of 24 under 93.5%); with the learner 1.0 point (worst 93.0%). A deletion that looks free on our weeks (+€778 on halal-65..96, +€509 here) removes the only part of the driver side that answers to a changed world within the day. **Keep `Fleet.learned`.**
4. **The fitted pessimism is a reserve, and centring the level spends it.** In a world two logits harder than the calibrated level, the frozen main loses 1.1 points of on-time and stays ranked in every week (worst 92.6%): its level starts 0.88 under the truth and its learner may move one logit more. With the level centred and the same learner (G) the same world costs 1.9 points and the worst week is 91.3%. Without the clamp the centred system holds (worst 93.3%, on time −0.9 point, but €1,046 a week poorer where main is level): if the level is ever centred, the clamp must go with it, and that is H. D in the same world: −1.1 points, worst week 91.6%, two of 24 under 93.5% as main. H is not recommended: it is a larger change than D for the same result in our weeks and no better one in the hard world.
