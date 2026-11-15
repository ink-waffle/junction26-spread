# Halal Team — Spread: the deck as text

**The thesis, in one sentence: our dispatcher knows what it does not know, and proves it on weeks it has never seen.**

Ten slides, one argument (the jury's limit is 5 to 10 slides; it judges "how elegant, clear, creative and robust", `challenge.md`). Each title is a claim and one step of the argument; under it the evidence with its run tag, and one figure to draw. The appendices are backup and are not shown.

"Knows what it does not know" means four things, and the slides show them in order:
1. What can be measured, we measured; what cannot be known, we proved cannot be known (slide 2).
2. Every probability the system acts on comes true: the chance of a yes (slide 3) and of a late car (slide 4). What nobody announces, it weighs instead of guessing (slide 5). Where the world is plain, it uses no model at all (slide 6).
3. It audited itself on weeks nobody had played, found where it was wrong, and earned more (slide 7). The ideas that did not beat it are logged with their numbers (slide 8).
4. It holds on weeks no number of it was chosen on (slide 9), and it says where it would break (slide 10).

Conventions:
- Everything is level 8. A week counts ("ranked") only when at least 90% of its orders are on time: the delivery minimum.
- The system is the default policy of commit `8ae61c5` (Saturday 23:00; ideas 1–15 of `NIGHT_LOG.md`), the frozen system. Idea 15 is the audit of slide 7 (`SKEPTIC.md`). The final plays `3f85408`: the frozen system with one number changed, the on-time aim 97.5% → 96.5% (Sunday 06:30; slide 9 says why and what it costs).
- Practice weeks, and what each was used for:
  - **tune** = `halal-01..08`: fitted on from the start.
  - **wide** = `halal-17..32`: their notes and Mondays helped build the note reader and the bisection; no price or fee number came from them until Saturday afternoon, when the surprise days of slide 5 were designed and fitted on tune and wide weeks together.
  - **hold** = `halal-09..16`: nothing was fitted on them. They were played to confirm, and one of them, `halal-09`, was opened to study the flu.
  - **untouched** = `halal-65..128`: first played by the audit. Its deletions and its target were decided on `65..96` and confirmed once on `97..128`.
  - **fresh** = `halal-33..64` and `halal-129..160`: each played once, after a freeze, as the record of a frozen system. `129..160` is the record of this one.
  - **after the freeze** = `halal-161..192`: played by the frozen system at strides 14 and 13 as the baseline that every idea tried after the freeze had to beat (slide 8; `orch-main161-s14`, `orch-main161-s13`). The final's aim of 96.5% was chosen on them, so for `3f85408` they are decision weeks, not unseen.
  - **unseen** = `halal-97..192`: no number of the frozen system was fitted or chosen on them (`97..128` confirmed it once). The audit set the on-time model's level from tune, fresh `33..64` and untouched `65..96` weeks, so those are not counted as unseen.
- "Stride 14" marks weeks played with the practice clock moving 14 minutes a turn while requests arrive: three times faster to play, and our answers come up to 14 minutes later than in the final. "No stride" is the final's pace. Another stride is another sample of the same policy.
- One week moves by about ±1.3 points of on-time and €1,000–3,000 between two plays of nearly the same policy. So late comparisons use 24 to 32 weeks, paired per week, often with several samples a side (`tools/replicates.py`, `tools/ablations.py`), and give a standard error (se).
- `[FINAL …]` and `[SUNDAY …]` mark results still to come. `OPEN_NUMBERS.md` has the command or file for every number. Run tags in `code font` are folders under `runs/` and lines of `runs/log.jsonl`.

---

## Slide 1 — Our dispatcher knows what it does not know, and proves it on weeks it has never seen

**Three numbers.**

| | it said | it was | where |
|---|---|---|---|
| **1. Its odds come true.** The driver side's chance that a car is late | 4.2% | 4.5% late | the 32 fresh weeks `halal-129..160`, played once after the freeze (`python -m tools.fleet_fit --calibrate orch-head-record`) |
| The dealer side's chance of a yes | 44.4% | 45.2% yes | 30,517 of our quotes replayed, within 3 points in every bin of chance, day, trust and price (`GAP.md` on `research/gap`, §1 item 5) |
| **2. It found where it was wrong, and earned more.** The same driver side before the audit, on 64 weeks its fit never saw | 10.0% | 4.8% late | deleting what did not hold: **+€766 a week (se 221)** on the 32 fresh weeks, on time unchanged (`orch-old-record` → `orch-head-record`) |
| **3. It holds where it has never been.** Plays of the frozen system on the 96 unseen weeks | | **160 of 160 ranked** | worst 92.3% on time, mean €15,327 a week (`skeptic-C975-B-s0`, `skeptic-C975-B-s14`, `orch-head-record`, `orch-main161-s14`, `orch-main161-s13`) |

**The final.** €18,532.31 margin, 94.5% on time, 510 orders (the most of any team in the top 14), 0.2% not delivered; place 14 of 58 ranked teams, €552 under 10th (€19,083.95); first €22,931

**For scale.** The kit starter on our own weeks: −€63,232 a week (tune) and −€68,908 (hold), no week ranked. Secret weeks, the same for every team: Saturday 18:00 round 10th of 67 ranked teams at 1.29 × House best; Sunday 00:00, the frozen system, €81,046 for five weeks at 1.33 × House best (€60,812), 2nd of the 18 teams ranked at 00:06, closed 11th of 58 (10th €81,840); Sunday 03:00 €71,665 at 1.28 × House best (closed 28th of 48); Sunday 06:00 €69,092 at 1.18 ×. We quote €14–15k a week, never the €17,846 of the 8 tune weeks.

**Figure: the thesis as one picture.** A calibration plot, x = "the system said", y = "it was", both 0–50%, with the diagonal drawn. Two dots on the diagonal: "late car: said 4.2%, were 4.5%" and "dealer's yes: said 44.4%, were 45.2%". One hollow dot far off it, "Saturday 19:00: said 10.0%, were 4.8%", with an arrow to the late-car dot labelled "the audit: +€766 a week". Under the plot, one line: "160 of 160 unseen plays ranked".

---

## Slide 2 — We measured the world instead of guessing it: a practice day replays to the cent, so we bisected every dealer's price, and found the part nobody can know

**The idea.** The same seed and the same actions give the same week to the cent. So we play a day many times; each time every request is quoted at the middle of its bracket, and the dealer's yes or no halves the bracket.
- Mondays of 24 worlds, 16 passes each (`tools/probe.py`): 10,181 options of 5,581 requests; 87.7% known within 3%, median bracket 0.5%.
- Every working day of 24 of our own weeks, on copies of the week forked at each midnight (`tools/probe_week.py`): 24,127 thresholds within 2%.

**What it measured.**
- **The dealer's rule.** Offered two options that it would each buy alone, a dealer takes the one with the largest (threshold − price) in euros: 98.1% of 2,397 probed menus (`python -m tools.probe_read`). This is why every option is quoted at one margin (slide 3).
- **Speed is worth euros, not percent.** Same day over next day: a median €14.5 (quartiles €9.5–19.9).
- **Trust.** +0.9% per order delivered on time to that dealer (the rules say 1%).
- **The week's events, exactly** (slide 5): the price war day lies 0.23 log under the calm days, the outage adds 0.26 for cars that leave its region.

**What it proved cannot be known.** Inside one world and lane each request still has its own factor of 8.2% (sd), and nothing in the request predicts it (typical fee, car, note, opening hours, hour of day: every |r| < 0.1). Exact replay of Monday on 7 tune worlds: our learner earns €2,103; an oracle that knows every lane's level €2,065; only an oracle that knows every request's own threshold earns more, €3,723. The knowable part is spent. So we stopped working on price precision, and dropped the lane and dealer tables carried from other worlds (they predict a lane with r = 0.38, a dealer with r = 0.01, and made the fit worse). No bisected price is used anywhere, and the hold worlds were never bisected.

**Figure.** One request as a ladder of passes: a vertical axis "price × list" from 0.5 to 2.5; pass 1 at 1.50 "no", pass 2 at 1.00 "yes", pass 3 at 1.25 "yes", pass 4 at 1.37 "no", … the bracket shrinks to a tick at 1.31 ± 0.5% (example numbers; a real request can be read from `runs/bisect/halal-01.json`). Beside it three bars of euros per Monday: €2,103 "our learner", €2,065 "knows every lane", €3,723 "knows every request: not knowable".

---

## Slide 3 — So a quote is a bet with known odds: the dealer side says how likely a yes is (44.4% said, 45.2% yes), and the quote maximises (price − cost) × P(yes), every option at one margin

**Why learn it.** With random quotes on 8 weeks (`explore1`), the price at which half the quotes win was 1.20–1.49 × list by world, and 1.01–1.78 × by world and day. A fixed 1.45 × list won 177 cars in one world and 485 in another.

**The idea.**
- A dealer says yes with a chance that is logistic in log(price ÷ list price) around a level. The level is a sum of five parts: world, day, pickup place, delivery place, lane. Two terms are known, not learned: +1.05% per order delivered on time to this dealer (trust), −8.5% per step slower than the fastest option.
- Every yes and no moves each part it touched by one Kalman step: a part moves as much as it is still uncertain.
- The quote: the option and price with the highest (price − cost) × P(yes); every other option at the same margin over its own cost. By the dealer's rule (slide 2) we earn the same whichever it takes, and it takes the faster option exactly when speed is worth more to it than it costs us.

**The effect.**

| same weeks | before | after | on time, worst week |
|---|---|---|---|
| fixed 1.45 × list → learned level, tune (`base1` → `market-r30`) | €6,824, ranked 5 of 8 | €10,367, ranked 7 of 8 | 83.9% → 89.1% |
| one option → every option at one margin, tune (`market-m8-best` → `main-m8`) | €14,203 | €14,987 (7 of 8 weeks up) | 93.3% → 93.9% |
| the same on hold (`market-hold-best` → `main-m8-hold`) | €10,795 | €12,170 (5 of 8 weeks up) | 91.5% → 91.3% |

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
 P(yes | price): 44.4% said, 45.2%    P(late | fee): 4.2% said, 4.5%
 learned from every yes and no        cost = fee + risk of a late car
 weighs: war day, outage day          weighs: flu day
   │                                   │
   │ quote = argmax (price − cost) × P(yes)        gig: stops, windows, one fee
   │                                               PAIRS: two cars, one gig
   └──────────────┬────────────────────┘
                  ▼
        actions, quotes first ──► world ──► its answers ──► journal
```

```
P(yes | price) = σ( 11.9 × ( level − ln(price ÷ list price) ) )          flatter while the level is uncertain
level          = world + day + pickup place + delivery place + lane
                 + 1.05% × on-time orders of this dealer − 8.5% × steps slower than the fastest option
quote:           margin m of the best option; every option at  cost of that option + m
```

1,900 lines of Python, standard library only, eleven modules; 123 numbers fitted or set by hand.

---

## Slide 4 — The driver side says how likely a car is to be late, and is right (4.2% said, 4.5% late): a gig has one fee because drivers learn, and a car costs that fee plus its risk

**Why.**
- **Drivers learn that fees rise.** The kit starter raises the fee 10% an hour to 1.5 × the typical fee. On Monday its bookings came a median 7 minutes after posting, at 1.0 × typical; from Tuesday the median booked fee was exactly the cap, 1.5 ×; from Friday 2.5 ×. It paid €118.6k in fees on €71.3k of revenue (`spread-1`). So a gig of ours has one fee, chosen again at four named moments only: after six hours without a driver, when its last day begins, at the deadline warning, when a driver is lost.
- **A car booked before its deadline warning is on time 96% of the time; one that is not, 25%** (`explore1`, random flat fees). Above 1.15 × typical more money books no more cars (share booked before the warning at 0.70 / 0.85 / 1.00 / 1.15 / 1.30 / 1.50 ×: 39 / 61 / 81 / 91 / 88 / 91%).
- **The risk depends on who lives near the pickup.** Orders with ≤ 3 / 4–15 / 16–50 / > 50 drivers within 30 km of the pickup were late 12.6 / 10.0 / 6.5 / 3.3%.

**The idea.** A logistic on-time model (15 weights fitted by `tools/fleet_fit.py`; its level set once where 64 weeks the fit never saw put it, slide 7) gives P(late) for a car at a fee. The fee is the step that costs least in all; the cost the dealer side sees is that fee plus the risk. There is no list of forbidden cars: a car we should not win gets a cost that no dealer pays.

```
fee   =  the step f of {0.85, 1.0, 1.15, 1.3, 1.5} × typical fee with the lowest  f + P(late | f) × (refund + λ) + harm to the cars that already wait
cost  =  fee + P(late) × refund + (P(late) − 3.5%) × λ + harm
λ     =  €300 × (late orders we expect this week ÷ 3.5% of orders)⁴      €19 at half the allowance, €300 at it
allowance  =  100% − the on-time aim  =  3.5% in the final (aim 96.5%); 2.5% in the frozen system (aim 97.5%)
```

**The effect.**
- Four hard rules (8 hours of slack; no private pickup, trade-in or premium car) → cost = fee + risk, 8 tune weeks, same quotes (`base1` → `fleet-v3`): €6,824 → €9,613 a week, worst week 83.9% → 93.8%, ranked 5 of 8 → 8 of 8.
- The look after six hours (`offers-m8-board96` → `main-m9-look6-ot96`): €14,935 → €16,838 a week, 350 → 438 orders, worst week 94.5% → 94.7%.
- **What it knows it gets wrong:** only lanes over 400 km are off (7.8% said, 10.9% late; 53 orders a week, 1.6 late orders a week more than it thinks; `GAP.md` §1 item 4).

**Figure.** Left: two bars, "booked before the deadline warning: 96% on time" and "not: 25%". Right: the six-point supply curve (x = fee × typical, y = share booked before the warning), flat after 1.15 ×. Small inset: the starter's median booked fee by weekday, Mon 1.0, Tue–Thu 1.5, Fri 2.5, caption "Tuesday: drivers wait for the cap".

---

## Slide 5 — What nobody announces, it weighs instead of guessing: 600 possible weeks for the price war and the outage, and the one night when the flu gives bookings back

**Why.** A level 8 week has one price war day (the competitor 20% cheaper), one outage day and region (30% dearer for cars that leave a town and the places within 80 km), and one flu day (a third of the drivers stay at home). Nobody says which. A day part that chased them followed a war after a median 18 requests, and an outage after 67 or never.

**The idea.**
- **Dealer side.** 5 war days × 4 other days for the outage × 30 towns = 600 possible weeks. Every answer weighs every one of them, and the quote is priced against the mix that is left for today.
- **Driver side.** On one night a week 22–57% of the bookings held for that day come back in its first hour; on every other night 2.7% (`tools/night_study.py`, 24 weeks). The books count it at each day's first event; the fleet turns the nights seen so far into the chance that a day is the flu's, and the on-time model has that chance as one more sign.
- Both are functions of the event log, so a restart rebuilds them.

```
P(day d is the flu's) ∝ (0.33 ÷ 0.03)^back(d) × (0.67 ÷ 0.97)^(held(d) − back(d))      over the 5 working days
```

**The effect.**

| | before | after |
|---|---|---|
| War day named from the answers alone | — | 24 of 24 weeks, sure after a median 5 answers of that day |
| Outage day named | — | 16 of the 19 weeks where it reached enough requests |
| Requests until our level is within 5%, war day / outage day | 18 / 67 or never | 4 / 7 |
| Exact replay of 24 probed weeks (`python -m tools.surprises money`) | €12,082 a week | €12,284 (+€202, se 66; 19 of 24 weeks up) |
| The flu sign, 25 weeks, 49 samples a side (`tools/replicates.py`) | — | on time +0.38 point (se 0.20), 1.6 late orders a week fewer, margin −€23 (se 232) |
| The seven weeks whose flu is Friday | — | +1.1 points; the hardest, a hold week: 92.3% → 94.6% |

**Figure.** Two rows over one week, Monday to Friday. Top, dealer side: five boxes, each with a bar "chance that today is the war day"; by 08:30 on Thursday the Thursday bar is at 100% and the quote line drops 20%. Bottom, driver side: at each midnight a small bar "share of the day's bookings given back": 3%, 2%, 3%, then 40% on Friday 00:30.

---

## Slide 6 — Where the world is plain, it uses no model: two cars share a gig because the trip home is half a driver's cost, and a small grammar reads 22,099 of 22,099 notes

**Two cars, one gig.** The typical fee of a trade-in (one car out, one back) is 0.50 × the two single typical fees (175 requests): the trip home is half of what a driver is paid for. So a new car waits up to 30 minutes for a second car whose pickup is within 30 km of its delivery (at most 5 hours of driving); both go as one gig at 0.70 × the two typical fees (0.85 × when the partner already sits in the app).
- Randomised inside the same worlds: pairs with at most 4 hours of driving at 0.70 × were booked 85% of the time, in a median 4 minutes; their fees came to 0.89 × typical against 1.21 × for the same cars as two gigs.
- On the 32 fresh weeks 27% of our cars travel in a two-car gig, at 0.80 × typical and 99.1% on time; cars never paired 0.98 × and 95.5% (`python -m tools.offers_study paired orch-head-record`).

**Notes.** 41% of requests carry a note, in Finnish, Swedish or English, with typos and corrections, and the world acts on it whether we read it or not. The kit's keyword reader got 80.0% of notes right, and we paid 10.6 failed visits a week. Ours: note → clauses → cue words, clock times and days → one fact per clause; a correction replaces a time, a denial deletes it. No language model: 13 microseconds a note, and the same facts on every replay, which the restart depends on.
- `python -m tools.notes_eval`: 22,099 of 22,099 notes right on 50 labelled worlds, 6,152 facts at 100% precision and recall. On 26 worlds never seen while building it, the first run misread 2 of 11,432; with one more random typo in every note, 99.69%.
- Failed visits 10.6 → 0.0 a week (tune, `base1` → `notes-v1`); 0.2 a week on the 64 untouched weeks.

**Both earn their place on unseen weeks** (slide 7): taking out the pairs costs €1,444 a week, the grammar €998.

**Figure.** Left, a map sketch of one pair: car 1 from A to B, car 2 from B′ to C, B′ within 30 km of B, one driver, "0.70 × (typical 1 + typical 2)". Right, one real note read left to right (world `halal-03`, Friday 09:46):

```
"Liike auki arkisin klo 7-20. Huolto kesken, valmis klo 15, ei kun klo 14. Lisäksi 4 kesärengasta tavaratilassa"

clause 1   auki + 7-20                 → pickup site really open 07:00–20:00
clause 2   valmis + 15, "ei kun" 14    → the correction replaces 15: car ready Friday 14:00
clause 3   kesärengasta + tavaratilassa → summer tyres as cargo: no fact
```

---

## Slide 7 — It found where it was wrong: an audit on weeks nobody had played caught a model off by a factor of two that a learner had hidden, and deleting what did not hold earned €766 a week more

**The question, Saturday 19:20.** The system made €17,846 a week on the 8 weeks it was fitted on and €14,360 on 32 fresh ones. Was it fitted to its own weeks? One agent with no stake in any part inventoried every number, 129 of them (91 from a fitting tool, 60 of those the place table; 38 set by hand), each with how it was obtained, on which weeks, and whether other weeks confirm it (`SKEPTIC.md` §3). Then it took each part out in turn on 32 weeks nobody had played (`halal-65..96`).

**What did not hold.**
- **The on-time model's level was off by a factor of two.** On 64 weeks the fit never saw, it said 10.0% of the cars late where 4.8% were: as baked it foretold worse than a constant. A learner inside the week found the missing intercept again every week, slowly (+0.35 by Monday noon, +0.75 from Thursday), so it hid the error, and every Monday was priced as twice as risky as Wednesday: 72 orders against 89–92.
- **One sign had the wrong sign.** `known`: baked +0.25, the unseen weeks say −0.17 ± 0.06.
- **Two parts of the dealer's level predicted nothing**: −0.3 and +1.2 per mille of log-likelihood on 64 weeks, where the lane part gives 15.

**What we did.** Deleted all four: 1,948 → 1,900 lines, 129 → 123 numbers. Set the model's level once, +0.88, the same on three disjoint sets of weeks (+0.86 / +0.90 / +0.87). A level that is right makes caution cheap, so the aim went from 97% to 97.5%. Decided on `65..96`, confirmed once on `97..128`, recorded once on `129..160`. (For the final the aim is 96.5%: slide 9.)

**The effect.** Against the system before the audit, same weeks, paired per week:

| weeks | before | after |
|---|---|---|
| **fresh `halal-129..160`**, once each, after the freeze, no stride (`orch-old-record` → `orch-head-record`) | €13,547 a week, on time 96.3%, 402 orders | **€14,313 (+€766, se 221)**, on time 96.3% (−0.03 point, se 0.15), 426 orders; 24 of 32 weeks up |
| orders won Monday, same fresh weeks | 71 | 82 (+10.8, se 3.0); Monday's sales +€1,178 (se 232) |
| untouched `halal-97..128`, no stride (`skeptic-Bbase-B-s0` → `skeptic-C975-B-s0`) | €15,829, 96.2% | €16,266, 96.4%, 32 of 32 ranked |
| hold `halal-09..16`, four samples a side | | +€694 (se 142), on time +0.03 point |

**What stayed.** Taking out each of these cost money on the same untouched weeks: the harm to the cars that wait −€2,967 a week, the pickup-side signs −€1,702, two-car gigs −€1,444, the six-hour look −€1,394, the note grammar −€998. A second agent built a rival with 64 numbers fewer: equal in margin (−€76, se 184; `research/simple`), so it was judged and not chosen; its warning is on slide 10.

**One step toward the leader.** Of 164 variants of ours paired against their baselines, this is one of only two that add more than 3% orders and also earn more on each (+4.6% orders, +€0.25 an order, +0.45 point of on-time; `runs/reports/detective.md` §0).

**Figure.** Left, two pairs of bars, "the model says late / late in fact": before 10.0% / 4.8%, after 4.2% / 4.5% (fresh weeks). Right, orders won by weekday on the 32 fresh weeks: before 71 / 85 / 81 / 96 / 73, after 82 / 91 / 88 / 95 / 76. Caption: "129 → 123 numbers, +€766 a week on weeks nobody had played."

---

## Slide 8 — The graveyard: about fifty ideas played against the frozen system after the freeze; none earns more than its noise without paying for it in on-time, so the system sits at the optimum of its own design

After the freeze (Saturday 23:00 to Sunday 02:35) five research streams played about fifty variants against `8ae61c5` on the same weeks, paired (gap about thirty, chains eleven, a hunt three built of fifteen hypotheses, trade-ins three, direct offers two). Earlier rows are Saturday's brackets of every knob. Each row: margin a week against the system on the same weeks (se), on time in points.

| tried | when, weeks | margin a week (se) | on time | why it lost |
|---|---|---|---|---|
| On-time aim 96.5% instead of 97.5% | after, `halal-161..192` × 2 | +€330 (156) | −1.33 (mean 95.0%); worst week 90.5%, 10 of 64 under 93.5%, 64 of 64 ranked | not lost: it buys margin with on-time, and **the final plays it** (slide 9). Past it the knee: 96% +€401 (173), −2.01, one week of 64 at 89.6% (unranked); 95% +€224, two of 32 unranked; 98% −€1,044 (24 × 2) |
| Fee floor one step lower, 0.75 × typical | Saturday, 24 × 2 | −€771 (222) | unchanged | cheap gigs sit, the queue grows, every new car looks riskier |
| A finer fee grid, steps of 0.05 × | Saturday, 24 × 2 | −€624 (284) | −0.23 | the coarse steps are a safety margin on the model's choice |
| Gigs of 3 / 4 cars (chains) | after, 24 | −€55 (203) / −€126 | | drivers earn about €13 an hour whatever the gig holds |
| Long shared gigs, up to 12 hours (chains) | after, 24 | +€198 (204) | −0.38 (0.11) | buys orders with on-time, as a lower aim does |
| More pairs: wait 60 minutes, drive 6 hours | Saturday, 24 | +€284 (304) | −0.57 | the same trade |
| Direct offers to drivers who end a gig of ours near a waiting car | after, 24 | −€183 (136) / −€207 (131) | | 1 of 210 such offers taken: after delivering, drivers stop |
| Winning trade-ins (their weight −3.35 → −1.54) | after, `halal-161..192` × 2 | +€55 (105) | −0.02 (0.08) | 0.7 trade-ins a week, their own margin about zero |
| No six-hour look at the weekend; fees based on the lane's median (the hunt) | after, `halal-161..192` | +€12 (11); +€43 (222) | −0.05; +0.16 | inside the noise |
| Meet the drivers on the day: keep a car out of the app until 07:00 of its last day | Saturday, randomised by order number in 9 worlds | | kept half late 11.1% against 7.0% | a weak promise is far better than none |
| A crisis price after a bad night | Saturday, 14 weeks | −€481 | unchanged | |
| The second look after 12 hours instead of 6 | Saturday, 24 | −€342 | −0.11 | |

**The leader, read from the leaderboards** (`runs/reports/detective.md`: event logs of our 30 ranking worlds and both test finals, read only). Over 15 ranking runs the leading team wins 11% more orders than the top-10 median and €3.2 more on each, at the same on-time (97.2% against 97.3%), and its volume does not depend on how many drivers a world has (about 470 orders at 641 or 933 drivers). That is the fingerprint of more cars moved per driver. The chains, offers and trade-in rows above are our attempts at it. Across 164 variants of ours, each lever that adds orders loses margin on each order (−0.13 × the % of orders added − €0.9): the leader is on another frontier, not on ours with another knob. We know where our design ends.

**Figure.** A forest plot: one row per idea, a dot at its margin a week against the frozen system and a whisker of ± 2 se; a vertical line at zero. Every whisker crosses zero or lies left of it, except the lower on-time aim, drawn in a second colour: it buys margin with on-time. Inset: the frontier, x = % orders added, y = € margin per order added, 164 grey dots of ours along the line −0.13 x − 0.9, one star for the leader at (+11.4%, +3.2) far above it.

---

## Slide 9 — It holds where it has never been: 160 of 160 plays on 96 unseen weeks ranked, its first secret round at 1.33 × House best, and a restart replays the week to the cent

**Unseen weeks**, the frozen system:

| weeks | plays | margin a week | on time, mean (worst) | ranked |
|---|---|---|---|---|
| **fresh `halal-129..160`**, once, no stride (`orch-head-record`) | 32 | **€14,313** | 96.3% (92.8%) | 32 of 32 |
| untouched `halal-97..128`, no stride and stride 14 (`skeptic-C975-B-s0`, `-s14`) | 64 | €16,266 / €16,126 | 96.4% (93.2%) | 64 of 64 |
| after the freeze `halal-161..192`, strides 14 and 13 (`orch-main161-s14`, `-s13`) | 64 | €14,964 | 96.4% (92.3%) | 64 of 64 |
| **all 96 unseen weeks** | **160** | **€15,327** | **96.4% (92.3%)** | **160 of 160** |

With the practice and decision weeks: 273 plays of 160 weeks in `runs/log.jsonl`, every one ranked. The kit starter: 0 of 16.

**The final plays a measured risk.** The final asks only for a place in the top 10 ("Reaching the top 10 is enough. After that, your margin no longer counts", `challenge.md`) and the field moved past the frozen system overnight (the Sunday rounds: 00:00 closed 11th of 58, €794 under 10th; 03:00 closed 28th of 48; 06:00 19th of 20 at 06:06), so the final plays the aim at 96.5% (`3f85408`), whose cost we measured on the 64 plays of `halal-161..192`, weeks first played tonight: +€330 a week (se 156), on time 95.0% in the mean (−1.33 points), worst week 90.5%, 10 of 64 under 93.5%, 64 of 64 ranked (`orch-t965-s14`, `-s13` against `orch-main161-s14`, `-s13`); 96% earned more, +€401 (se 173), but one week of 64 ended at 89.6%, unranked, so we did not take it (`orch-t96-s14`, `-s13`).

**Secret weeks, the same for every team** (places at the round's close unless marked):

| | ours | × House best | place |
|---|---|---|---|
| Ranking round Saturday 09:00 (ideas 1–7) | €48,860 | 0.96 × | 35th of 45 |
| Ranking round Saturday 12:00 | €82,785 | 1.07 × | 22nd of 58 |
| Ranking round Saturday 15:00 | €82,278 | 1.28 × | 19th of 63 |
| Ranking round Saturday 18:00 (ideas 1–14) | €75,405 | 1.29 × | 10th of 67 |
| Ranking round Saturday 21:00 (ideas 1–14) | €79,391 | 1.20 × | 28th of 56 |
| Ranking round Sunday 00:00, the frozen system | €81,046, 5 of 5 ranked | 1.33 × | 2nd of 18 ranked at 00:06, closed 11th of 58 (10th €81,840) |
| Ranking round Sunday 03:00, the frozen system | €71,665, 5 of 5 ranked (€13,045 / €13,758 / €8,761 / €19,367 / €16,735; on time 95.9–98.0%) | 1.28 × | 15th of 18 ranked at 03:07, closed 28th of 48 |
| Ranking round Sunday 06:00, the frozen system | €69,092, 5 of 5 ranked (on time 94.0–96.9%) | 1.18 × | 19th of 20 ranked at 06:06 |
| Test final Saturday 14:00, live clock, joined on Thursday | €3,747, 97.6% on time | | 2nd of 55 |
| Test final Saturday 20:00, live clock, a full week (the final's shape) | €15,752.50, 97.2% on time | | 18th of 75 |

**A restart is a replay.** State is a fold over the world's events and the actions the world acknowledged (a journal on disk). `tools/restart_test.py`: on the frozen system 8 of 8 restarts rebuilt the same desk, and the week ended at €21,126.94 with and without them (halal-02). The test caught a real bug on Saturday (a fleet that learned inside the week: 1 of 12 restarts matched, −€2,309); the audit deleted that learner.

**A kill in the middle of the week.** On the cloud machine, started as the final starts (tmux, `final.sh`'s loop), a full week from Monday at 4× (halal-05), `kill -9` on the desk on Tuesday afternoon: €21,684.94, 98.2% on time, 570 orders; the desk rejoined by itself; 1 request unanswered (it arrived while the desk was dead); the slowest turn of an hour 38 ms in the median, 1.3 s at most, where a request allows 4.5 s (`runs/rehearse-8ae61c5.out`). The final's system, 3f85408, the same way: €23,682.94, 97.6% on time, 627 orders, 0 requests unanswered, slowest turn 290 ms (`runs/rehearse-3f85408.out`).

**Figure.** A dot plot: x = on-time share from 30% to 100% with a red line at 90%, y = margin from −€90k to +€25k. 160 dots of the frozen system on unseen weeks sit right of the line and above zero; 16 starter dots sit far left and far below. Beside it: "world's log + journal → fold → desk", drawn twice, once for play and once after a restart, with an equals sign between the two desks.

---

## Slide 10 — It knows what it does not know, to the end: what the final showed, and the risks it carries, named in advance

**The final.** €18,532.31 margin, 94.5% on time, 510 orders (the most of any team in the top 14), 0.2% not delivered; place 14 of 58 ranked teams, €552 under 10th (€19,083.95); first €22,931.

**The thesis, once more.** Its odds come true (4.2% said, 4.5% late; 44.4% said, 45.2% yes). It found where it was wrong and earned more (+€766 a week). It holds where it has never been (160 of 160).

**What would break it, said before the final.**
- **A week whose drivers are much scarcer than in any of ours: the one risk we chose.** Since the audit a week moves one thing in the on-time model, which day the flu is; such a week is braked only by the price of the delivery minimum, which sees late cars two days after we accept them. With a model one logit too easy, on time falls 2.8 points and one week ends at 90.5%; with the learner we deleted, 1.0 point (`runs/reports/simple.md`). We kept the measured constant because it earns more on every unseen set; the aim is the margin for this, and in the final it is a point thinner by choice: 96.5% instead of the frozen system's 97.5% (slide 9).
- **A week that is not the rules' week.** Slide 5 assumes one war day, one outage, one flu night. In the replay a week without a war still gains €66; without both events it loses €118. A flu on Monday has no night before it to show.
- **A Friday flu in the capital region** is still our hardest week: 94.5% on time on the mean of four samples.
- **A note in words we have not seen** is missed silently: 0.2 failed visits a week on the untouched weeks (the kit's reader: 10.6).
- **Two desks on one world.** Only a lock file and a procedure prevent it.

**What we do not know.** Two weights are not settled: `waited` (without it, +€601 a week, se 187, and −0.29 point of on-time on untouched weeks) and `short` (we win almost none of the cars it describes); the trade-in weight is settled near −1.5 and changing it is worth +€55 (se 105), so it stays. The numbers set by hand that remain (the fourth power and its cap, `CALM`, the two-car fees, `SURE`, `RETRY`, `MIN_SPAN`) have no measurement of their own; the barrier they shape keeps the floor (a flat €300 a late order ends one week at 90.3%).

Every number in this deck has the command or file that prints it again (`OPEN_NUMBERS.md`).

**Figure.** The calibration plot of slide 1 again, with the final's point added when it can be computed. Under it the three numbers, and the five risks as plain text.

---

# Backup (not shown)

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

Source: `weeks fleet3-cand-ns fleet3-cand-hold orch-base-s14` and `runs/starter-tune.out`, `runs/starter-hold.out`. Ideas 1–14 (decisions of `52aaf93`). Tune weeks without stride; hold and wide weeks with stride 14, one sample each. The frozen system on these sets: hold €15,488 a week, worst week 94.6% (`skeptic-holdC975-x-s14`); tune and wide at stride 14 €15,444, worst week 94.5% (`skeptic-twC975-x-s14`).

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

Idea 15 is not a row here on purpose: it was decided and measured on weeks nobody had played, never on the tune weeks as a set (slide 7). On the 24 tune and wide weeks at stride 14 it is +€625 a week (se 331) and +0.43 point of on-time against ideas 1–14 at the same stride (`orch-base-s14`).
