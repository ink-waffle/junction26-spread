# Speaker notes — a 5-minute walk through `PRESENTATION.md`

For a speaker who did not write the code. Per slide: three sentences to say, then the two questions a jury member is most likely to ask, each with a truthful answer.

Before you present:
- The jury's own rule: "If an agent wrote your slides, read every line and cut each one that you cannot explain yourself." Do that. Every claim here names its source, so you can check it.
- Fill the placeholders first (`OPEN_NUMBERS.md`). Do not say a number that still carries `[UPDATE]`.
- Timing: ten slides, 30 seconds each. If you must cut, cut slide 8 (notes) to one sentence and slide 10 to its second sentence.
- Use their words: dealer, request, option, gig, fee, typical fee, list price, deadline, deadline warning, delivery minimum, direct offer.
- State of these notes: Saturday 17:45, commit `0b050b8`, ideas 1–14 of `NIGHT_LOG.md`.

---

## Slide 1 — The answer

**Say.**
1. "In the final we made `[FINAL]`; in our best ranking round we earned 1.28 times the organisers' best system on the same weeks, and in the test final we were 2nd of 55 `[UPDATE]`."
2. "The system asks two questions about every request: what will this dealer pay, and what does this car cost us. The quote is the price that earns most between the two."
3. "Nobody announces the price war, the outage or the flu, so each side works out which day it is; and everything the system knows is rebuilt from the world's event log, so a restart continues as the same desk."

**Q: Which single idea is worth the most?**
Measured one at a time on the same 8 practice weeks: learning the dealer's price level, +€3,543 a week (€6,824 → €10,367). Pricing a car as fee plus risk, +€2,789, and it took the ranked weeks from 5 of 8 to 8 of 8. Dropping the extra reserve, +€2,431. The second look at a gig that sits, +€1,903. They were measured at different stages, so they do not add up exactly. The later ideas (the town's drivers, the surprise days) buy on-time more than money: the worst hold week went from 91.5% to 93.2% on time and the worst wide week from 92.6% to 93.4%. Appendix B of the deck has the whole path.

**Q: How big is it?**
1,948 lines of Python in eleven modules, standard library only `[UPDATE: recount on the frozen commit]`. Each module has one stated reason; the table is in `README.md`, and `REVIEW.md` is our own reading of where a reader still stumbles.

---

## Slide 2 — One fee per gig

**Say.**
1. "The kit starter raises its fee every hour. On Monday its gigs were booked after a median 7 minutes at the typical fee; from Tuesday drivers waited for the cap, 1.5 times typical."
2. "So a gig of ours has one fee. It is chosen again at four moments only: after six hours without a driver, on the last day, at the deadline warning, and when a driver is lost."
3. "The look after six hours earned €1,900 a week, and we measured what it teaches: on Fridays 33% of new gigs are booked within 15 minutes with it, against 48% without."

**Q: You do change the fee. Is that not a rising fee?**
It is a compromise, and we measured both sides of it. With a fee that never moved, 26 orders a week sat for a median 70 hours and half of them arrived late. One look after six hours earned €1,903 a week (€14,935 → €16,838): 88 more orders, and the worst week no worse. Drivers do learn from it (71 / 67 / 59 / 58 / 33% booked within 15 minutes, Monday to Friday, against 73 / 71 / 65 / 67 / 48%). More looks, daily or six-hourly, or steps up to twice the typical fee, did not earn more. A raise sends no notification, so after a gig's first minutes a higher fee reaches few drivers.

**Q: Is the starter comparison on the same weeks?**
Yes, since Saturday afternoon. On our 8 tune weeks the starter makes −€63,232 a week at 52.1% on time and ranks in none; we make €17,846 at 96.9%. On the 8 hold weeks: −€68,908 against €14,806. That compares whole systems. The evidence for the fee alone is our own test of a fee that rises once: weeks ranked 5 of 8 → 3 of 8 on the same weeks.

---

## Slide 3 — A car costs its fee plus its risk

**Say.**
1. "In weeks with random fees, a car booked before its deadline warning was on time 96% of the time; a car that was not, 25%. And above 1.15 times typical a higher fee books no more cars."
2. "So the driver side estimates the chance of a late car and reports one number, fee plus risk. That number replaced four hard rules: the worst week went from 83.9% to 93.8% on time."
3. "Then we taught the model where the drivers live: orders from yards with three drivers nearby were late 12.6% of the time, with more than fifty nearby 3.3%. With that and an aim of 97%, late orders on weeks it never saw fell from 23 to 16 a week."

