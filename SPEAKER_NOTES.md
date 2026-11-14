# Speaker notes — a 5-minute walk through `PRESENTATION.md`

For a speaker who did not write the code. Per slide: three sentences to say, then the two questions a jury member is most likely to ask, each with a truthful answer.

Before you present:
- The jury's own rule: "If an agent wrote your slides, read every line and cut each one that you cannot explain yourself." Do that. Every claim here names its source, so you can check it.
- Fill the placeholders first (`OPEN_NUMBERS.md`). Do not say a number that still carries `[UPDATE]`.
- Timing: slide 1, 40 seconds; slides 2 to 7, 30 seconds each; slides 8 and 9, 40 seconds each. Total 5 minutes.
- Use their words: dealer, request, option, gig, fee, typical fee, list price, deadline, deadline warning, delivery minimum, direct offer.

---

## Slide 1 — The answer

**Say.**
1. "In the final we made `[FINAL]`; our best ranking round was `[BEST ROUND]`."
2. "The system asks two questions about every request: what will this dealer pay, and what does this car cost us. The quote is the price that earns most between the two."
3. "Everything it knows is rebuilt from the world's event log and a journal of what we sent, so the same loop runs in practice, in the final and after a restart."

**Q: Which single idea is worth the most?**
Measured one at a time on the same 8 practice weeks: learning the dealer's price level, +€3,543 a week (€6,824 → €10,367). Pricing a car as fee plus risk, +€2,789 (€6,824 → €9,613), and it took the ranked weeks from 5 of 8 to 8 of 8. Dropping the extra reserve, +€2,431. The second look at a gig that sits, +€1,903. They were measured at different stages, so they do not add up exactly. Appendix B of the deck has the whole path.

**Q: How big is it?**
1,785 lines of Python in 10 modules, standard library only. Each module has one stated reason; the table is in `README.md`.

---

## Slide 2 — One flat fee per gig

**Say.**
1. "The kit starter raises its fee every hour. On Monday its gigs were booked after a median 7 minutes at the typical fee. From Tuesday drivers waited for the cap, 1.5 times typical, and from Friday for 2.5 times."
2. "So we post every gig at one fee, with a schedule of one step."
3. "We tested a fee that rises once in our own system: fees fell 3.6%, but the weeks that met the delivery minimum fell from 5 of 8 to 3 of 8."

**Q: You do change the fee after six hours. Is that not a rising fee?**
Yes, it is a compromise, and we measured its price. A gig's fee can be chosen again at three planned moments (six hours without a driver, the last day, the deadline warning) and when a driver is lost. It never rises on a timer. The six-hour look raises about one gig in three. From Tuesday, gigs are booked within 15 minutes up to 9 points less often than without the look. It still earns €1,903 a week more on the tune weeks: of the gigs the look raises, 92 to 97% are then booked, where before 26 cars a week sat until their deadline warning.

**Q: Is the starter comparison on the same weeks?**
No. The starter's −€72,613 is the handbook's run on seed `spread-1`. Our numbers are on our own seeds `[UPDATE if the starter was run on halal-01..08]`. The same-week evidence for this slide is our own rising-fee test (`offers-q1` against `base1`).

---

## Slide 3 — A car costs its fee plus its risk

**Say.**
1. "In weeks with random fees, a car booked before its deadline warning was on time 96% of the time; a car that was not, 25%."
2. "A higher fee stops helping above 1.15 times typical. What is left is the car itself: its hours of room, the lane, our own queue."
3. "So the driver side estimates the chance of a late car and reports one number, fee plus risk. That number replaced four hard rules: €6,824 became €9,613 a week, and the worst week went from 83.9% to 93.8% on time."

