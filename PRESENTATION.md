# Halal Team — Spread: the deck as text

Ten slides. Each slide is one claim (its title), the evidence, and one figure to draw.

- Everything is level 8. A week counts ("ranked") only when at least 90% of its orders are on time.
- The system described is the default policy of commit `0b050b8` (Saturday 17:35; ideas 1–14 of `NIGHT_LOG.md`) `[UPDATE: the frozen commit that plays the final]`.
- Practice weeks, and what each was used for:
  - **tune** = seeds `halal-01..08`: fitted on from the start.
  - **wide** = `halal-17..32`: their notes and Mondays helped build the note reader and the bisection; no price or fee number came from them until Saturday afternoon, when the surprise days of slide 6 were designed and fitted on tune and wide weeks together.
  - **hold** = `halal-09..16`: nothing was fitted on them. They were played to confirm, and one of them, `halal-09`, was opened to study the flu.
  - The on-time target was chosen after looking at hold weeks (96%) and then on tune and wide weeks (97%).
  - So the clean test is the 32 fresh weeks of slide 9 `[UPDATE]`.
- "Stride 14" marks weeks played with the practice clock moving 14 minutes a turn while requests arrive. A week is then three times faster to play, and our answers come up to 14 minutes later than in the final.
- One week moves by about ±1.3 points of on-time and €1,000–3,000 between two plays of nearly the same policy. So the late comparisons use 24 weeks with several samples a side (`tools/replicates.py`) and give a standard error (se).
- `[UPDATE: source]` marks a number that can still move. `OPEN_NUMBERS.md` has the command or file for each one.
- Run tags in `code font` are folders under `runs/` and lines of `runs/log.jsonl`.

---

## Slide 1 — The answer: a driver side that prices each car's risk, a dealer side that learns each dealer's price, and both weigh the events that nobody announces

**Result.**
- Final: `[FINAL: € … margin, … % on time, … orders, place … of …]`
- Best ranking round: Saturday 15:00, **€82,278** for five weeks, 5 of 5 ranked, on time 95.0–97.1%; 14th of 42 ranked teams; **1.28 × House best** (€64,249) on the same weeks `[UPDATE: the 18:00 round and Sunday's rounds, runs/board.jsonl + leaderboard]`.
- Test final, Saturday 14:00, live clock: €3,747, 97.6% on time, **2nd of 55 ranked teams** (217 entered) `[TEST FINAL 20:00: € …, … % on time, place … of …]`.
- Practice, against the kit starter on the same weeks: on the 8 weeks we fitted on, **€17,846 a week**, worst week 95.9% on time, against **−€63,232** and 52.1% for the starter (no week ranked). On 8 weeks we did not fit on, €14,806 a week, worst week 93.2%, against −€68,908 and 47.8% `[UPDATE: 32 fresh weeks on the frozen commit]`.

**The big ideas** (one slide each):
1. One fee per gig, because drivers learn.
2. A car costs its fee plus its risk of arriving late. That cost alone decides which cars we want.
3. Each dealer's price level is learned from every yes and no. The quote maximises (price − cost) × P(yes).
4. The practice world is deterministic, so we bisected the competitor.
5. Nobody announces the price war, the outage or the flu. Each side weighs which day it is.
6. Two cars in one gig: the trip home is half a driver's cost.
7. Notes are read by a small grammar.

**Figure: the system in one picture.**

```
 the world's events
        │
        ▼
     BOOKS      state = a fold over events and acknowledged actions. Decides nothing.
        │
   ┌────┴───────────────────────────────┐
   ▼                                    ▼
 MARKET                               FLEET  (+ NOTES and TIMETABLE: when can the car really be collected?)
 "what will this dealer pay?"   ◄──   "what does this car cost us?"
 P(yes | price), learned from          cost = fee + risk of a late car
 every yes and no                      │
 weighs: war day, outage day           weighs: flu day
   │                                   ▼
   │ quote = argmax (price − cost) × P(yes)        gig: stops, windows, one fee
   │                                               PAIRS: two cars, one gig
   └──────────────┬────────────────────┘
                  ▼
        actions, quotes first ──► world ──► its answers ──► journal
```