**Q: How do you know the chance of a late car? Is it calibrated?**
It is a logistic model with 16 weights, fitted on our own practice weeks by `tools/fleet_fit.py`. It is pessimistic on purpose: it says 12.9% late where 6.4% are, and one number per week, learned from the week's own outcomes, corrects that within about forty orders. We tried a better-calibrated fit and earned €2,266 a week less: it accepts more risk on Monday, and the late cars show two days later. Two of the 16 weights (the drivers who know us, an hour already waited) no longer have support in a refit. We left them in, because taking them out changes decisions and we have not tested that on 24 weeks.

**Q: Why 97%, why €300, why the fourth power?**
They are set by hand, and the 97% is measured. On 24 tune and wide weeks, an aim of 96.5% gave €15,081 a week at 95.6% on time, 97% gave €14,608 at 96.2%, and 97.5% gave €14,269 at 96.6%. We chose 97% for the final: a week under 90% is then four to five standard deviations away. The price of the minimum is €300 × (expected late share ÷ 3%)⁴: about €19 at half the allowance and €300 at it. We bracketed the aim again on Saturday evening: 96.5% gives +€112 a week (se 176) for half a point of on-time.

---

## Slide 4 — The dealer side

**Say.**
1. "The price at which a dealer buys half the time moves from 1.0 to 1.8 times the list price between worlds and days, so a fixed price wins 177 cars in one world and 485 in another."
2. "We model the dealer's yes as a logistic curve around a level, and the level as a sum of parts: world, day, dealer, places, lane. Every yes and no moves the parts it touched."
3. "We quote the price with the highest expected margin over the car's cost, and offer every option at that same margin: learning the level gave €6,824 → €10,367 a week, and offering every option another 5.5% on tune weeks and 12.7% on hold weeks."

**Q: Why the same margin on every option?**
Because of how a dealer chooses (slide 5): among the options it would buy, it takes the one with the largest threshold minus price, in euros. If every option carries the same margin over its own cost, we earn the same whichever it takes, and it takes the faster one exactly when speed is worth more to it than it costs us. Today the faster option costs a median €11 more in our quotes, and dealers value it at a median €14.5.

**Q: The competitor answers your wins. Do you model that?**
No, on evidence. We measured it: a dealer's level falls about 4% per unit of the share of its Monday requests that we won, so about 2% at the biggest dealer after we took 30% of its Monday. Trust is larger: about +1% per order delivered on time. The day and dealer parts of the level absorb the competitor's answer.

---

## Slide 5 — We bisected the competitor

**Say.**
1. "A practice world is deterministic. So we replayed a day many times with different prices, and each yes or no halved the bracket around the dealer's threshold: ten thousand options on Mondays, then 24,000 across every day of 24 weeks."
2. "It told us that price precision is spent: our learner earns €2,103 a Monday, and a pricer that knows every lane's level exactly earns €2,065."
3. "It also gave us the dealer's rule for choosing between options, showed that price tables from other worlds do not carry over, and measured the week's events exactly, which is the next slide."

**Q: Is that not fitting to the simulator? What of it reaches the final?**
We used it to learn how dealers decide, not to store prices. What we shipped is structure: the menu at one margin, the size of the price war and of the outage as the rules state them (20% and 30%), and the decision not to ship lane or dealer tables. No price from a bisected world is used anywhere. The hold seeds were never bisected: `runs/bisect/` holds seeds 01–08 and 17–32 only.

**Q: An oracle earns €3,723 and you earn €2,103. Why is no money left?**
That oracle knows each request's own factor, 8.2% (sd) around its lane's level. We tested the request's typical fee, car, note, opening hours and hour of the day against it: nothing predicts it. The organisers' handbook also names "a small factor for the request alone". The part that can be known is the level, and there we are at the ceiling.

---

## Slide 6 — The week's surprises, weighed on both sides

**Say.**
1. "A level 8 week has a price war day, an outage day and a flu day, and nobody says which. Our dealer side used to notice a war after 18 requests and an outage after 67 or never."
2. "Now the dealer side weighs all 600 possible weeks with every answer: it names the war day right in 24 of 24 weeks, after a median 5 answers. The driver side reads the flu from the first hour of each day, when sick drivers give back a third of that day's bookings."
3. "The dealer side gained €202 a week in an exact replay; the driver side gained 0.4 points of on-time at the same margin, and our hardest week went from 92.3% to 94.6%."

**Q: You were told the rules of the events. What is creative here?**
The rules say that the events exist, not when or where. Two things are ours. First, treating the week as one of 600 possible weeks and letting every answer weigh all of them, instead of letting a "day" number chase each one: a war and an ordinary cheap day then differ in what they ask of the day, and we keep one belief for each case. Second, finding that the flu shows itself at all. We looked in views and bookings and found nothing. We ran a census with direct offers that pay nothing: in 7 of 20 weeks it found a day when 15–35% of the regular readers were silent, but that was the night that takes our bookings in only 2 of them. Then we saw that on one night a week 22–57% of the bookings held for that day come back in its first hour, against 2.7% on other nights. That count needs no extra action.