**Q: How do you know the chance of a late car? Is it calibrated?**
It is a logistic model with 12 weights, fitted on our own practice weeks by `tools/fleet_fit.py`. It is pessimistic. On the 4,410 orders it was fitted on it predicted 7.5% late and 6.6% were late. On the weeks it then played itself it predicted 10.3% and 6.0% were late. We tried a better-calibrated fit (9.0% predicted) and earned €2,266 a week less. The calibrated model accepts more risk on Monday, the late cars show two days later, and the price of the minimum then cuts volume for the rest of the week. So we kept the pessimistic one. We know that this is a safety margin and not a principle.

**Q: Why 96%, why €300, why the fourth power?**
They are set by hand. 96%: with a target of 95% one unseen week ended at 89.7% on time and another at 90.2%; with 96% the worst unseen weeks are 91.5 to 92.5%. The price of the minimum is €300 × (expected late share ÷ allowed share)⁴: about €19 at half the allowance and €300 at it. An earlier version charged a standing €300 on every point of risk. It asked 0.48 × list price more for the faster option, and dealers pay 0.12 to 0.15 × for it, so only one win in six was on the fastest option (42 of 253).

---

## Slide 4 — The dealer side

**Say.**
1. "The price at which a dealer buys half the time moves from 1.0 to 1.8 times the list price between worlds and days, so a fixed price wins 177 cars in one world and 485 in another."
2. "We model the dealer's yes as a logistic curve around a level, and the level as a sum of parts: world, day, dealer, places, lane. Every yes and no moves the parts it touched."
3. "We quote the price with the highest expected margin over the car's cost, and offer every option at that same margin. Learning the level gave €6,824 → €10,367 a week; offering every option gave another 5.5% on tune weeks and 12.7% on hold weeks."

**Q: Why the same margin on every option?**
Because of how a dealer chooses (slide 5): among the options it would buy, it takes the one with the largest threshold minus price, in euros. If every option carries the same margin over its own cost, we earn the same whichever it takes, and it takes the faster one exactly when speed is worth more to it than it costs us.

**Q: The competitor answers your wins. Do you model that?**
No, on evidence. We measured it: a dealer's level falls about 4% per unit of the share of its Monday requests that we won, so about 2% at the biggest dealer after we took 30% of its Monday. Trust is larger: about +1% per order delivered on time. The day and dealer parts of the level absorb the competitor's answer.

---

## Slide 5 — We bisected the competitor

**Say.**
1. "A practice world is deterministic, and on Monday nothing we do feeds back. So we replayed Monday 16 times with different prices, and bracketed the price threshold of ten thousand options, half of them to within half a percent."
2. "It told us that price precision is spent: our learner earns €2,103 a Monday, and a pricer that knows every lane's level exactly earns €2,065."
3. "It also gave us the dealer's rule for choosing between options, which is why we quote every option at one margin, and it showed that price tables from other worlds do not carry over, so we ship none for lanes or dealers."

**Q: Is that not fitting to the simulator? What of it reaches the final?**
We used it to learn how dealers decide, not to store prices. What we shipped is structural: the menu at one margin, the confirmation that trust is about 1% per order, and the decision not to ship lane or dealer tables. No price from a bisected world is used anywhere. The hold seeds were never bisected: `runs/bisect/` holds seeds 01–08 and 17–32 only.

**Q: An oracle earns €3,723 and you earn €2,103. Why is no money left?**
That oracle knows each request's own factor, 8.2% (sd) around its lane's level. We tested the request's typical fee, car, note, opening hours and hour of the day against it: nothing predicts it. The organisers' handbook also names "a small factor for the request alone". The part that can be known is the level, and there we are at the ceiling.

---

## Slide 6 — The queue is the scarce thing

**Say.**
1. "Up to about 340 orders a week drivers were not our limit. Our late orders were one tail: 26 cars a week that sat 70 hours at the lowest fee, and half of them arrived late."
2. "So a gig that sits six hours has its fee chosen again, and a new car can share a gig with a car whose pickup is near its delivery, at 0.70 times the two typical fees."
3. "The trade-in told us the fee: its typical fee is half of two single ones, so the trip home is half a driver's cost. A quarter of our cars now go in two-car gigs, at 0.80 times typical and 99.3% on time."

