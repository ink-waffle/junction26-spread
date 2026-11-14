# Halal Team — Spread: the deck as text

Eleven slides. Each slide is one claim (its title), the evidence, and one figure to draw.

- Everything is level 8. A week counts ("ranked") only when at least 90% of its orders are on time.
- The system described is the default policy of commit `8ae61c5` (Saturday 23:00; ideas 1–15 of `NIGHT_LOG.md`). It plays the final. Idea 15 is a skeptic's pass over ideas 1–14 (slide 9; `SKEPTIC.md`).
- Practice weeks, and what each was used for:
  - **tune** = seeds `halal-01..08`: fitted on from the start.
  - **wide** = `halal-17..32`: their notes and Mondays helped build the note reader and the bisection; no price or fee number came from them until Saturday afternoon, when the surprise days of slide 6 were designed and fitted on tune and wide weeks together.
  - **hold** = `halal-09..16`: nothing was fitted on them. They were played to confirm, and one of them, `halal-09`, was opened to study the flu.
  - **untouched** = `halal-65..128`: first played by the skeptic's pass. Its deletions and its two numbers were decided on `65..96` and confirmed once on `97..128`.
  - **fresh** = `halal-33..64` and `halal-129..160`: each played once, after the decisions were frozen, as the record of a frozen system. `129..160` is the record of this one.
  - The on-time target was chosen after looking at hold weeks (96%), then on tune and wide weeks (97%), then on `halal-65..96` (97.5%).
  - So the clean test is the 32 fresh weeks `halal-129..160` (slides 9 and 10): no system of ours had played them before.
- "Stride 14" marks weeks played with the practice clock moving 14 minutes a turn while requests arrive. A week is then three times faster to play, and our answers come up to 14 minutes later than in the final. "No stride" is the final's pace.
- One week moves by about ±1.3 points of on-time and €1,000–3,000 between two plays of nearly the same policy. So the late comparisons use 24 to 32 weeks, paired per week, often with several samples a side (`tools/replicates.py`, `tools/ablations.py`), and give a standard error (se).
- `[FINAL …]` and `[SUNDAY …]` mark results still to come. `OPEN_NUMBERS.md` has the command or file for every number.
- Run tags in `code font` are folders under `runs/` and lines of `runs/log.jsonl`.

---

## Slide 1 — The answer: a driver side that prices each car's risk, a dealer side that learns what dealers pay, both weigh the events that nobody announces, and only what holds on unseen weeks stays