**Q: What if the final's week has no war, or two?**
Then we lose a little. In the replay a week without a war still gains €66 over the old dealer side; a week without an outage loses €2; a week with neither loses €118. If no war has been heard by Friday morning, the dealer side starts Friday about 99% sure that today is the day, and corrects itself from the answers. A flu on Monday cannot be seen in advance: Monday has no night before it with bookings to give back.

---

## Slide 7 — Two cars in one gig

**Say.**
1. "The typical fee of a trade-in, one car out and one back, is half of two single typical fees. So the trip home is half of what a driver is paid for."
2. "A new car waits up to 30 minutes for a second car whose pickup is within 30 km of its delivery; the two go as one gig at 0.70 times both typical fees."
3. "28% of our cars now travel that way, at 0.81 times the typical fee and 98.8% on time."

**Q: Why 0.70 and 0.85, 30 km and 5 hours?**
From randomised tests inside the same worlds. Pairs with at most 4 hours of driving at 0.70 × were booked 85% of the time, in a median 4 minutes; their fees came to 0.89 × typical against 1.21 × for the same cars as two gigs. Pairs over 6 hours were booked 29% of the time. When one of the two cars already sits in the app, 0.70 × delivered 46% as a pair and 0.85 × delivered 76%, at the same cost in the end. 30 km is the radius in which the app notifies a driver of a new gig.

**Q: Why not pair more?**
We tried: a wait of 60 minutes and pairs up to 6 hours gave +€284 a week (se 304) for −0.57 point of on-time on 24 weeks. That buys volume the way a lower on-time aim does, so we left it.

---

## Slide 8 — Notes

**Say.**
1. "41% of requests carry a note in Finnish, Swedish or English, and the world acts on it whether we read it or not. With the kit's reader we paid 10.6 failed visits a week."
2. "Our reader is a small grammar: clauses, cue words, clock times and days, one fact per clause. A correction replaces a time, a denial deletes it."
3. "It reads 22,099 of 22,099 labelled notes, and failed visits fell to zero."

**Q: 100% sounds fitted. What about a note you have not seen?**
The vocabulary was built on 24 labelled worlds. On 26 fresh worlds its first run misread 2 notes of 11,432; on the hold worlds, 1 of 3,539. All three are fixed, so today's 100% includes them. With one more random typo in every note it reads 99.69%. A template with cue words outside the vocabulary would be missed silently; that is the real risk.

**Q: Why not a language model?**
The reader takes 13 microseconds a note, needs no network inside a 4.5-second deadline, and gives the same facts on a replay, which the restart depends on. We could also score it against the world's truth on every note. We did not test a language model as a reader.

---

## Slide 9 — Robust

**Say.**
1. "All 32 of our practice weeks met the delivery minimum; the kit starter met it in none of the 16 we played it on. `[UPDATE: and on 32 fresh weeks that the code had never seen: …]`"
2. "One week moves by more than a point of on-time between two plays of the same policy, so we decided late changes on 24 weeks with several samples each, and moved every knob both ways: none was worth changing."
3. "A restart replays the world's log and our journal through the same code: 12 of 12 rebuilt desks were identical and the week ended at the same margin to the cent; and the test final ran from a cloud machine with every request answered."

**Q: Why should we believe your practice numbers?**
Believe the ones the code never saw. The 8 tune weeks are the ones we fitted on: €17,846 a week. The 16 wide weeks were clean until Saturday afternoon, when we used them to design the surprise days. The 8 hold weeks were only played to confirm, and one of them was opened to study the flu. So the clean evidence is three things: the 32 fresh weeks `[UPDATE]`; the secret weeks of the ranking rounds, where we went from 0.96 to 1.07 to 1.28 times House best in six hours; and the test final, 2nd of 55. The limits: single weeks are noisy (±1.3 points of on-time), and the on-time aim was chosen after looking at unseen weeks.

**Q: What exactly happens when the process dies in the final?**
A shell loop starts it again within a second. The new desk reads the world's whole log and its snapshot, replays them with the journal of what we sent, and then quotes every request that is still open and posts every car that has no gig. While it is down, requests go to the competitor and booked drivers keep driving. The beliefs about the war day, the outage and the flu are rebuilt too, because they are functions of the log. On another machine, without the journal, every order and gig is still recovered, but the dealer side starts again from its prior: that cost 2 to 4% of a week in two early measurements. The test earned its keep: on Saturday it caught the fleet remembering something that the journal did not hold.

---

## Slide 10 — What did not work, what would break it