One turn, the same in practice and in the final: fold the events, move the clock, issue the actions that make the world match the plan. A restart replays the world's log and the journal through the same fold.
1,948 lines of Python, standard library only, eleven modules `[UPDATE: wc -l dispatch/*.py]`.

---

## Slide 2 — Drivers learn that fees rise, so a gig has one fee, chosen again at four named moments only

**The idea.** A gig is posted with a fee schedule of one step. The fee is chosen again only when the gig has sat six hours without a driver, when the last day before its last possible pickup begins, at the deadline warning, and when a driver is lost. At the first two it goes at least one step up. It never rises on a timer.

**Why.**
- The kit starter raises the fee 10% an hour to 1.5 × the typical fee. On Monday its 186 bookings came a median 7 minutes after posting, at 1.0 × typical. From Tuesday the median booked fee was exactly the cap, 1.5 ×. From Friday it was 2.5 ×. It paid €118.6k in fees on €71.3k of revenue (`spread-1`).
- With a fee that never moved, 26 orders a week sat a median 70 hours at the lowest fee and were raised only at the deadline warning. 52% of them arrived late. So a fee must be looked at again, but rarely.

**The effect.**
- A fee that rises once (every gig at 0.6 × for 30 minutes, then 1.15 ×), same 8 tune weeks (`offers-q1` against `base1`): fees −3.6%, but orders that reach the deadline warning 8.8% → 12.2%, weeks ranked 5 of 8 → 3 of 8.
- The look after six hours, same 8 tune weeks (`offers-m8-board96` → `main-m9-look6-ot96`): €14,935 → €16,838 a week, 350 → 438 orders, worst week 94.5% → 94.7% on time.
- Its price, measured (`tools/waiting_study.py`): new one-car gigs booked at their first fee within 15 minutes, Monday to Friday, are 73 / 71 / 65 / 67 / 48% without the look and 71 / 67 / 59 / 58 / 33% with it. Drivers do learn from one raise. More raises do not pay: a look every day, a look every six hours, and steps up to 2 × each gave between −€514 and +€236 a week on 8 weeks, which 8 weeks cannot tell from zero; a look after 12 hours instead of 6 gave −€342 on 24 weeks.

**Figure.** Bar chart, x = weekday of the starter's week, y = median booked fee as a multiple of the typical fee: Mon 1.0, Tue 1.5, Wed 1.5, Thu 1.5, Fri 2.5. A dashed step line marks the cap of the starter's schedule (1.5 ×, then 2.5 × after the deadline warning). A flat line at 0.94 × marks our average fee `[UPDATE: fee column of the final tune run]`. Caption: "Monday: 7 minutes to a booking at 1.0 ×. Tuesday: drivers wait for the cap."

---

## Slide 3 — A car booked before its deadline warning is on time (96% against 25%), so a car costs its fee plus its risk

**Why.**
- Eight weeks with random prices and random flat fees (`explore1`): a car booked before its deadline warning was on time 96% of the time; a car that was not, 25%.
- A higher fee stops helping. Share booked before the warning at a flat 0.70 / 0.85 / 1.00 / 1.15 / 1.30 / 1.50 × typical: 39 / 61 / 81 / 91 / 88 / 91%. Above 1.15 × what is left is the car and the town.
- The shortage differs from town to town. Orders with ≤ 3 / 4–15 / 16–50 / > 50 drivers living within 30 km of the pickup were late 12.6 / 10.0 / 6.5 / 3.3%. Our first model said 12% for all of them.

**The idea.** An on-time model (16 weights, fitted on our own weeks by `tools/fleet_fit.py`) gives P(late) for a car at a fee. The fee is the step that costs least in all. The cost that the dealer side sees is that fee plus the risk. There is no list of forbidden cars: a car we should not win gets a cost that no dealer pays.

**The effect.**

