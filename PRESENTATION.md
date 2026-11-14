# Halal Team — Spread: the deck as text

Nine slides. Each slide is one claim (its title), the evidence, and one figure to draw.

- Everything is level 8. A week counts ("ranked") only when at least 90% of its orders are on time.
- Practice weeks: **tune** = seeds `halal-01..08` (every fitted number comes from these), **hold** = `halal-09..16`, **wide** = `halal-17..32`. No constant was fitted on hold or wide.
- The configuration described is commit `07c8f21` with the policy `{"fleet": {"early_look": 6}}` (the on-time target of 96% is the default). The Saturday 12:00 ranking round was played with it.
- `[UPDATE: source]` marks a number that can still move. `OPEN_NUMBERS.md` has the command for each one.
- Run tags in `code font` are folders under `runs/` and lines of `runs/log.jsonl`.

---

## Slide 1 — The answer: a dealer side that learns what each dealer pays, a driver side that prices each car's risk, one loop between them

**Result.**
- Final: `[FINAL: € … margin, … % on time, … orders, place … of …]`
- Best ranking round: `[BEST ROUND: Saturday 12:00, €82,785 for five weeks, on time 94.2–96.9%, 5 of 5 ranked; place … of …; House best € …; House starter …]` `[UPDATE: runs/board.jsonl + leaderboard]`
- Practice: **€16,838 a week** on our 8 tune weeks, worst week 94.7% on time; **€13,057 a week** on 18 weeks we never fitted on, worst week 91.5%; 26 of 26 weeks ranked `[UPDATE: fleet2-base-look6 = main-m9-look6-ot96, and its -hold and -wide runs]`. The kit starter: −€72,613 and 45.5% on time on its own seed (`spread-1`), not ranked.

**The big ideas** (one slide each):
1. One flat fee per gig, because drivers learn.
2. A car costs its fee plus its risk of arriving late. That cost alone decides which cars we want.
3. Each dealer's price level is learned from every yes and no. The quote maximises (price − cost) × P(yes).
4. The practice world is deterministic, so we bisected the competitor.
5. The queue of cars without a driver is the scarce thing: a second look, and two cars in one gig.
6. Notes are read by a small grammar.

**Figure: the system in one picture.**

```
 the world's events
        │
        ▼
     BOOKS      state = a fold over events and acknowledged actions. Decides nothing.
        │
   ┌────┴───────────────────────────────┐
   ▼                                    ▼
 MARKET                               FLEET  (+ NOTES: when can the car really be collected?)
 "what will this dealer pay?"   ◄──   "what does this car cost us?"
 P(yes | price), learned from          cost = fee + risk of a late car
 every yes and no                      │
   │                                   ▼
   │ quote = argmax (price − cost) × P(yes)        gig: stops, windows, one flat fee
   │                                               PAIRS: two cars, one gig
   └──────────────┬────────────────────┘
                  ▼
        actions, quotes first ──► world ──► its answers ──► journal
```

One turn, the same in practice and in the final: fold the events, move the clock, issue the actions that make the world match the plan. A restart replays the world's log and the journal through the same fold.
1,785 lines of Python, standard library only, 10 modules `[UPDATE: wc -l dispatch/*.py]`.

---

## Slide 2 — Drivers learn that fees rise, so every gig has one flat fee

**The idea.** A gig is posted with a fee schedule of one step. The fee is chosen again only at four named moments: six hours in the app without a driver, the last day before the last possible pickup, the deadline warning, a lost driver. Never on a timer.

**Why.** The kit starter raises the fee 10% an hour to 1.5 × the typical fee. On Monday its 186 bookings came a median 7 minutes after posting, at 1.0 × typical. From Tuesday the median booked fee was exactly the cap, 1.5 ×. From Friday it was 2.5 ×. The starter paid €118.6k in fees on €71.3k of revenue (`spread-1`).

