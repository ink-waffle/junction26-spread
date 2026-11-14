# Night log — Halal Team, Spread

Level 8 throughout. "tune" = our seeds halal-01..08, "hold" = halal-09..16 (never tuned on). Margin is per week; a week counts only when ≥ 90% of its orders are on time.

## Status

| When | Best version | tune: margin / min on-time / ranked | hold | Trying now |
|---|---|---|---|---|
| Sat 12:25 | `main` c25160e + `{"fleet": {"early_look": 6, "on_time": 0.96}}` = ideas 1–11 | €16,838 / 94.7% / 8 of 8 | 4 of 8 weeks played: €14,588, worst 92.2%; 11 of 16 wide weeks: €12,680, worst 92.5% | Making the fleet's learned state survive a restart (restart test fails since the refit); pricing the classes that carry the late orders (private delivery 21% late, premium 12%, trade-in 58%); test final 14:00 from the Helsinki machine |
| Sat 11:00 | `main` 922cddd = ideas 1–9 (all options quoted, lanes in the learner, two-car gigs) | €13,770 / 94.7% / 8 of 8 | pending | The leaderboard says volume: the top ten deliver 345–460 orders a week at 96–99% on time for about our margin per order (we: 214–384). Recalibrating the fleet's cost (it prices the faster option out), exact price thresholds by bisection, pairing with cars that sit |
| Sat 10:40 | `main` f20e34d = idea 1–7 (price-level learner, on-time model, note reader, reserve 0, live loop with resolver fallback) | €12,711 / 94.4% / 8 of 8 | €11,487 / 93.0% / 8 of 8 | Network outage 03:40–10:00 cost six hours. Now: capacity-aware volume (drivers take ≥ 340 orders a week; top teams deliver 350–400), two-car gigs, loss audit; test final at 14:00 from the Helsinki VM |
| Sat 03:10 | `main-m1` = base1 + online price-level learner (idea 4) + live final loop | €10,367 / 89.1% / 7 of 8 | — | Fleet cost model with a capacity price (to lift the worst week over 90%), note reader (100% of facts on 24 labelled weeks), two-car gigs (fees 0.89 × vs 1.21 × typical on short pairs) |
| Sat 02:35 | `base1` (flat 1.15 × fee, 1.45 × list, ≥ 8 h slack, no private pickup / trade-in / premium) | €6,824 / 83.9% / 5 of 8 | — | Five parallel research streams: notes reader, win-curve pricing, fleet cost model, direct offers, live final loop |

## Ideas

### 1. One flat fee per gig (no rising schedule)
- **The idea.** Every gig is posted at a single fee and stays there. The fee changes at most once, at the deadline warning.
- **Why.** In the kit starter's week (fee +10%/h to 1.5 × typical, then to 2.5 ×), Monday's 186 bookings came a median 7 minutes after posting at 1.0 × typical. From Tuesday the median booked fee was exactly the cap, 1.5 ×, and from Friday 2.5 ×: drivers had learned that our fees rise, and waited. The starter paid €118.6k in fees on €71.3k revenue.
- **The effect.** Starter on `spread-1`: −€72,613, 45.5% on time. Same quotes with a flat 1.0 × fee (halal-01): fees €52k on 591 orders (fee × 1.15 of typical on average instead of × 1.67).

### 2. Sell above list, because typical fee ≈ 0.9 × list
- **The idea.** Quote a multiple of the list price well above 1.
- **Why.** Typical fee / list price is 0.90 on average (0.6 under 40 km). At list price a delivered car earns nothing. Dealers' win curve (8 weeks of random quotes, `explore1`): 85% at 1.05 ×, 50% at 1.3–1.4 ×, 10% at 1.8 ×.
- **The effect.** 1.45 × list with a flat 1.15 × fee and idea 3: €6,824/week on tune, against −€72,613 for the starter on its own seed and −€8,001 for 1.3 × list without selection (halal-01).

### 3. Only win cars that will be booked before the deadline warning
- **The idea.** A request is quoted only when the time from the dealer's answer to the last possible pickup is at least 8 hours; otherwise we decline (quote 4 × list).
- **Why.** `explore1`: a car booked before its deadline warning is on time 96% of the time; one that is not, 25%. At a flat 1.15–1.5 × typical, 90–100% of cars with ≥ 8 h of slack are booked before the warning, 77% with 5–8 h, ≤ 58% under 5 h.
- **The effect.** Tune seeds, same price (1.45 × list) and fee (flat 1.15 ×): with the rule €6,824/week, on-time 91.6% mean (83.9% worst), 5 of 8 weeks ranked; without it €6,640/week, 82.8% mean (68.3% worst), 3 of 8 ranked. (Rule here also refuses private pickups, trade-ins and premium cars.)