| same weeks | before | after |
|---|---|---|
| Four hard rules (8 hours of slack; no private pickup, trade-in or premium car) → cost = fee + risk. 8 tune weeks, same quotes (`base1` → `fleet-v3`) | €6,824, worst week 83.9% on time, 5 of 8 ranked | €9,613, worst week 93.8%, 8 of 8 ranked |
| The dealer side drops its own reserve on top of the cost. 8 tune weeks (`main-m4-r0.3` → `main-m4-r0.0`) | €10,280, 207 orders, worst week 96.2% | €12,711, 342 orders, worst week 94.4% |
| The model learns where the drivers live (both ends of the lane), and the aim goes from 96% to 97%. 8 hold weeks, stride 14 (`main-look6-s14-hold` → `fleet2-s-v2b-hold`) | €13,472, 23.1 late orders a week, 93.9% on time; weeks from 91.5% to 96.2% | €13,753, 15.7 late orders a week, 95.7% on time; seven weeks from 95.3% to 97.4%, and one at 90.7% (the flu week of slide 6) |

The last step on 16 wide weeks: €13,240 → €13,201, late orders 17.8 → 14.6 a week, worst week 92.6% → 93.5%. On weeks it was not fitted on it buys on-time, not money.

**Figure.** Left: two bars, "booked before the deadline warning: 96% on time" and "not booked before it: 25%". Right: the curve of the six points above (x = fee × typical, y = share booked before the warning), flat after 1.15 ×. Below, the rule:

```
P(late)  from a logistic model of: the gig's fee against the fees of our other open gigs, hours until the
         last possible pickup, lane length, the drivers who live near the pickup and near the delivery,
         premium, trade-in, private delivery, the typical fee as a share of the list price, cars already
         waiting, an hour already waited, the chance that the car's last day is the flu's (slide 6);
         plus one number per week, learned from the week itself
fee   =  the step f of {0.85, 1.0, 1.15, 1.3, 1.5} × typical fee with the lowest
         f + P(late | f) × (refund + λ) + harm to the cars that already wait
cost  =  fee + P(late) × refund + (P(late) − 3%) × λ + harm
λ     =  €300 × (late orders we expect this week ÷ 3% of orders)⁴      €19 at half the allowance, €300 at it
```

---

## Slide 4 — A dealer's price level is learned online as a sum of parts; the quote maximises (price − cost) × P(yes), and every option goes at the same margin

**Why.** With random quotes on 8 weeks (`explore1`), the price at which half the quotes win was 1.20–1.49 × list price by world, and 1.01–1.78 × by world and day. A fixed 1.45 × list won 177 cars in one world and 485 in another.

**The idea.**
- A dealer says yes with a chance that is logistic in log(price ÷ list price) around a level.
- The level is a sum of parts: the world, the day, the dealer, the pickup place, the delivery place, the lane, the pickup place today. The two place parts start from a table of 60 numbers fitted on our tune weeks; the others start at zero. Two terms are known, not learned: +1.05% per order delivered on time to this dealer (trust), −8.5% per step slower than the fastest option.
- Every yes and no moves each part it touched by one Kalman step.
- The quote: the option and price with the highest (price − cost) × P(yes). Every other option is quoted at the same margin over its own cost. The dealer chooses its speed. We earn the same whichever it takes.

**The effect.**

| same weeks | before | after | on time, worst week |
|---|---|---|---|
| fixed 1.45 × list → learned level, tune (`base1` → `market-r30`) | €6,824, ranked 5 of 8 | €10,367, ranked 7 of 8 | 83.9% → 89.1% |
| one option → every option at one margin, tune (`market-m8-best` → `main-m8`) | €14,203 | €14,987 (7 of 8 weeks up) | 93.3% → 93.9% |
| the same on hold (`market-hold-best` → `main-m8-hold`) | €10,795 | €12,170 (5 of 8 weeks up) | 91.5% → 91.3% |

Since the model of slide 3 knows the town, the faster option costs a median €11 more than the slower one in our quotes (€16 before). Dealers value it at a median €14.5, and we now sell the fastest option in 57% of the wins with two options (49% before).

**Figure.** The formula, with a small sketch beside it: x = the hours of one week, y = the level as a multiple of the list price; a step line that changes each morning; dots for our quotes (filled = yes, empty = no) that close in on the line in the first hour of each day.