**Q: Why 0.70 and 0.85, 30 km and 5 hours?**
From randomised tests inside the same worlds. Pairs with at most 4 hours of driving at 0.70 × were booked 85% of the time, in a median 4 minutes; their fees came to 0.89 × typical against 1.21 × for the same cars as two gigs. Pairs over 6 hours were booked 29% of the time. When one of the two cars already sits in the app, 0.70 × delivered 46% as a pair and 0.85 × delivered 76%, at the same cost in the end. 30 km is the radius in which the app notifies a driver of a new gig.

**Q: The second look added 88 orders a week. Did on-time suffer?**
On the tune weeks, no: the worst week went from 94.5% to 94.7%. On 4 hold weeks, yes: the worst week went from 93.7% to 92.2%, while the margin rose from €13,016 to €14,588 a week. The look buys volume and spends some of our room above the minimum.

---

## Slide 7 — Notes

**Say.**
1. "41% of requests carry a note in Finnish, Swedish or English, and the world acts on it whether we read it or not. With the kit's reader we paid 10.6 failed visits a week."
2. "Our reader is a small grammar: clauses, cue words, clock times and days, one fact per clause. A correction replaces a time, a denial deletes it."
3. "It reads 22,099 of 22,099 labelled notes, and failed visits fell to zero."

**Q: 100% sounds fitted. What about a note you have not seen?**
The vocabulary was built on 24 labelled worlds. On 26 fresh worlds its first run misread 2 notes of 11,432; on the hold worlds, 1 of 3,539. All three are fixed, so today's 100% includes them. With one more random typo in every note it reads 99.69%. A template with cue words outside the vocabulary would be missed silently; that is the real risk.

**Q: Why not a language model?**
The reader takes 13 microseconds a note, needs no network inside a 4.5-second deadline, and gives the same facts on a replay, which the restart depends on. We could also score it against the world's truth on every note. We did not test a language model as a reader.

---

## Slide 8 — Robust

**Say.**
1. "On 26 practice weeks every week met the delivery minimum. 18 of them were never fitted on: €13,057 a week there, worst week 91.5% on time."
2. "A restart replays the world's log and our journal through the same code. The test compares the new desk with the dead one object by object: 12 of 12 identical, and the week ends at the same margin to the cent."
3. "The live loop answered every request of a week at the final's clock from a phone hotspot, with a quote at 69 ms median against 4.5 seconds allowed, and rejoined by itself after a dead resolver, cut streams and a kill."

**Q: Why should we believe 8 seeds?**
Do not; believe the others. The 8 tune weeks are the ones we fitted on, and they flatter us: €16,838 a week. On 18 weeks we did not fit on we earn €13,057, and the worst week is 91.5% on time. On the 5 secret weeks of the Saturday 12:00 ranking round we earned €16,557 a week, worst week 94.2%. Three limits: one seed moves by €3,000 between two variants, so we cannot resolve differences under about €500 a week; 6 unseen weeks were not played because the harness lost the server under them (timeouts and one restart); and we picked the on-time target of 96% after looking at the unseen weeks, so for that one number they are not a clean test.

**Q: What exactly happens when the process dies in the final?**
A shell loop starts it again within a second. The new desk reads the world's whole log and its snapshot, replays them with the journal of what we sent, and then quotes every request that is still open and posts every car that has no gig. While it is down, requests go to the competitor and booked drivers keep driving. On another machine, without the journal, every order and gig is still recovered, but the dealer side starts again from its prior: that cost 2 to 4% of a week in two early measurements. One honest detail: on seed halal-09, 11 of 12 restarts rebuilt an identical desk; the week still ended at the same margin to the cent, and we have not traced the one difference `[UPDATE if traced]`.

---

## Slide 9 — What did not work, what would break it