**The effect.**
- Starter: fees 1.67 × typical, −€72,613, 45.5% on time. One flat fee on the same kind of quotes: fees 1.15 × typical (`smoke`, halal-01). These are not the same week `[UPDATE: starter on halal-01..08, see OPEN_NUMBERS]`.
- Same weeks, our own test of a fee that rises once (every gig at 0.6 × for 30 minutes, then 1.15 ×; tune, `offers-q1` against `base1`): fees −3.6%, but orders that reach the deadline warning 8.8% → 12.2%, weeks ranked 5 of 8 → 3 of 8. Cars with 24–36 hours of room waited 724 minutes at the 90th percentile instead of 102.

**Figure.** Bar chart, x = weekday of the starter's week, y = median booked fee as a multiple of the typical fee: Mon 1.0, Tue 1.5, Wed 1.5, Thu 1.5, Fri 2.5. A dashed step line marks the cap of the starter's schedule (1.5 ×, then 2.5 × after the deadline warning). A flat line at 0.94 × marks our average fee `[UPDATE: main-m9-look6-ot96, column fee]`. Caption: "Monday: 7 minutes to a booking at 1.0 ×. Tuesday: drivers wait for the cap."

---

## Slide 3 — A car booked before its deadline warning is on time (96% against 25%), so a car costs its fee plus its risk

**Why.** Eight weeks with random prices and random flat fees (`explore1`):
- A car booked before its deadline warning was on time 96% of the time. A car that was not: 25%.
- A higher fee stops helping. Share booked before the warning at a flat 0.70 / 0.85 / 1.00 / 1.15 / 1.30 / 1.50 × typical: 39 / 61 / 81 / 91 / 88 / 91%. Above 1.15 × what is left is the car: its hours of room, the lane, premium, trade-in, the drivers near the delivery, our own queue.

**The idea.** An on-time model (12 weights, fitted on our own weeks by `tools/fleet_fit.py`) gives P(late) for a car at a fee. The fee is the step that costs least in all. The cost that the dealer side sees is that fee plus the risk. There is no list of forbidden cars: a car we should not win gets a cost that no dealer pays.

**The effect.** Same quotes, same tune weeks (`base1` → `fleet-v3`). Before: four hard rules (at least 8 hours of slack; no private pickup, no trade-in, no premium car) and a flat 1.15 × fee. After: the cost alone.

| | margin a week | on time, worst week | weeks ranked | fee × typical |
|---|---|---|---|---|
| hard rules | €6,824 | 83.9% | 5 of 8 | 1.17 |
| cost = fee + risk | €9,613 | 93.8% | 8 of 8 | 1.08 |

Then the dealer side dropped its own reserve on top of the cost, because the cost already prices scarcity (`main-m4-r0.3` → `main-m4-r0.0`): €10,280 → €12,711 a week, 207 → 342 orders, worst week 96.2% → 94.4% on time.

**Figure.** Left: two bars, "booked before the deadline warning: 96% on time" and "not booked before it: 25%". Right: the curve of the six points above (x = fee × typical, y = share booked before the warning), flat after 1.15 ×. Below, the rule:

```
P(late)  from a logistic model of: the gig's fee against the fees of our other open gigs, hours until the
         last possible pickup, lane length, premium, trade-in, drivers who live near the delivery, cars
         already waiting, an hour already waited; plus one number per week, learned from the week itself
fee   =  the step f of {0.85, 1.0, 1.15, 1.3, 1.5} × typical fee with the lowest
         f + P(late | f) × (refund + λ) + harm to the cars that already wait
cost  =  fee + P(late) × refund + (P(late) − 4%) × λ + harm
λ     =  €300 × (late orders we expect this week ÷ 4% of orders)⁴      €19 at half the allowance, €300 at it
```

---

## Slide 4 — A dealer's price level is learned online as a sum of parts; the quote maximises (price − cost) × P(yes), and every option goes at the same margin

**Why.** With random quotes on 8 weeks (`explore1`), the price at which half the quotes win was 1.20–1.49 × list price by world, and 1.01–1.78 × by world and day (the price war day, the outage day). A fixed 1.45 × list won 177 cars in one world and 485 in another.