```
P(yes | price) = σ( 11.9 × ( level − ln(price ÷ list price) ) )          flatter while the level is uncertain
level          = world + day + dealer + pickup place + delivery place + lane + pickup place today
                 + 1.05% × on-time orders of this dealer − 8.5% × steps slower than the fastest option
for each option:   best price = argmax over 0.80…3.50 × list of (price − cost) × P(yes | price)
quote:             margin m of the best option; every option at  cost of that option + m
                   nothing earns → 10 × list on the first option (a decline costs nothing)
```

---

## Slide 5 — We bisected the competitor: the practice world is deterministic, so replaying a day brackets each request's price threshold

**The idea.** The same seed and the same actions give the same week to the cent. So we play a day many times. Each time every request is quoted at the middle of its bracket, and the dealer's yes or no halves the bracket.
- Mondays of 24 worlds, 16 passes each (`tools/probe.py`): 10,181 options of 5,581 requests; 87.7% known within 3%, median bracket 0.5%. On Monday nothing we do feeds back, so a pass plays Monday alone.
- Every working day of 24 of our own weeks, on copies of the played week forked at each midnight (`tools/probe_week.py`): 24,127 thresholds within 2%.

**What it proved.**
- **No money is left in price precision.** Exact replay of Monday on 7 tune worlds: our learner earns €2,103; an oracle that knows every lane's level, €2,065; an oracle that knows every request's threshold, €3,723. Inside one world and lane a request still has its own factor of 8.2% (sd). Nothing in the request predicts it (typical fee, car, note, opening hours, hour of the day: every |r| < 0.1).
- **The dealer's rule.** Offered two options that it would each buy alone, a dealer takes the one with the largest (threshold − price) in euros: 98.1% of 2,397 probed menus. This is why every option goes at one margin (slide 4).
- **Speed is worth euros per dealer, not percent.** Same day over next day: median €14.5 (quartiles €9.5–19.9); inside one dealer the spread is €0.39. Next day over within 3 days: €6.1.
- **Trust, measured.** Tuesday's thresholds after two different Mondays (546 requests): +0.9% per on-time order (the rules say 1%). The competitor's answer to our wins is small: −4% per unit of the dealer's Monday share that we won.
- **The week's events, exactly** (slide 6): the price war day lies 0.23 log under the calm days, the outage adds 0.26 for cars that leave its region, and calm days stray by only 0.04.

**What it killed.** A lane table and a dealer table carried from other worlds (other worlds predict a lane's level with r = 0.38 and a dealer's with r = 0.01; both tables made the fit worse). Step pricing "just under the threshold" (inside a lane the yes is a logistic, not a step).

**Figure.** One request as a ladder of passes: a vertical axis "price × list" from 0.5 to 2.5; pass 1 at 1.50 "no", pass 2 at 1.00 "yes", pass 3 at 1.25 "yes", pass 4 at 1.37 "no", … the bracket shrinks to a tick at 1.31 ± 0.5% (example numbers; a real request can be read from `runs/bisect/halal-01.json`). Beside it, three bars of euros per Monday: €2,103 (ours), €2,065 (knows every lane), €3,723 (knows every request).

---

## Slide 6 — Nobody announces the price war, the outage or the flu: each side weighs which day it is, from what it sees anyway

**Why.** A level 8 week has one price war day (the competitor 20% cheaper), one outage day and region (30% dearer for cars that leave a town and the places within 80 km), and one flu day (a third of the drivers stay at home). Nobody says which.
- The dealer side used to chase them with its day part. It followed a war after a median 18 requests (09:45), and an outage after 67 requests (13:30) or never: over that day our level was a median 14% too low in the region.
- The flu shows in the first hour of its day. On one night a week, 22–57% of the bookings held for that day come back; on every other night 2.7% (`tools/night_study.py`, 24 weeks). Orders whose last day is the flu's end late 9.3% of the time, against 3.3–3.7%. Friday holds twice the bookings of other days, so a Friday flu was our week at 90–92%.