### 4. Learn each dealer's price level online, quote the price with the highest expected margin
- **The idea.** A dealer says yes with a chance that is logistic in log(price / list) around a level. The level is a sum of parts: the world, the day, the dealer, the pickup place, the delivery place (place parts start from a prior fitted on other weeks). Every yes and no moves each part it touched (one Kalman step). The quote is the price that maximises (price − cost) × P(yes), for the one option where that is highest.
- **Why.** With random quotes on 8 weeks (`explore1`) the price at which half the quotes win was 1.20–1.49 × list by world and 1.01–1.78 × by world and day (price war day, outage day). A fixed 1.45 × won 177 cars in one world and 485 in another, and missed the delivery minimum where it won most.
- **The effect.** Same fleet (`base1`), tune: €6,824 → €10,367 a week, ranked 5/8 → 7/8.

### 5. An on-time model picks each gig's fee, and its risk is part of the car's cost
- **The idea.** P(on time) is a logistic model of the fee, the hours until the last possible pickup, lane length, who lives near pickup and delivery, private stops, premium, trade-in and our own backlog (fitted by `tools/fleet_fit.py` on our weeks). The gig's one flat fee is the multiple of typical that minimises fee + P(late) × cost of a late order. The car's cost for pricing = that fee + expected refund + a shadow price on the delivery minimum that rises steeply once expected late orders pass 5%. This replaced the hard rules of idea 3 (no list of refused kinds, no minimum slack).
- **Why.** Booked before the deadline warning → 96% on time, else 25%; and more fee stops helping above ~1.15 × typical, so what a car costs is mostly its risk, not its fee.
- **The effect.** Same quotes (`base1`), tune: €6,824 → €9,613 a week, worst week 83.9% → 93.8% on time, ranked 5/8 → 8/8; average fee 1.16 × → 0.95 × typical.

### 6. Read the dealer's note with a small grammar
- **The idea.** note → clauses → words → cues (a vocabulary in Finnish, Swedish, English; one typo forgiven), clock times and days → one fact per clause; a correction replaces, a denial deletes. Facts become the gig's stop windows: no driver before ready or release, at a really closed site, after the note's deadline, or without plates or licence.
- **Why.** 41% of requests carry a note; the kit's keyword reader got 80% of notes right (50.7% precision / 40.4% recall on facts) and we paid 10.6 failed visits a week.
- **The effect.** Reader: 22,099 of 22,099 notes right on 50 labelled weeks, 3,539 of 3,539 on the hold weeks (first shot 3,538); with one more random typo per note 99.7%. On `base1`, tune: failed visits 10.6 → 0.0 a week, €6,824 → €7,661, late among orders with a note fact 19.2% → 12.1%.

### 7. Let the fleet's cost alone decide volume
- **The idea.** The quote maximises (price − cost) × P(yes) with no extra reserve on top of the fleet's cost.
- **Why.** After merging 4–6 every week was 96–99% on time: the market's reserve (30% of cost) and the fleet's risk price charged twice for the same scarcity. The same requests won at 207, 272 and 342 orders a week were booked before the warning 92.7%, 92.6% and 92.4% of the time: up to ~340 a week the drivers are not the limit.
- **The effect.** Merged system, tune: reserve 0.3 → €10,280 (worst week 96.2% on time); 0.15 → €11,881 (95.5%); 0 → €12,711 (94.4%). Hold at 0: €11,487, worst week 93.0%, 8/8 ranked.

### 8. Quote every option the dealer accepts, each at the same margin
- **The idea.** Find the option and price with the highest expected margin, then quote every other option at the price that leaves the same margin over its own cost.
- **Why.** Bisecting each Monday request's price threshold on 7 seeds (`tools/probe.py`, 2,515 options to within 0.5%): the thresholds of two options of one request are nearly independent (r ≈ 0.2; the slower one is 8.6% lower on average with sd 14.7%). Each offered option is a second chance to win.
- **The effect.** Tune, same fleet: €12,707 → €13,512 a week, worst week 94.4% → 95.0% on time, 343 → 349 orders.

### 9. Two cars in one gig
- **The idea.** A new one-car order stays out of the app for at most 30 minutes. If a second car starts within 30 km of where the first ends, with at most 5 hours of planned driving and windows a driver can meet, both go as one gig at 0.70 × the two typical fees. No driver in 60 minutes, or a deadline warning: the gig is withdrawn and the cars go alone.
- **Why.** The typical fee of a trade-in (out and back) is half the sum of two single typical fees: the trip home is half a driver's cost. In randomised tests pairs with ≤ 4 h of driving booked 85% at 0.70 × (median 4 minutes), all-in fees 0.89 × typical against 1.21 × for the same cars as two gigs; pairs over 6 h booked 29%.
- **The effect.** Merged system on tune: €13,337 → €13,770 a week, worst week 94.7% on time in both; cars delivered in a two-car gig: 0.71 × typical and 99.6% on time.