**The idea.**
- A dealer says yes with a chance that is logistic in log(price ÷ list price) around a level.
- The level is a sum of parts: the world, the day, the dealer, the pickup place, the delivery place, the lane, the pickup place today. The two place parts start from a table of 60 numbers fitted on our tune weeks; the others start at zero. Two terms are known, not learned: +1.05% per order delivered on time to this dealer (trust), −8.5% per step slower than the fastest option.
- Every yes and no moves each part it touched by one Kalman step. By 10:00 the day's part is within 5% of its end-of-day value, also on the price war day.
- The quote: the option and price with the highest (price − cost) × P(yes). Every other option is quoted at the same margin over its own cost. The dealer chooses its speed. We earn the same whichever it takes.

**The effect.**

| same weeks | before | after | on time, worst week |
|---|---|---|---|
| fixed 1.45 × list → learned level, tune (`base1` → `market-r30`) | €6,824, ranked 5 of 8 | €10,367, ranked 7 of 8 | 83.9% → 89.1% |
| one option → every option at one margin, tune (`market-m8-best` → `main-m8`) | €14,203 | €14,987 (7 of 8 weeks up) | 93.3% → 93.9% |
| the same on hold (`market-hold-best` → `main-m8-hold`) | €10,795 | €12,170 (5 of 8 weeks up) | 91.5% → 91.3% |

**Figure.** The formula, with a small sketch beside it: x = the hours of one week, y = the level as a multiple of the list price; a step line that changes each morning and drops about 20% on the price war day; dots for our quotes (filled = yes, empty = no) that close in on the line within the first hour of each day.

```
P(yes | price) = σ( 11.9 × ( level − ln(price ÷ list price) ) )          flatter while the level is uncertain
level          = world + day + dealer + pickup place + delivery place + lane + pickup place today
                 + 1.05% × on-time orders of this dealer − 8.5% × steps slower than the fastest option
for each option:   best price = argmax over 0.80…3.50 × list of (price − cost) × P(yes | price)
quote:             margin m of the best option; every option at  cost of that option + m
                   nothing earns → 10 × list on the first option (a decline costs nothing)
```

---

## Slide 5 — We bisected the competitor: the practice world is deterministic, so replaying Monday brackets each request's price threshold (median bracket 0.5%)

**The idea.** The same seed and the same actions give the same week to the cent. On Monday nothing we do feeds back: the competitor moves only each morning, and trust needs deliveries. So we play Monday 16 times. Each time every request is quoted at the middle of its bracket, and no gig is posted. The dealer's yes or no halves the bracket. Result: 10,181 options of 5,581 Monday requests in 24 worlds; 87.7% known within 3%, median bracket 0.5% (`tools/probe.py`; `python -m tools.probe_read` reprints every figure below except the replay in euros).

**What it proved.**
- **No money is left in price precision.** Exact replay of Monday on 7 tune worlds: our learner earns €2,103; an oracle that knows every lane's level, €2,065; an oracle that knows every request's threshold, €3,723. Inside one world and lane a request still has its own factor of 8.2% (sd). Nothing in the request predicts it (typical fee, car, note, opening hours, hour of the day: every |r| < 0.1).
- **The dealer's rule.** Offered two options that it would each buy alone, a dealer takes the one with the largest (threshold − price) in euros: 98.1% of 2,397 probed menus, 100% when the two differ by more than 1% of the list price. This is why every option goes at one margin (slide 4).
- **Speed is worth euros per dealer, not percent.** Same day over next day: median €14.5 (quartiles €9.5–19.9), and inside one dealer the spread is €0.39. Next day over within 3 days: €6.1.
- **Trust, measured.** Tuesday's thresholds after two different Mondays (546 requests): +0.9% per on-time order (the rules say 1%). The competitor's answer to our wins is small: −4% per unit of the dealer's Monday share that we won.

**What it killed.** A lane table and a dealer table carried from other worlds (other worlds predict a lane's level with r = 0.38 and a dealer's with r = 0.01; both tables made the fit worse). Step pricing "just under the threshold" (inside a lane the yes is a logistic, not a step). Learning each dealer's value of speed (+1–2% in the replay; not shipped).