**The idea.**
- **Dealer side.** There are 600 possible weeks: 5 war days × 4 other days for the outage × 30 towns. Each answer weighs every one of them. The quote is priced against the mix that is left for today. The day part keeps two beliefs, one if today is the war day and one if it is not.
- **Driver side.** The books count, at each day's first event, the bookings held for cars to collect that day, and how many come back before 01:00. The fleet turns the nights seen so far into the chance that a given day is the flu's. The on-time model has that chance, for the car's last day, as one more sign.
- Both are functions of the event log, so a restart rebuilds them.

**The effect.**

| | before | after |
|---|---|---|
| War day named from the answers alone | — | 24 of 24 weeks, sure after a median 5 answers of that day |
| Outage day named | — | 16 of the 19 weeks where it reached enough requests |
| Requests until our level is within 5%, war day / outage day | 18 / 67 or never | 4 / 7 |
| Exact replay of 24 probed weeks (`python -m tools.surprises money`) | €12,082 a week | €12,284 (+€202, se 66; 19 of 24 weeks up; told both events at 08:00: +€300) |
| Played weeks, stride 14: tune / 16 wide (`surprise-before` → `surprise-weighs`) | €17,421 / €13,201 | €17,813 / €13,536; worst week on time unchanged |
| The flu sign, 25 weeks, 49 samples a side (`tools/replicates.py`) | — | on time +0.38 point (se 0.20), 1.6 late orders a week fewer, margin −€23 (se 232) |
| The seven weeks whose flu is Friday | — | +1.1 points; the hardest, a hold week: 92.3% → 94.6% |
| Tune without stride (`surprise-weighs-ns` → `fleet3-cand-ns`) | €17,607, worst week 93.4% | €17,846, worst week 95.9% |

**Figure.** Two rows over one week, Monday to Friday. Top row, dealer side: five boxes, each with a bar "chance that today is the war day"; by 08:30 of Thursday the Thursday bar is at 100% and the quote line drops 20%. Bottom row, driver side: at each midnight a small bar "share of the day's bookings given back": 3%, 2%, 3%, then 40% on Friday 00:30, with the note "Thursday: no such night seen yet, so Friday is 1 in 2". Formula under the bottom row:

```
P(day d is the flu's) ∝ (0.33 ÷ 0.03)^back(d) × (0.67 ÷ 0.97)^(held(d) − back(d))      over the 5 working days
sign in the on-time model = how far that chance for the car's last day is above 1 in 5
```

---

## Slide 7 — Two cars in one gig: the trip home is half a driver's cost

**Why.** The typical fee of a trade-in (one car out, one car back) is 0.50 × the two single typical fees (175 requests). So the trip home is half of what a driver is paid for.

**The idea.** A new one-car order stays out of the app for at most 30 minutes. If another car's pickup is within 30 km of its delivery, with at most 5 hours of planned driving and windows a driver can meet with at most 1 hour idle, both go as one gig at 0.70 × the two typical fees. When the partner already sits in the app without a driver, the fee is 0.85 ×. No driver in 60 minutes, or a deadline warning: the gig is withdrawn and each car goes alone.

**The effect.**

| the same 8 tune weeks | margin a week | orders | on time, worst week |
|---|---|---|---|
| no pairs (`offers-m8-nopairs`) | €13,843 | 322 | 95.1% |
| + two new cars in one gig (`main-m8`) | €14,987 | 359 | 93.9% |
| + a car that sits joins a new car, target 95% (`offers-m8-board`) | €15,882 | 396 | 93.9% (one hold week 89.7%) |
| the same, target 96% (`offers-m8-board96`) | €14,935 | 350 | 94.5% |

- In randomised tests inside the same worlds, pairs with at most 4 hours of driving at 0.70 × were booked 85% of the time, in a median 4 minutes. Their fees came to 0.89 × typical, against 1.21 × for the same cars as two gigs.
- Today 28% of our cars are delivered in a two-car gig, at 0.81 × typical and 98.8% on time. Cars never paired: 0.97 × and 96.3% `[UPDATE: tools.offers_study paired <final tune tag>]`.
- More pairs (a wait of 60 minutes, up to 6 hours of driving): +€284 a week (se 304) for −0.57 point of on-time on 24 weeks. Not adopted.