**Say.**
1. "The most instructive failure: keeping a car out of the app until the morning of its last day, to avoid weak promises. In a randomised test the kept cars were late 11% of the time against 7%: a weak promise is far better than none."
2. "Also not working: a better-calibrated risk model, a finer fee grid, a crisis price after a bad night, and direct offers, 85 accepted of 75,000."
3. "What would break us: a week that is not the rules' week, a flu on a Friday in the capital region, which is still our hardest week at 93 to 96% on time, and a note in words we have not seen."

**Q: What happens in a world unlike the practice ones?**
The dealer side adapts: its world and day parts are learned from the first answers, and it already handled levels from 1.20 to 1.49 times the list price. The driver side adapts less. Its weights come from practice weeks; during a week it learns one intercept, limited to one logit either way, and which day the flu is. The price of the delivery minimum cuts volume once late cars appear, but late cars show two days after we accept them. Our aim is 97% so that a bad week still ends above 90%: over 32 practice weeks the average week ended 0.9 points under the aim and the worst 6.3 points under it, in an earlier version.

**Q: What would you do with one more day?**
Two things we measured and did not finish. A booking made the day before a car's last day is given back 18% of the time, against 5% for one made that morning; holding the car back was the wrong answer, and a better one may exist. And about 30% of the bookings held for the second Monday come back at its midnight in every week; we do not handle that, and those orders are late 3 to 5% of the time. We would also test the model without its two unsupported weights on 24 weeks.

---

## Questions that can come on any slide

**How much of this was written by agents?**
As far as the repository shows, all of the code, the experiments and the first draft of these slides. 124 of the 158 commits carry a `Co-Authored-By: Claude` line; the others are merges and a reader's pass, also made by agents `[UPDATE: recount]`. The work ran from Saturday 02:25 as parallel research streams in separate git branches (dealer side, driver side, notes, direct offers and pairs, the live loop, later the surprise days, the flu, and a reader's pass over the code) with one coordinating agent that merged them. The rules the agents worked under are in `RESEARCH.md`: few parts, each with a reason in one sentence; every baked-in constant regenerated by a script from saved weeks; fit on 8 seeds and never on the hold seeds; for each idea the triple idea, why, effect on the same seeds; failed ideas logged too. `[FILL IN, truthfully: what the two of you did yourselves — the brief, the choice of ideas, the checks you made on Saturday and Sunday, what you changed.]` Do not claim more than that. What you can claim: every number on the slides is reproduced by a command in `OPEN_NUMBERS.md`, and you have run them.

**Did the agents see the hold weeks?**
No constant was fitted on them, but they were not locked away either. They were played about twenty times to confirm changes, and three decisions used what they showed: the on-time aim of 96% (one hold week had ended at 89.7%), dropping a rule for the flu night that helped on tune and wide weeks and did nothing on hold, and confirming the flu sign with three samples a side. The aim of 97% was chosen on tune and wide weeks. One hold week, `halal-09`, was opened on Saturday afternoon to find out why it ended near 90%: that is how the flu night was found, and that week is named as the declared test wherever it is counted. The dealers of the wide worlds were bisected; those of the hold worlds never were.

**Why should a dispatcher in real life care about any of this?**
Four things carry over without the simulator. A fee that rises teaches drivers to wait. A car's cost is mostly its risk of finding no driver in time, not its fee, and that risk depends on who lives near the pickup. The return trip is half of a driver's cost, so a car that shares a gig with one that starts where it ends costs about a sixth less in fees. And a bad day announces itself: in the first hour, drivers give back what they held for it.

---

## Words you may be asked to explain

| Word | Meaning in this system |
|---|---|
| fold | State is computed by applying each event of the world's log, in order, to an empty state. No other memory exists. |
| journal | A file with every batch of actions we sent and the world's answer to each. The world's log does not repeat our quotes, so the journal does. |
| level | The log of the price, as a multiple of the list price, at which a dealer buys half the time. |
| Kalman step | After a yes or no, each part of the level moves in proportion to how uncertain it still is, and becomes a little more certain. |
| logistic | An S-shaped curve from 0 to 1. Here: the chance of a yes falls as the price rises, by about one logit per 10% of price. |
| weigh | Keep a score for each thing that could be true (each possible week, each possible flu day) and raise or lower it with every observation, instead of deciding once. |
| price of the delivery minimum | A cost added to every risky car. It is near zero while we expect far fewer late orders than 3%, and steep near 3%. |
| queue | Our orders that are in the app without a driver. Drivers choose among our own gigs, so a new gig competes with them. |
| tune / hold / wide | Practice seeds 01–08 (fitted on), 09–16 (only to confirm), 17–32 (unseen until Saturday afternoon). |
| stride | In practice only: the clock moves 14 minutes a turn while requests arrive. Another stride is another sample of the same policy. |
| bisect | Halve a price bracket with each replay of the same day, until the dealer's threshold is known. |
| se | Standard error: how far the measured difference could be from the true one by chance. A gain smaller than its se is not shown. |