**Figure.** One request as a ladder of passes: a vertical axis "price × list" from 0.5 to 2.5; pass 1 at 1.50 "no", pass 2 at 1.00 "yes", pass 3 at 1.25 "yes", pass 4 at 1.37 "no", … the bracket shrinks to a tick at 1.31 ± 0.5% (example numbers; a real request can be read from `runs/bisect/halal-01.json`). Beside it, three bars of euros per Monday: €2,103 (ours), €2,065 (knows every lane), €3,723 (knows every request).

---

## Slide 6 — The queue of cars without a driver is the scarce thing: a second look at a gig that sits, and two cars in one gig

**Why.**
- Drivers are not the limit up to about 340 orders a week: the same requests won at 207, 272 and 342 orders a week were booked before the warning 92.7%, 92.6% and 92.4% of the time.
- Almost all late orders were one tail: 26 orders a week sat a median 70 hours at the lowest fee and were raised only at the deadline warning, 3 hours before the last possible pickup. 52% of them arrived late. A car that sits also keeps the queue long, so every new car looks risky and dear.
- The typical fee of a trade-in (one car out, one car back) is 0.50 × the two single typical fees (175 requests). So the trip home is half of a driver's cost.

**The idea.**
- (a) **Second look.** A gig with no driver after six hours in the app has its fee chosen again by the same model, at least one step up.
- (b) **Two cars in one gig.** A new one-car order stays out of the app for at most 30 minutes. If another car's pickup is within 30 km of its delivery, with at most 5 hours of planned driving and windows a driver can meet with at most 1 hour idle, both go as one gig at 0.70 × the two typical fees (0.85 × when the partner already sits in the app without a driver). No driver in 60 minutes, or a deadline warning: the gig is withdrawn and each car goes alone.

**The effect.**

| the same 8 tune weeks | margin a week | orders | on time, worst week |
|---|---|---|---|
| no pairs (`offers-m8-nopairs`) | €13,843 | 322 | 95.1% |
| + two new cars in one gig (`main-m8`) | €14,987 | 359 | 93.9% |
| + a car that sits joins a new car, target 95% (`offers-m8-board`) | €15,882 | 396 | 93.9% (one hold week 89.7%) |
| the same, target 96% (`offers-m8-board96`) | €14,935 | 350 | 94.5% |
| + second look after six hours (`main-m9-look6-ot96`) | **€16,838** | 438 | 94.7% |

On 4 hold weeks the second look gives €13,016 → €14,588 a week; the worst week goes from 93.7% to 92.2% on time `[UPDATE: main-m9-look6-ot96-hold, 4 of 8 weeks played]`.
In the final configuration 26% of cars are delivered in a two-car gig, at 0.80 × typical and 99.3% on time. Cars never paired: 0.97 × and 93.5% `[UPDATE: tools.offers_study paired main-m9-look6-ot96]`.

**Figure.** Top: a map sketch of one pair: car 1 from A to B, car 2 from B′ to C, B′ within 30 km of B, one driver, one gig, "0.70 × (typical 1 + typical 2)"; beside it the trade-in fact "out and back = 0.50 × two singles". Bottom: the timeline of one gig: posted at fee f → 6 hours without a driver: fee chosen again → last day before the last possible pickup: again → deadline warning (3 hours before it): 1.6 ×.

---

## Slide 7 — Notes: a small grammar reads 22,099 of 22,099 labelled notes; failed visits fell from 10.6 a week to 0

**Why.** 41% of requests carry a note, in Finnish, Swedish or English, with typos and corrections. The world acts on the note whether we read it or not. A driver who comes too early is a failed visit (at least €25). The kit's keyword reader got 80.0% of notes right (facts: 50.7% precision, 40.4% recall), and we paid 10.6 failed visits a week.

**The idea.** note → clauses (cut at punctuation) → words → cues, clock times and days → one fact per clause. The cues are one vocabulary of stems in three languages; one typo is forgiven in a word of six letters or more. A correction replaces a time, a denial deletes it. The facts become the gig's stop windows and audience: no driver before the car is ready or released, at a site that is really closed, after the note's deadline, or without plates or the licence for a manual car.