**Figure.** A map sketch of one pair: car 1 from A to B, car 2 from B′ to C, B′ within 30 km of B, one driver, one gig, "0.70 × (typical 1 + typical 2)". Beside it the trade-in fact: "out and back = 0.50 × two singles".

---

## Slide 8 — Notes: a small grammar reads 22,099 of 22,099 labelled notes; failed visits fell from 10.6 a week to 0

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

## Slide 9 — Robust: all 32 of our practice weeks ranked, where the kit starter ranks none of 16; a restart replays the log into the same desk

**Many weeks.** The system of this deck against the kit starter on the same weeks:

| weeks | ours: margin a week | ours: on time, worst week (mean) | ours ranked | starter: margin a week | starter: on time (mean) | starter ranked |
|---|---|---|---|---|---|---|
| tune `halal-01..08` (`fleet3-cand-ns`) | €17,846 | 95.9% (96.9%) | 8 of 8 | −€63,232 | 52.1% | 0 of 8 |
| hold `halal-09..16`, stride 14 (`fleet3-cand-hold`) | €14,806 | 93.2% (95.8%) | 8 of 8 | −€68,908 | 47.8% | 0 of 8 |
| wide `halal-17..32`, stride 14 (`orch-base-s14`); see the header for what they were used for | €13,418 | 93.4% (96.2%) | 16 of 16 | not played | | |
| 32 fresh weeks, frozen commit | `[UPDATE: runs/final-fresh.out]` | `[UPDATE]` | `[UPDATE]` | | | |

Secret weeks, the same for every team:

| | ours | against House best on the same weeks | place |
|---|---|---|---|
| Ranking round Saturday 09:00 (Saturday morning's system: no menu of options, no pairs, no second look) | €48,860 | 0.96 × | 35th of 45 |
| Ranking round Saturday 12:00 | €82,785 | 1.07 × | 22nd of 58 |
| Ranking round Saturday 15:00 | €82,278 | 1.28 × | 14th of 42 |
| Ranking round Saturday 18:00 and later | `[UPDATE: runs/board.jsonl]` | `[UPDATE: leaderboard]` | `[UPDATE]` |
| Test final Saturday 14:00, live clock, joined on Thursday | €3,747, 97.6% on time | first team €4,023, 10th €3,292 | 2nd of 55 |
| Test final Saturday 20:00 | `[TEST FINAL 20:00]` | | |

**How we decided late.** One week moves by ±1.3 points of on-time between two plays of nearly the same policy. So each late change was played on 24 weeks with several samples a side: the same seed at strides of 12 to 15 minutes is another sample of the same policy (`tools/replicates.py`). Then every knob of the final configuration was moved both ways on 24 weeks, two samples a side. None was worth changing: fee floor at 0.75 × typical −€771 a week (se 222), at 0.90 × −€47 (se 246); aim at 96.5% +€112 (se 176) for −0.51 point of on-time; second look at 12 hours −€342.

**A restart.** State is a fold over the world's events and the actions the world acknowledged (a journal on disk). A new desk replays both and is the desk that died. `tools/restart_test.py` compares every object, and then the week's margin: 12 of 12 restarts rebuilt the same desk, and the week ended at €20,493.78 with and without them (halal-02, ideas 1–14) `[UPDATE: restart_test on the frozen commit]`. The test caught a real bug on Saturday: when the fleet began to learn inside the week, 1 of 12 restarts matched and a week with restarts ended €2,309 lower. Since the fix every week with restarts has ended at the same margin to the cent.

**A slow network and a surprise.** In the final a request must be answered within 4.5 real seconds.
- The test final ran on a cloud machine 9 ms from the server: every request of Thursday and Friday was quoted, no action was refused, and the slowest turn took 0.86 s.
- Rehearsals with an earlier version: a whole week at the final's clock from a laptop on a phone hotspot, 0 of 1,038 requests unanswered; with 1.5 seconds added to every request, 0 unanswered; a Thursday join with a dead resolver, two cut streams, 90 seconds without a route and a kill: the desk rejoined by itself three times `[UPDATE: rehearse on the frozen commit]`.

**Figure.** A dot plot: x = on-time share from 30% to 100% with a red line at 90%, y = margin from −€90k to +€25k. 32 dots of ours (three colours for tune, hold, wide) sit right of the line and above zero; 16 starter dots (tune and hold) sit far left and far below. Beside it a two-line diagram: "world's log + journal → fold → desk" drawn twice, once for play and once after a restart, with an equals sign between the two desks.

---

## Slide 10 — What did not work, and what would break the system

**Did not work.**

| tried | result |
|---|---|
| Meeting the drivers on the day: keep a car out of the app until 07:00 of its last day. Randomised by order number inside 9 worlds | The kept half ended late 11.1% against 7.0%, and 30% against 15% in the flu's night. A weak promise is far better than none. |
| A rule for the night of the flu: when five orders lose their driver within an hour, reopen at the fee of a deadline warning | Late among those cars 14% → 10% on tune and wide weeks, nothing on hold weeks. Not taken; slide 6 weighs the night instead. |
| A crisis price, to win safe cars after a bad night | −€481 a week on 14 weeks, on time unchanged. |
| A better-calibrated on-time model (predicted late 10.3% → 9.0%, realised 6.0%) | €14,973 → €12,707 a week. It accepts more risk on Monday, and the late cars show two days later. |
| A finer fee grid (steps of 0.05 from 0.8 to 1.2 × typical) | −€624 a week (se 284) on 24 weeks. |
| Finding the flu by a census: a direct offer that pays nothing, to every driver each day | Names a silent day in 7 of 20 weeks, but it is the night that takes our bookings in only 2 of them. |
| Opening low (0.6 × for 30 minutes, then 1.15 ×); one low fee for everything; trade-ins at a higher fee | Slide 2; 76.7% on time at 550 orders a week; trade-ins on time 17–61% at any fee we tried. |
| Direct offers to the likeliest drivers | 75,390 offers, 85 accepted. €6,723 against €6,824 a week. |

**What would break it.**
- **A week that is not the rules' week.** Slide 6 assumes one war day, one outage, one flu night. In the replay a week without a war still gains €66; without both events it loses €118. A flu on Monday shows no night before it. A week whose drivers are unlike our practice weeks can move only two numbers of the on-time model: one intercept, and which day the flu is.
- **A Friday flu in the capital region** is still our hardest week: 94.6% on time on the mean of four samples, 93.2% on the worst.
- **A note in words we have not seen.** A cue outside the vocabulary is missed silently.
- **Two desks on one world.** Only a lock file and a procedure prevent it.

**What we do not know.**
- The margin of knowing where the drivers live sits on the weeks it was fitted on (+€1,144 a week on tune; −€39 on wide; +€282 on hold). On unseen weeks it buys on-time.
- The flu sign costs nothing on tune and wide weeks (−€23, se 232) and may cost a little on hold weeks (−€252, se 209).
- Two of the 16 weights (the drivers who know us, an hour already waited) have no support in a refit any more. Taking them out changes decisions, and we have not tested that on 24 weeks.
- The on-time model is pessimistic on purpose: it says 12.9% late where 6.4% are, and the week's own intercept corrects it within about forty orders.

**Figure.** One bar: 75,390 direct offers, with a sliver of 85 marked "yes". Next to it the two lists "would break it" and "do not know" as plain text.

---

## Appendix A — every practice week of this system, with the kit starter on the same week

Source: `weeks fleet3-cand-ns fleet3-cand-hold orch-base-s14` (helper in `OPEN_NUMBERS.md`) and `runs/starter-tune.out`, `runs/starter-hold.out`. Tune weeks without stride; hold and wide weeks with stride 14, one sample each. `[UPDATE: add the 32 fresh weeks of the frozen commit, runs/final-fresh.out]`

| set | seed | margin | on time | orders | starter: margin | starter: on time |
|---|---|---|---|---|---|---|
| tune | halal-01 | €15,298 | 97.1% | 454 | −€81,724 | 41.4% |
| tune | halal-02 | €20,494 | 95.9% | 507 | −€73,524 | 50.1% |
| tune | halal-03 | €16,575 | 97.1% | 449 | −€86,889 | 34.8% |
| tune | halal-04 | €22,021 | 97.2% | 495 | −€68,552 | 47.7% |
| tune | halal-05 | €23,111 | 97.0% | 609 | −€52,536 | 62.4% |
| tune | halal-06 | €14,840 | 96.4% | 444 | −€50,993 | 64.1% |
| tune | halal-07 | €18,061 | 97.4% | 464 | −€59,029 | 55.6% |
| tune | halal-08 | €12,366 | 96.7% | 398 | −€32,606 | 60.2% |
| hold | halal-09 | €17,045 | 93.2% | 399 | −€80,956 | 38.0% |
| hold | halal-10 | €10,034 | 97.5% | 322 | −€62,304 | 44.9% |
| hold | halal-11 | €20,230 | 95.4% | 437 | −€76,465 | 45.8% |
| hold | halal-12 | €19,642 | 96.5% | 489 | −€68,643 | 47.0% |
| hold | halal-13 | €11,212 | 98.2% | 333 | −€47,735 | 62.7% |
| hold | halal-14 | €10,178 | 93.9% | 314 | −€80,255 | 39.0% |
| hold | halal-15 | €13,767 | 95.3% | 407 | −€79,947 | 51.2% |
| hold | halal-16 | €16,336 | 96.1% | 486 | −€54,963 | 54.1% |
| wide | halal-17 | €11,515 | 95.8% | 379 | | |
| wide | halal-18 | €10,410 | 93.9% | 278 | | |
| wide | halal-19 | €12,611 | 97.1% | 344 | | |
| wide | halal-20 | €13,496 | 98.0% | 348 | | |
| wide | halal-21 | €12,919 | 96.0% | 399 | | |
| wide | halal-22 | €18,054 | 96.2% | 494 | | |
| wide | halal-23 | €12,353 | 96.9% | 457 | | |
| wide | halal-24 | €10,728 | 96.4% | 308 | | |
| wide | halal-25 | €18,693 | 95.5% | 400 | | |
| wide | halal-26 | €10,986 | 93.4% | 333 | | |
| wide | halal-27 | €15,496 | 97.8% | 496 | | |
| wide | halal-28 | €14,553 | 96.8% | 401 | | |
| wide | halal-29 | €12,392 | 96.5% | 404 | | |
| wide | halal-30 | €13,653 | 95.5% | 403 | | |
| wide | halal-31 | €15,164 | 95.6% | 360 | | |
| wide | halal-32 | €11,674 | 97.2% | 427 | | |
| ranking round Sat 15:00 | secret week 1 | €16,232 | 95.4% | 390 | | |
| ranking round Sat 15:00 | secret week 2 | €19,659 | 96.5% | 512 | | |
| ranking round Sat 15:00 | secret week 3 | €10,738 | 95.0% | 300 | | |
| ranking round Sat 15:00 | secret week 4 | €15,417 | 97.1% | 451 | | |
| ranking round Sat 15:00 | secret week 5 | €20,231 | 96.4% | 499 | | |

## Appendix B — the path from the first version to this one (same 8 tune weeks, no stride)

One line per step, each against the line above it. "Merged" marks a step where several streams met, so it changes more than one thing.

| step | run tag | margin a week | on time, worst week | weeks ranked | orders |
|---|---|---|---|---|---|
| kit starter | `starter-tune` | −€63,232 | 34.8% | 0 of 8 | 903 |
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
| + the model knows where the drivers live, target 97% | `fleet2-v2` | €17,116 | 94.2% | 8 of 8 | 457 |
| + the dealer side weighs the war day and the outage day | `surprise-weighs-ns` | €17,607 | 93.4% | 8 of 8 | 463 |
| + the driver side weighs the flu day | `fleet3-cand-ns` | €17,846 | 95.9% | 8 of 8 | 478 |