**Say.**
1. "Direct offers did not work for us: 75,000 offers, 85 accepted. Neither did opening low, trade-ins at a higher fee, or a better-calibrated risk model, which earned less."
2. "What would break us: a week whose drivers behave unlike our practice weeks, because the driver model can move only one number during a week and late cars show two days after we accept them."
3. "And a note written in words we have not seen is missed silently. Our worst unseen week was 1.5 points above the minimum."

**Q: What happens in a world unlike the practice ones?**
The dealer side adapts: its world and day parts are learned from the first answers and sit within 5% by 10:00, and it already handled levels from 1.20 to 1.49 times the list price. The driver side adapts less. Its weights come from practice weeks; during a week it learns one intercept, limited to one logit either way, and the price of the minimum cuts volume once late cars appear. That reaction is two days late. If Monday and Tuesday of a week were much harder than practice, we could end under 90%. We did not measure the surprises (outage, flu, bulk order) separately from the weeks they occur in.

**Q: What would you do with one more day?**
Sell the faster option. The fleet's cost asks a median 0.33 × list price more for same day; dealers value it at a median €14.5, and the extra cost we actually paid on same-day orders was about €8 of fee and up to 2 points of lateness. Our estimate from the bisection data is about €1,000 a week; it is an estimate, not a measurement. Second, protect Monday: start the week with the price of the minimum already on, instead of waiting for the week's own late cars.

---

## Questions that can come on any slide

**How much of this was written by agents?**
Almost all of the code, the experiments and the first draft of these slides. 76 of the 78 commits in the repository carry a `Co-Authored-By: Claude` line. The work ran from Saturday 02:25 as five research streams in separate git branches (dealer side, driver side, notes, direct offers and pairs, the live loop) with one coordinating agent that merged them. The rules the agents worked under are in `RESEARCH.md`: few parts, each with a reason in one sentence; every baked-in constant regenerated by a script from saved weeks; fit on 8 seeds and never on the hold seeds; for each idea the triple idea, why, effect on the same seeds; failed ideas logged too. `[FILL IN, truthfully: what the two of you did yourselves — the brief, the choice of ideas, the checks you made on Saturday and Sunday, what you changed.]` Do not claim more than that. What you can claim: every number on the slides is reproduced by a command in `OPEN_NUMBERS.md`, and you have run them.

**Did the agents see the hold weeks?**
No constant was fitted on them. Two decisions were made after looking at them: the on-time target went from 95% to 96% because one hold week ended at 89.7%, and the wide weeks were used the same way. The note reader's vocabulary was built from tune and wide worlds, and checked on hold only at the end. The dealers of the wide worlds' Mondays were bisected; those of the hold worlds never were.

**Why should a dispatcher in real life care about any of this?**
Three things carry over without the simulator: a fee that rises teaches drivers to wait; a car's cost is mostly its risk of finding no driver in time, not its fee; and the return trip is half of a driver's cost, so a car that shares a gig with one that starts where it ends costs about a sixth less in fees (0.80 against 0.97 × the typical fee in our weeks).

---

## Words you may be asked to explain

| Word | Meaning in this system |
|---|---|
| fold | State is computed by applying each event of the world's log, in order, to an empty state. No other memory exists. |
| journal | A file with every batch of actions we sent and the world's answer to each. The world's log does not repeat our quotes, so the journal does. |
| level | The log of the price, as a multiple of the list price, at which a dealer buys half the time. |
| Kalman step | After a yes or no, each part of the level moves in proportion to how uncertain it still is, and becomes a little more certain. |
| logistic | An S-shaped curve from 0 to 1. Here: the chance of a yes falls as the price rises, by about one logit per 10% of price. |
| price of the delivery minimum | A cost added to every risky car. It is near zero while we expect far fewer late orders than 4%, and steep near 4%. |
| queue | Our orders that are in the app without a driver. Drivers choose among our own gigs, so a new gig competes with them. |
| tune / hold / wide | Practice seeds 01–08 (fitted on), 09–16 (only to confirm), 17–32 (more unseen weeks). |
| bisect | Halve a price bracket with each replay of the same Monday, until the dealer's threshold is known to 0.5%. |