**The effect.**
- Reader (`python -m tools.notes_eval`): 22,099 of 22,099 notes right on 50 labelled worlds, 6,152 facts at 100% precision and recall. 26 of those worlds were never seen while building it: first shot 2 misreads in 11,432 notes. Hold worlds: 3,539 of 3,539 (first shot 3,538). With one more random typo in every note: 99.69%.
- Same weeks, same commit (tune, `base1` → `notes-v1`): failed visits 10.6 → 0.0 a week; €6,824 → €7,661; late among orders with a note fact 19.2% → 12.1%.

**Figure.** One real note, read left to right (world `halal-03`, Friday 09:46):

```
"Liike auki arkisin klo 7-20. Huolto kesken, valmis klo 15, ei kun klo 14. Lisäksi 4 kesärengasta tavaratilassa"

clause 1   auki + 7-20                 → pickup site really open 07:00–20:00
clause 2   valmis + 15, "ei kun" 14    → the correction replaces 15: car ready Friday 14:00
clause 3   kesärengasta + tavaratilassa → summer tyres as cargo: no fact
gig        pickup window starts Friday 14:00, inside 07:00–20:00
```

Second line on the slide, with a typo: `"Buyer pays first, pcikup from 14:00"` → released after payment, Monday 14:00.

---

## Slide 8 — Robust: 26 of 26 practice weeks ranked, 18 of them never fitted on; a restart replays the log into the same desk

**Many weeks.** Final configuration, level 8:

| weeks | played | margin a week | on time: worst week (mean) | ranked |
|---|---|---|---|---|
| tune `halal-01..08` | 8 | €16,838 | 94.7% (95.4%) | 8 of 8 |
| hold `halal-09..16` `[UPDATE: main-m9-look6-ot96-hold]` | 4 of 8 | €14,588 | 92.2% (93.7%) | 4 of 4 |
| wide `halal-17..32` `[UPDATE: main-m9-look6-ot96-wide]` | 14 of 16 | €12,619 | 91.5% (95.1%) | 14 of 14 |
| ranking round Saturday 12:00, 5 secret weeks `[UPDATE: place, House best]` | 5 | €16,557 | 94.2% | 5 of 5 |
| ranking round Saturday 09:00, the system before the menu of options, pairs and the second look | 5 | €9,772 (House best €10,132) | 93.5% | 5 of 5 |
| kit starter, `spread-1` `[UPDATE: starter on our seeds]` | 1 | −€72,613 | 45.5% | 0 of 1 |

The 6 missing weeks were not played: the harness lost the server three times in a row on each (timeouts under our own load, and a restart with HTTP 502). Unseen weeks earn 22% less than tune weeks and their worst week is 3 points lower: this is why the on-time target is 96% and not 90%.

**A restart.** State is a fold over the world's events and the actions the world acknowledged (a journal on disk). A new desk replays both and is the desk that died. `tools/restart_test.py` compares every object and then the week's margin:

| system | seed | restarts rebuilt identically | week with restarts against without |
|---|---|---|---|
| first version | halal-01, halal-03 | 12 of 12, 16 of 16 | €6,088.69 and €4,958.52, identical |
| Saturday morning's merged system | halal-02 | 12 of 12 | €16,359.75, identical |
| after the fleet began to learn inside the week (a bug: its memory was not in the journal) | halal-09 | 1 of 12 | €16,942 against €19,251 |
| fixed, commit `ae60d61` | halal-09 | 11 of 12 | €17,404.93, identical |
| commit `07c8f21`, default policy `[UPDATE: restart_test with the final's policy]` | halal-02 | 12 of 12 | €20,151.83, identical |

**A slow network and a surprise.** In the final a request must be answered within 4.5 real seconds.
- A whole week at the final's clock from a laptop on a phone hotspot: 0 of 1,038 requests unanswered; a quote took 69 ms at the median and 1,102 ms at most; €8,668 against €8,665 for the practice loop (halal-01).
- With 1.5 seconds added to every request: 0 unanswered.
- A Thursday join with a dead resolver, two cut streams, a lost request, 90 seconds without a route and a kill: the desk rejoined by itself three times; 94.8% on time on what it won.
- On the cloud machine (10 ms from the server), a week at 4 × the final's clock with one `kill -9`: 1 of 1,038 requests unanswered.
- Test finals: `[TEST FINAL 14:00: € …, … % on time, … of … requests quoted]` `[TEST FINAL 20:00: …]`