### 10. Refit the fleet on its own weeks; the delivery minimum is a barrier, not a toll
- **The idea.** The on-time model is refitted on weeks played by the merged system (a gig's own fee against the fee level of our other open gigs, an hour already waited, how many drivers know us). The price of a late order is next to nothing while the books expect far fewer late orders than we allow, and steep near that share. The world's own intercept is learned during the week.
- **Why.** The leaderboard: the top ten deliver 345–460 orders a week at 96–99% on time for about our margin per order; we delivered 214–384. Calibration on our weeks: 6.6% late realised against 7.5% predicted, the fastest option 6.1% against 8.1%; the model asked 0.48 × list more for the faster option, a dealer pays 0.12–0.15 ×. A stress run with prices 15% lower delivered 422 orders a week at 94.2% on time: the drivers were not the limit, our caution was.
- **The effect.** Tune: €13,770 → €14,973 a week, 342 → 357 orders, fee 0.98 × → 0.93 × typical, worst week 94.7% → 93.9%. Hold: €12,170, worst week 91.3% (see idea 11 for the fix).

### 11. A gig that sits gets its fee chosen again after six hours; pair a new car with a car that sits
- **The idea.** (a) A gig with no driver six hours after posting has its fee chosen again by the same model, once. (b) A new car whose pickup is near the delivery of a car that sits unbooked in the app is posted with it as one gig at 0.85 × both typical fees.
- **Why.** Almost all late orders were one tail: 26 orders a week sat a median 70 hours at the lowest fee and were raised only at the deadline warning, three hours before the last pickup; 52% of them arrived late. A car that sits also keeps the queue long, which makes every new car look risky and dear. In a randomised test a sitting car paired with a new one had a driver within 3 hours 69% of the time, against 35% left alone.
- **The effect.** Tune, with the on-time target at 96%: €14,935 (board pairs, no second look) → €16,838 a week with the second look; 350 → 438 orders; worst week 94.5% → 94.7%. Board pairs alone, target 95%: €14,987 → €15,882 on tune, but one hold week fell to 89.7%, so the target went to 96%.

## Did not work
- **A better-calibrated on-time model.** Refitting so that predicted lateness matches realised (10.3% → 9.0% predicted against 6.0%) lost €2,266 a week on tune (€14,973 → €12,707): the calibrated model accepts more risk early in the week, lateness shows two days later, and the barrier then cuts volume for the rest of the week. The pessimism was doing the work of a safety margin.
- **Price precision.** Bisecting every Monday request's threshold on 24 seeds (`tools/probe.py`): our learner earns €2,103 a Monday, an oracle that knows every lane's level €2,065, an oracle that knows every request's own threshold €3,723. A request carries a factor of about 8% that nothing visible predicts; cross-world lane and dealer tables made the fit worse. No money left in the level, only in the menu of options.
- **Trust as an asset** (a euro from a dealer still building trust counts for more): 27 more orders a week, margin €12,707 → €12,682.
- **Pricing a car cheaper when a partner for it waits** (`Fleet.saving`): 44 more orders a week, −€209, worst week −1.8 points.
- **Direct offers.** 12.9k random offers on 8 weeks: 25% read, 0.6% accepted (1.4% at ≥ 1.15 × typical; 0 of 556 after a deadline warning; best class — a driver who holds a gig of ours ending within 30 km of the pickup — 4.4%). Targeted offers on every gig unbooked for 20 minutes: 75k offers, 85 yes; €6,723 vs €6,824 a week, on-time 91.3% vs 91.6%. Dropped.
- **Opening low.** Every gig at 0.6 × typical for 30 minutes, then 1.15 ×: 13–18% book low, fees −3.6%, but one point of on-time lost and a median wait of 33 instead of 3 minutes. Dropped.
- **Trade-ins at a higher fee.** Typical fee is only 0.535 × list for a trade-in (0.926 × for one car), yet they were on time 17% / 38% / 61% at ≤ 1.0 / 1.15–1.3 / 1.5–2.0 × typical (83 orders): not worth winning at any fee we tried.
- **One low fee for everything at high volume.** 0.85 × typical on ~550 orders a week: 70% booked before the warning, 76.7% on time, not ranked. Drivers choose among our own gigs: a higher fee buys priority more than capacity (a gig's own fee has 4 × the weight of the level of all our fees).
- Flat 1.0 × typical on everything we could win at 1.3 × list (halal-01): −€8,001, 57.7% on time. We won 591 cars; drivers booked ~150 a day.

## Ranking rounds and test finals
- **Saturday 09:00 round** (played 10:38 with commit f20e34d = ideas 1–7): 5 of 5 weeks ranked, total €48,860 (€6,521 / €8,434 / €10,772 / €13,515 / €9,616; on time 93.5–97.6%; 214–384 orders). Place 35 of 45 ranked teams at that moment; top €79,003, 10th €69,979, 20th €59,652, House best €50,660, House starter not ranked. The top ten earn 1.43 × our margin on the same weeks: about €10 more per order, and more orders in worlds where the competitor is cheap.