**Result.**
- Final: `[FINAL: € … margin, … % on time, … orders, place … of …]`
- On 32 weeks that no system of ours had played (`halal-129..160`, once, at the final's pace): **€14,313 a week, 32 of 32 ranked**, on time 96.3% in the mean and 92.8% in the worst week. The system before idea 15 on the same weeks: €13,547. The kit starter on our own weeks: −€63,232 (tune) and −€68,908 (hold), no week ranked. We quote €14–15k a week; the €17,846 of the 8 tune weeks is 8 rich worlds.
- Best ranking round: Saturday 18:00, **€75,405** for five weeks, 5 of 5 ranked, on time 95.3–97.6%; **10th of 67 ranked teams**; **1.29 × House best** (€58,677) on the same weeks. Rounds from Sunday 00:00 are played by the frozen system `[SUNDAY: rounds 00:00, 03:00, 06:00, runs/board.jsonl + leaderboard]`.
- Test finals, live clock, from a cloud machine, the system before idea 15: Saturday 14:00 (joined on Thursday) €3,747, 97.6% on time, **2nd of 55 ranked teams**; Saturday 20:00 (a full week from Monday, the final's shape) €15,752.50, 424 orders, 97.2% on time, 18th of 75 ranked (first €19,592, 10th €16,623).

**The big ideas** (one slide each):
1. One fee per gig, because drivers learn.
2. A car costs its fee plus its risk of arriving late. That cost alone decides which cars we want.
3. The price level dealers pay is learned from every yes and no. The quote maximises (price − cost) × P(yes).
4. The practice world is deterministic, so we bisected the competitor.
5. Nobody announces the price war, the outage or the flu. Each side weighs which day it is.
6. Two cars in one gig: the trip home is half a driver's cost.
7. Notes are read by a small grammar.
8. We audited our own system on weeks nobody had played, deleted what did not hold, and earned more.

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
1,900 lines of Python, standard library only, eleven modules; 123 numbers fitted or set by hand (129 before idea 15).

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

**Figure.** Bar chart, x = weekday of the starter's week, y = median booked fee as a multiple of the typical fee: Mon 1.0, Tue 1.5, Wed 1.5, Thu 1.5, Fri 2.5. A dashed step line marks the cap of the starter's schedule (1.5 ×, then 2.5 × after the deadline warning). A flat line at 0.95 × marks our average fee (32 fresh weeks, `orch-head-record`). Caption: "Monday: 7 minutes to a booking at 1.0 ×. Tuesday: drivers wait for the cap."

---

## Slide 3 — A car booked before its deadline warning is on time (96% against 25%), so a car costs its fee plus its risk

**Why.**
- Eight weeks with random prices and random flat fees (`explore1`): a car booked before its deadline warning was on time 96% of the time; a car that was not, 25%.
- A higher fee stops helping. Share booked before the warning at a flat 0.70 / 0.85 / 1.00 / 1.15 / 1.30 / 1.50 × typical: 39 / 61 / 81 / 91 / 88 / 91%. Above 1.15 × what is left is the car and the town.
- The shortage differs from town to town. Orders with ≤ 3 / 4–15 / 16–50 / > 50 drivers living within 30 km of the pickup were late 12.6 / 10.0 / 6.5 / 3.3%. Our first model said 12% for all of them.

**The idea.** An on-time model (15 weights, fitted on our own weeks by `tools/fleet_fit.py`; its level set on 64 weeks the fit never saw, slide 9) gives P(late) for a car at a fee. The fee is the step that costs least in all. The cost that the dealer side sees is that fee plus the risk. There is no list of forbidden cars: a car we should not win gets a cost that no dealer pays.

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
         its intercept where 64 weeks the fit never saw put it, the same all week
fee   =  the step f of {0.85, 1.0, 1.15, 1.3, 1.5} × typical fee with the lowest
         f + P(late | f) × (refund + λ) + harm to the cars that already wait
cost  =  fee + P(late) × refund + (P(late) − 2.5%) × λ + harm
λ     =  €300 × (late orders we expect this week ÷ 2.5% of orders)⁴    €19 at half the allowance, €300 at it
```

---

## Slide 4 — The price level dealers pay is learned online as a sum of parts; the quote maximises (price − cost) × P(yes), and every option goes at the same margin

**Why.** With random quotes on 8 weeks (`explore1`), the price at which half the quotes win was 1.20–1.49 × list price by world, and 1.01–1.78 × by world and day. A fixed 1.45 × list won 177 cars in one world and 485 in another.

**The idea.**
- A dealer says yes with a chance that is logistic in log(price ÷ list price) around a level.
- The level is a sum of parts: the world, the day, the pickup place, the delivery place, the lane. The two place parts start from a table of 60 numbers fitted on our tune weeks; the others start at zero. Two terms are known, not learned: +1.05% per order delivered on time to this dealer (trust), −8.5% per step slower than the fastest option. (A dealer part and a pickup-place-today part were in it until idea 15: on 64 unseen weeks they foretold no answer, slide 9.)
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
level          = world + day + pickup place + delivery place + lane
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
- On the 32 fresh weeks 27% of our cars are delivered in a two-car gig, at 0.80 × typical and 99.1% on time. Cars never paired: 0.98 × and 95.5% (`python -m tools.offers_study paired orch-head-record`).
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

## Slide 9 — We audited our own system on weeks nobody had played: what did not hold is deleted, and the system earns more on every untouched set

**Why.** On Saturday evening the system held 129 numbers fitted or set by hand. It made €17,846 a week on the 8 weeks we fitted on and €14,360 on 32 fresh ones. Was it fitted to its own weeks? One agent with no stake in any part counted every number and took each part out in turn on 32 weeks that nobody had played (`halal-65..96`; `SKEPTIC.md`).

**What did not hold.**
- **A model level off by a factor of two, patched every week.** On 64 weeks the fit never saw, the on-time model said 10.0% of the cars late where 4.8% were: as baked it foretold worse than a constant. A learner inside the week (`Fleet.learned`, behind a hand-set prior and a clamp of one logit) found the missing intercept again every week, slowly: +0.35 by Monday noon, +0.75 from Thursday. So Monday was priced as twice as risky as Wednesday: 72 orders against 89–92.
- **One sign with the wrong sign.** `known`, the drivers have seen our week's first hundred bookings: baked +0.25, the unseen weeks say −0.17 ± 0.06.
- **Two parts of the dealer's level that predict nothing.** The dealer part and the pickup-place-today part: −0.3 and +1.2 per mille of log-likelihood on 64 weeks, where the lane part gives 15.

**What we did.** Deleted all four: 1,948 → 1,900 lines, 129 → 123 numbers, and the fleet now remembers nothing that a restart must rebuild. Set the model's level once, where the unseen weeks put it: +0.88, the same on three disjoint sets of weeks (+0.86 / +0.90 / +0.87). On its own play the model now says 4.3% late where 4.0% are. A level that is right makes caution cheap, so the aim went from 97% to 97.5%.

**The effect.** Against the system before the pass, same weeks, paired per week:

| weeks | before | after |
|---|---|---|
| **fresh `halal-129..160`**, once each, after the freeze, no stride (`orch-old-record` → `orch-head-record`) | €13,547 a week, on time 96.3%, worst week 93.1%, 402 orders | **€14,313 (+€766, se 221)**, on time 96.3% (−0.03 point, se 0.15), worst week 92.8%, 426 orders; 24 of 32 weeks up |
| untouched `halal-97..128`, no stride (`skeptic-Bbase-B-s0` → `skeptic-C975-B-s0`) | €15,829, 96.2%, worst 94.3% | €16,266, 96.4%, worst 94.1%, 32 of 32 ranked |
| untouched `halal-65..96`, where it was decided, two samples a side | | +€679 (se 206), on time +0.52 point (se 0.11) |
| hold `halal-09..16`, four samples a side | | +€694 (se 142), on time +0.03 point |
| orders won Monday / Tuesday / Wednesday / Thursday / Friday, fresh weeks | 71 / 85 / 81 / 96 / 73 | 82 / 91 / 88 / 95 / 76; Monday's sales +€1,178 (se 232) |

**What stayed, on the same untouched weeks.** Taking out each of these cost money: the harm to the cars that wait −€2,967 a week, the pickup-side signs −€1,702, two-car gigs −€1,444, the six-hour look −€1,394, the note grammar −€998. The place table, the lane part and the events each foretell the dealers' answers in 55 to 64 of 64 unseen weeks. A deliberately small system ranks in 4 of 32 weeks.

**Judged and not chosen.** A second agent built a smaller system still: the old one minus 64 numbers (the 60 of the place table, `known`, the two parts), equal to it in margin (−€76, se 184; `research/simple`). Two of its findings stand. The slow Monday is mostly the world: dealers who do not yet trust us pay about 12% less on Monday. And the learner was insurance against a world much harder than ours: with a model one logit too easy, on time fell 2.8 points without it and 1.0 with it. We chose the measured constant: one line explains it, and it earns more on every untouched set. We accept that risk (slide 11).

**Figure.** Left, two pairs of bars, "the model says late / late in fact": before 10.0% / 4.8%, after 4.3% / 4.0%. Right, orders won by weekday on the 32 fresh weeks, two bars a day: before 71 / 85 / 81 / 96 / 73, after 82 / 91 / 88 / 95 / 76. Caption: "129 → 123 numbers, 1,948 → 1,900 lines, +€766 a week on weeks nobody had played."

---

## Slide 10 — Robust: every week the frozen system played is ranked (216 plays of 128 weeks), where the kit starter ranks none of 16; a restart replays the log into the same desk

**Many weeks.** The frozen system, each set once:

| weeks | margin a week | on time, worst week (mean) | ranked | orders |
|---|---|---|---|---|
| **fresh `halal-129..160`**, no stride (`orch-head-record`) | **€14,313** | 92.8% (96.3%) | 32 of 32 | 426 |
| untouched `halal-97..128`, no stride (`skeptic-C975-B-s0`) | €16,266 | 94.1% (96.4%) | 32 of 32 | 454 |
| hold `halal-09..16`, stride 14 (`skeptic-holdC975-x-s14`) | €15,488 | 94.6% (96.3%) | 8 of 8 | 422 |
| tune and wide `halal-01..32`, stride 14 (`skeptic-twC975-x-s14`) | €15,444 | 94.5% (96.8%) | 24 of 24 | 444 |

With the other samples of slide 9: 216 plays of 128 different weeks, none unranked, the worst 92.8%. The kit starter on our own weeks, against the system before idea 15 (ideas 1–14) on the same weeks: tune −€63,232 at 52.1% on time against €17,846; hold −€68,908 at 47.8% against €14,806; the starter ranked 0 of 16, ours 16 of 16. The system before idea 15 on the first fresh set, `halal-33..64`: €14,360, worst week 93.2%, 32 of 32 (`final-fresh`).

Secret weeks, the same for every team:

| | ours | against House best on the same weeks | place |
|---|---|---|---|
| Ranking round Saturday 09:00 (Saturday morning's system: no menu of options, no pairs, no second look) | €48,860 | 0.96 × | 35th of 45 |
| Ranking round Saturday 12:00 | €82,785 | 1.07 × | 22nd of 58 |
| Ranking round Saturday 15:00 | €82,278 | 1.28 × | 19th of 63 |
| Ranking round Saturday 18:00 (ideas 1–14) | €75,405 | 1.29 × | 10th of 67 |
| Ranking round Saturday 21:00 (ideas 1–14) | €79,391 | 1.20 × | 3rd of 11 ranked at 21:08 `[SUNDAY: closing place, leaderboard]` |
| Ranking rounds from Sunday 00:00, the frozen system | `[SUNDAY: runs/board.jsonl]` | `[SUNDAY: leaderboard]` | `[SUNDAY]` |
| Test final Saturday 14:00, live clock, joined on Thursday | €3,747, 97.6% on time | first team €4,023, 10th €3,292 | 2nd of 55 |
| Test final Saturday 20:00, live clock, a full week from Monday (the final's shape) | €15,752.50, 424 orders, 97.2% on time | first team €19,592, 10th €16,623 | 18th of 75 |

The 20:00 test final won 49 / 99 / 73 / 109 / 94 orders Monday to Friday. Its slow Monday sent the skeptic to the start of the week; on the fresh weeks the frozen system wins 11 more orders on Monday (slide 9).

**How we decided late.** One week moves by ±1.3 points of on-time between two plays of nearly the same policy. So each late change was played on 24 to 32 weeks, paired per week, with several samples a side: the same seed at strides of 12 to 15 minutes is another sample of the same policy (`tools/replicates.py`, `tools/ablations.py`). Every knob of ideas 1–14 was moved both ways on 24 weeks, two samples a side; none was worth changing (fee floor at 0.75 × typical −€771 a week, se 222; second look at 12 hours −€342). Idea 15 was decided on `halal-65..96`, confirmed once on `halal-97..128`, and recorded on `halal-129..160`.

**A restart.** State is a fold over the world's events and the actions the world acknowledged (a journal on disk). A new desk replays both and is the desk that died. `tools/restart_test.py` compares every object, and then the week's margin: on the frozen system 8 of 8 restarts rebuilt the same desk, and the week ended at €21,126.94 with and without them (halal-02; 12 of 12 for ideas 1–14). The test caught a real bug on Saturday: when the fleet began to learn inside the week, 1 of 12 restarts matched and a week with restarts ended €2,309 lower. Idea 15 deleted that learner: the fleet's state is now the books alone. The frozen commit plays a week of the skeptic's branch again to the cent (halal-98, €9,309.09): what plays the final is what was measured.

**A slow network and a surprise.** In the final a request must be answered within 4.5 real seconds.
- The test finals ran on a cloud machine 9 ms from the server. At 14:00 every request of Thursday and Friday was quoted, no action was refused, and the slowest turn took 0.86 s. At 20:00, a full week from Monday: all 1,030 requests quoted, the slowest turn under 0.25 s.
- Rehearsals with an earlier version: a whole week at the final's clock from a laptop on a phone hotspot, 0 of 1,038 requests unanswered; with 1.5 seconds added to every request, 0 unanswered; a Thursday join with a dead resolver, two cut streams, 90 seconds without a route and a kill: the desk rejoined by itself three times. `[SUNDAY: the rehearsal of a full week with a kill on 8ae61c5, if it ran]`

**Figure.** A dot plot: x = on-time share from 30% to 100% with a red line at 90%, y = margin from −€90k to +€25k. 32 dots of the frozen system on the fresh weeks sit right of the line and above zero; 16 starter dots (tune and hold) sit far left and far below. Beside it a two-line diagram: "world's log + journal → fold → desk" drawn twice, once for play and once after a restart, with an equals sign between the two desks.

---

## Slide 11 — What did not work, and what would break the system

**Did not work.**

| tried | result |
|---|---|
| Meeting the drivers on the day: keep a car out of the app until 07:00 of its last day. Randomised by order number inside 9 worlds | The kept half ended late 11.1% against 7.0%, and 30% against 15% in the flu's night. A weak promise is far better than none. |
| A rule for the night of the flu: when five orders lose their driver within an hour, reopen at the fee of a deadline warning | Late among those cars 14% → 10% on tune and wide weeks, nothing on hold weeks. Not taken; slide 6 weighs the night instead. |
| A crisis price, to win safe cars after a bad night | −€481 a week on 14 weeks, on time unchanged. |
| A better-calibrated refit of the on-time model, Saturday morning (predicted late 10.3% → 9.0%, realised 6.0%) | €14,973 → €12,707 a week. It accepts more risk on Monday, and the late cars show two days later: the pessimism was the safety margin. Idea 15 set the level right and moved that margin into the aim (97.5%) instead. |
| A finer fee grid (steps of 0.05 from 0.8 to 1.2 × typical) | −€624 a week (se 284) on 24 weeks. |
| Finding the flu by a census: a direct offer that pays nothing, to every driver each day | Names a silent day in 7 of 20 weeks, but it is the night that takes our bookings in only 2 of them. |
| Opening low (0.6 × for 30 minutes, then 1.15 ×); one low fee for everything; trade-ins at a higher fee | Slide 2; 76.7% on time at 550 orders a week; trade-ins on time 17–61% at any fee we tried. |
| Direct offers to the likeliest drivers | 75,390 offers, 85 accepted. €6,723 against €6,824 a week. |

**What would break it.**
- **A week whose drivers are much scarcer than in any of ours.** Since idea 15 a week moves one thing in the on-time model: which day the flu is. Such a week is braked by the price of the delivery minimum alone, which counts the late orders as they show, two days after we accept them. With a model one logit too easy, on time falls 2.8 points and one week ends at 90.5%; with the deleted learner it falls 1.0 point (`runs/reports/simple.md`). Our 128 weeks put the worst at 92.8%. We chose this risk with open eyes (slide 9).
- **A week that is not the rules' week.** Slide 6 assumes one war day, one outage, one flu night. In the replay a week without a war still gains €66; without both events it loses €118. A flu on Monday shows no night before it.
- **A Friday flu in the capital region** is still our hardest week: 94.5% on time on the mean of four samples (94.6% before idea 15).
- **A note in words we have not seen.** A cue outside the vocabulary is missed silently. On the 64 untouched weeks the reader left 0.2 failed visits a week (the kit's reader: 10.6).
- **Two desks on one world.** Only a lock file and a procedure prevent it.

**What we do not know.**
- Three weights are still open: `waited`, `short`, `trade_in`. On untouched weeks the model without `waited` earned +€601 a week (se 187) and lost 0.29 point of on-time; we win almost none of the cars the other two describe. Not played without them on the frozen system.
- The pickup-side signs earn €1,702 a week on untouched weeks. Two of them, where the drivers live, are real but twice too large there (0.75 and 0.71 baked, 0.31 and 0.34 measured). They stay as fitted.
- The flu sign costs margin on untouched weeks (+€432 a week without it, se 205) and buys 0.21 point of on-time and the floor: without it one week ends at 90.9%. It stays for the floor.
- The numbers set by hand that remain (the fourth power and its cap, `CALM`, the two-car fees, `SURE`, `RETRY`, `MIN_SPAN`) have no measurement of their own. The barrier they shape keeps the floor: a flat €300 a late order ends one week at 90.3%.

**Figure.** One bar: 75,390 direct offers, with a sliver of 85 marked "yes". Next to it the two lists "would break it" and "do not know" as plain text.

---

## Appendix A — every fresh week of the frozen system, with the system before idea 15 on the same week

Source: `weeks orch-head-record orch-old-record` (helper in `OPEN_NUMBERS.md`); `runs/orch-head-record.out`, `runs/orch-old-record.out`. Seeds `halal-129..160`, no stride, one play each, after the decisions were frozen. The frozen system is ahead in 24 of 32 weeks; every week of both is ranked.

| seed | frozen: margin | on time | orders | before idea 15: margin | on time | orders |
|---|---|---|---|---|---|---|
| halal-129 | €15,478 | 97.7% | 386 | €14,559 | 96.6% | 439 |
| halal-130 | €16,639 | 97.0% | 439 | €14,355 | 97.1% | 420 |
| halal-131 | €16,759 | 95.5% | 462 | €16,771 | 96.9% | 445 |
| halal-132 | €13,475 | 98.0% | 447 | €12,632 | 97.3% | 403 |
| halal-133 | €14,009 | 97.6% | 460 | €13,982 | 97.8% | 448 |
| halal-134 | €13,126 | 96.6% | 356 | €13,154 | 96.4% | 357 |
| halal-135 | €8,632 | 96.7% | 331 | €7,341 | 96.9% | 289 |
| halal-136 | €17,738 | 94.7% | 433 | €16,471 | 96.3% | 410 |
| halal-137 | €12,092 | 96.7% | 359 | €11,727 | 96.7% | 390 |
| halal-138 | €14,122 | 97.3% | 450 | €11,369 | 96.7% | 420 |
| halal-139 | €13,290 | 97.4% | 378 | €13,248 | 96.0% | 353 |
| halal-140 | €12,738 | 96.0% | 451 | €12,599 | 95.2% | 418 |
| halal-141 | €13,004 | 95.8% | 385 | €10,866 | 97.3% | 366 |
| halal-142 | €16,424 | 96.9% | 387 | €16,327 | 96.0% | 425 |
| halal-143 | €18,592 | 96.1% | 466 | €18,804 | 94.9% | 470 |
| halal-144 | €11,977 | 95.2% | 481 | €11,643 | 97.1% | 382 |
| halal-145 | €9,684 | 92.8% | 346 | €8,116 | 93.1% | 274 |
| halal-146 | €17,579 | 94.3% | 460 | €15,349 | 95.0% | 402 |
| halal-147 | €17,767 | 97.0% | 499 | €16,078 | 96.5% | 492 |
| halal-148 | €18,815 | 96.1% | 460 | €17,380 | 96.5% | 427 |
| halal-149 | €11,515 | 96.9% | 420 | €10,350 | 96.4% | 393 |
| halal-150 | €16,443 | 96.1% | 436 | €13,000 | 95.7% | 348 |
| halal-151 | €10,057 | 96.5% | 434 | €11,058 | 96.0% | 445 |
| halal-152 | €18,092 | 97.4% | 503 | €17,151 | 97.7% | 442 |
| halal-153 | €16,795 | 95.9% | 413 | €18,251 | 96.0% | 426 |
| halal-154 | €13,831 | 97.1% | 447 | €11,414 | 97.8% | 358 |
| halal-155 | €8,168 | 95.7% | 370 | €10,235 | 94.8% | 381 |
| halal-156 | €14,340 | 96.7% | 452 | €15,009 | 95.9% | 412 |
| halal-157 | €12,395 | 96.3% | 378 | €13,059 | 96.5% | 396 |
| halal-158 | €11,136 | 96.6% | 386 | €9,464 | 97.3% | 333 |
| halal-159 | €18,533 | 95.6% | 504 | €17,343 | 96.7% | 479 |
| halal-160 | €14,784 | 94.5% | 454 | €14,414 | 95.0% | 437 |
| **mean** | **€14,313** | **96.3%** (worst 92.8%) | **426** | **€13,547** | **96.3%** (worst 93.1%) | **402** |

## Appendix A2 — the system before idea 15 on our practice weeks, with the kit starter on the same week

Source: `weeks fleet3-cand-ns fleet3-cand-hold orch-base-s14` and `runs/starter-tune.out`, `runs/starter-hold.out`. Ideas 1–14 (decisions of `52aaf93`). Tune weeks without stride; hold and wide weeks with stride 14, one sample each. The frozen system on these sets: slide 10.

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

Idea 15 is not a row here on purpose: it was decided and measured on weeks nobody had played, never on the tune weeks as a set (slide 9). On the 24 tune and wide weeks at stride 14 it is +€625 a week (se 331) and +0.43 point of on-time against ideas 1–14 at the same stride (`orch-base-s14`).