All rehearsals above were measured on Saturday morning's system, before the menu of options, the pairs and the second look `[UPDATE: rehearse on the final commit]`.

**Figure.** The table of weeks as a dot plot: x = on-time share from 88% to 100% with a red line at 90%, one dot per week (26 dots, three colours for tune, hold, wide), y = margin. Beside it a two-line diagram: "world's log + journal → fold → desk" drawn twice, once for play and once after a restart, with an equals sign between the two desks.

---

## Slide 9 — What did not work, and what would break the system

**Did not work** (same weeks unless said):

| tried | result |
|---|---|
| Direct offers to the likeliest drivers, for every gig unbooked for 20 minutes | 75,390 offers, 85 yes (0.11%). €6,723 against €6,824 a week. In a separate run of random offers, 0 of 556 sent after a deadline warning were accepted. Dropped. |
| Opening low (0.6 × for 30 minutes, then 1.15 ×) | Fees −3.6%, weeks ranked 5 of 8 → 3 of 8: drivers learn to wait. |
| Winning trade-ins at a higher fee | On time 17% / 38% / 61% at ≤ 1.0 / 1.15–1.3 / 1.5–2.0 × typical (83 orders). Not worth winning at any fee we tried. |
| A better-calibrated on-time model (predicted late 10.3% → 9.0%, realised 6.0%) | €14,973 → €12,707 a week. It accepts more risk on Monday; the late cars show two days later; the price of the minimum then cuts volume for the rest of the week. |
| Trust as an asset (a euro from a dealer still building trust counts for more) | 27 more orders a week, €12,707 → €12,682. |
| Pricing a car cheaper when a partner for it waits | 44 more orders a week, −€209, worst week −1.8 points. |
| One low fee (0.85 × typical) for everything at 550 orders a week | 76.7% on time, no week ranked. Drivers choose among our own gigs: a higher fee buys priority, not capacity. |
| Price tables from other worlds; step pricing | Slide 5. |

**What would break it.**
- **A week whose drivers are unlike the practice ones.** The on-time model's 12 weights are fitted on our practice weeks. A new week can move one number only (an intercept, at most ±1 logit). Late cars show two days after we accept them, so the price of the minimum reacts late. Our worst unseen week was 91.5% on time: 1.5 points above the minimum.
- **A note in words we have not seen.** A cue outside the vocabulary is missed silently.
- **The first day.** The dealer side starts from a prior. A desk that joined on Thursday sold at 1.56 × list; the desk that had played since Monday sold the same Thursday at 1.90 ×. A restart on a new machine, without the journal, has the same cost: 2–4% of the week in two early measurements.
- **Two desks on one world.** Only a lock file and a procedure prevent it.

**What we do not know.**
- Eight weeks do not resolve €500: one seed moves by €3,000 between two variants.
- The second look does teach drivers to wait a little. Gigs booked within 15 minutes at their opening fee, with the look against without: Monday the same, Tuesday −4 points, Wednesday −5, Thursday 0, Friday −9. Part of that is the bigger book (20% more gigs). It still pays on the weeks we played.
- We sell the faster option too dear. The fleet's cost asks a median 0.33 × list more for it; dealers value it at a median €14.5.

**Figure.** One bar: 75,390 direct offers, with a sliver of 85 marked "yes". Next to it the two-row list "would break it / do not know" as plain text.

---

## Appendix A — every week of the final configuration (the dots of slide 8)

Source: the harness lines in `runs/main-m9-look6-ot96.out`, `…-hold.out`, `…-wide.out`, and `runs/board.jsonl` for the ranking round. `[UPDATE: replace with the weeks of the commit and policy that play the final]`

| set | seed | margin | on time | orders |
|---|---|---|---|---|
| tune | halal-01 | €15,101 | 94.8% | 423 |
| tune | halal-02 | €21,873 | 94.8% | 465 |
| tune | halal-03 | €15,424 | 95.8% | 379 |
| tune | halal-04 | €18,424 | 95.7% | 437 |
| tune | halal-05 | €21,395 | 96.0% | 530 |
| tune | halal-06 | €13,381 | 95.1% | 431 |
| tune | halal-07 | €16,209 | 94.7% | 418 |
| tune | halal-08 | €12,894 | 96.0% | 424 |
| hold | halal-11 | €15,319 | 94.7% | 436 |
| hold | halal-12 | €18,117 | 94.0% | 401 |
| hold | halal-14 | €11,052 | 92.2% | 319 |
| hold | halal-15 | €13,863 | 94.0% | 399 |
| wide | halal-17 | €10,418 | 94.7% | 360 |
| wide | halal-19 | €12,695 | 95.2% | 330 |
| wide | halal-20 | €11,898 | 96.8% | 314 |
| wide | halal-21 | €13,725 | 95.2% | 400 |
| wide | halal-22 | €18,181 | 94.4% | 499 |
| wide | halal-23 | €11,408 | 95.2% | 374 |
| wide | halal-24 | €9,656 | 95.7% | 303 |
| wide | halal-26 | €9,155 | 92.5% | 345 |
| wide | halal-27 | €15,180 | 97.3% | 450 |
| wide | halal-28 | €16,247 | 96.8% | 402 |
| wide | halal-29 | €10,881 | 95.6% | 363 |
| wide | halal-30 | €11,730 | 91.5% | 330 |
| wide | halal-31 | €15,476 | 94.7% | 341 |
| wide | halal-32 | €10,020 | 95.7% | 351 |
| ranking round Sat 12:00 | secret week 1 | €16,672 | 94.6% | 465 |
| ranking round Sat 12:00 | secret week 2 | €17,113 | 94.2% | 380 |
| ranking round Sat 12:00 | secret week 3 | €14,525 | 96.9% | 447 |
| ranking round Sat 12:00 | secret week 4 | €21,037 | 96.7% | 517 |
| ranking round Sat 12:00 | secret week 5 | €13,439 | 94.3% | 334 |

Not played: hold `halal-09, -10, -13, -16` and wide `halal-18, -25`. The harness lost the server three times in a row on each (a restart with HTTP 502 under the hold run, read timeouts under the wide run) and gave up.

## Appendix B — the path from the first version to the final one (same 8 tune weeks)

One line per step, each against the line above it. "Merged" marks a step where several streams met, so it changes more than one thing.

| step | run tag | margin a week | on time, worst week | weeks ranked | orders |
|---|---|---|---|---|---|
| flat 1.15 × fee, fixed 1.45 × list, four hard rules | `base1` | €6,824 | 83.9% | 5 of 8 | 332 |
| + dealer's level learned online (reserve 0.3) | `market-r30` | €10,367 | 89.1% | 7 of 8 | 257 |
| merged: + cost = fee + risk, + note grammar | `main-m4-r0.3` | €10,280 | 96.2% | 8 of 8 | 207 |
| reserve 0.3 → 0 | `main-m4-r0.0` | €12,711 | 94.4% | 8 of 8 | 342 |
| + every option at one margin | `market-z-all` | €13,512 | 95.0% | 8 of 8 | 349 |
| merged: + lane and pickup-place-today parts, refitted prior | `main-m6-nopairs` | €13,337 | 94.7% | 8 of 8 | 337 |
| + two new cars in one gig | `main-m6` | €13,770 | 94.7% | 8 of 8 | 342 |
| + on-time model refitted on its own weeks, barrier price | `fleet-v9` | €14,973 | 93.9% | 8 of 8 | 357 |
| + a car that sits joins a new car, and the on-time target 95% → 96% | `offers-m8-board96` | €14,935 | 94.5% | 8 of 8 | 350 |
| + second look after six hours | `main-m9-look6-ot96` | €16,838 | 94.7% | 8 of 8 | 438 |
