# Speaker notes — the 3-minute talk for `PRESENTATION.md`

For a speaker who did not write the code. Part 1 is what to say, slide by slide, in about three minutes. Part 2 is the five hardest questions, with short honest answers. Part 3 is backup: more questions by slide, and the words you may be asked to explain.

Before you present:
- The jury's own rule: "If an agent wrote your slides, read every line and cut each one that you cannot explain yourself." Do that. Every claim names its source, and `OPEN_NUMBERS.md` has the command that prints it.
- Fill the placeholders first. Do not say a number that still carries `[FINAL]` or `[SUNDAY]`.
- One sentence carries the talk: **"Our dispatcher knows what it does not know, and proves it on weeks it has never seen."** Say it on slide 1 and again on slide 10, word for word. If time runs short, cut slide 6 to its first sentence; never cut slide 7, it is the story.
- Use their words: dealer, request, option, gig, fee, typical fee, list price, deadline, deadline warning, delivery minimum, direct offer.
- State of these notes: Sunday 02:50, commit `8ae61c5`, ideas 1–15 of `NIGHT_LOG.md`. This commit plays the final.

---

# Part 1 — the talk (about 3 minutes, about 480 words)

**Slide 1 (25 s).** "We are Halal Team. Our dispatcher knows what it does not know, and proves it on weeks it has never seen. Three numbers. It says a car is 4.2% likely to be late; 4.5% are. It was once wrong by a factor of two, found out, and fixing that earned €766 a week. And on 96 weeks it had never seen, 160 plays out of 160 met the delivery minimum. In the final it made `[FINAL]`."

**Slide 2 (18 s).** "First, we measured the world. A practice day replays to the cent, so each replay halved a bracket around every dealer's price, down to half a percent. That gave us the dealer's exact rule, and the part nobody can know: each request has its own 8% that nothing predicts."

**Slide 3 (13 s).** "So a quote is a bet with known odds: price minus cost, times the chance of a yes, learned from every answer, and every option at one margin. It says 44% yes; 45% of dealers say yes."

**Slide 4 (15 s).** "Drivers learn that fees rise, so a gig of ours has one fee. A car booked before its deadline warning is on time 96% of the time, otherwise 25%. So a car costs its fee plus its risk of being late."

**Slide 5 (17 s).** "Nobody announces the price war, the outage or the flu, so we weigh instead of guessing. The dealer side weighs 600 possible weeks and names the war day in 24 of 24. The driver side sees the flu at midnight, when sick drivers give back their bookings."

**Slide 6 (12 s).** "Where the world is plain, no model. Two cars share a gig, because the trip home is half a driver's cost. And a small grammar reads 22,099 of 22,099 notes."

**Slide 7 (28 s).** "Then we measured ourselves. On Saturday night an agent with no stake counted all 129 numbers and took out each part on weeks nobody had played. Our on-time model said 10% late; 4.8% were. A learner had hidden that, patching it slowly every week, so every Monday looked twice as risky. We deleted four parts and set the level once. On 32 fresh weeks: €766 a week more, at the same on-time."

**Slide 8 (18 s).** "This is our graveyard: about fifty ideas played after the freeze. Chains of cars, direct offers, trade-ins, other targets. None earned more without paying for it in on-time. The leader moves more cars per driver; none of our levers does that, and we say so."

**Slide 9 (16 s).** "It holds where it has never been: 160 of 160 unseen plays ranked, the worst at 92.3%. A restart replays the week to the cent, and a desk we killed in the middle of a week on the cloud machine rejoined by itself."

**Slide 10 (14 s).** "So, once more: our dispatcher knows what it does not know, and proves it on weeks it has never seen. Its one real risk, a world much harder than ours, we chose with open eyes. Thank you."

---

# Part 2 — the five hardest questions

**1. Why are you not first?**
Because the leader moves more cars per driver, and we did not find how. Read from the leaderboards: over 15 ranking runs it wins 11% more orders than the top-10 median and €3.2 more on each, at the same on-time (97.2% against 97.3%), and its volume does not depend on how many drivers a world has (`runs/reports/detective.md`). Tonight we tried what could produce that, gigs of three and four cars, long shared gigs, direct offers to drivers who end nearby, trade-ins, and none earned more than its noise without losing on-time (slide 8). Across 164 variants of ours, every lever that adds orders loses margin on each order. So the gap is outside our design, not one knob away. We kept the system we can prove on every week we have. Our places: 10th of 67 in the Saturday 18:00 round; in the Sunday 00:00 round 1.33 × House best and 2nd of 18 at 00:06 `[SUNDAY: closing place]`.

**2. Isn't this overfitted?**
The headline number would be, so we never quote it: €17,846 a week on the 8 weeks we fitted on is 8 rich worlds. We quote the weeks no number of the frozen system was chosen on: 96 weeks, 160 plays, all ranked, mean €15,327 a week, worst 92.3%; and the record, 32 fresh weeks played once after the freeze, €14,313. The audit itself is our answer: decided on weeks 65–96, confirmed once on 97–128, recorded once on 129–160. The bisection taught us how dealers decide; no bisected price is stored, and the hold worlds were never bisected.

**3. You praise calibration, but on Saturday morning a better-calibrated model lost €2,266 a week. Which is it?**
Both are true, and the second explains the first. That refit was still not calibrated: it said 9.0% late where 6.0% were. It accepted more risk on Monday, the late cars showed two days later, and the price of the delivery minimum then cut the rest of the week (€14,973 → €12,707 on tune). The old model's pessimism was a hidden safety margin. The audit made it explicit: the level set where unseen weeks put it (+0.88, the same on three disjoint sets of weeks), and the margin moved into the aim, from 97% to 97.5%. A right level with a stated margin beat a wrong level with a hidden one: +€766 a week at the same on-time.

**4. What if the final's week is harder than anything you have seen?**
That is the one risk we chose, and we know its size. Since the audit, the driver side learns only one thing during a week, which day is the flu's. If drivers are much scarcer, it is braked only by the price of the delivery minimum, which sees late cars two days after we accept them. With a model one logit too easy, on time falls 2.8 points and one week ends at 90.5%; the learner we deleted would have held the fall to 1.0 point (`runs/reports/simple.md`). We kept the measured constant because it earns more on every unseen set we have. The aim of 97.5% is there so that a bad week still ends above 90%: on the 32 fresh weeks the worst ended 4.7 points under the aim, at 92.8%.

**5. What would you do with a real Bahn Express fleet?**
Keep the method, change how we measure. A real day cannot be replayed, so bisection becomes what we did first anyway: prices and fees randomised inside the same days (our `explore1` weeks; the meet-the-drivers test, randomised by order number). Four findings should carry over and are cheap to check. A fee that rises teaches drivers to wait. A car's cost is mostly its risk of finding no driver in time, and that depends on who lives near the pickup. The trip home is half a driver's cost, so pair a car with one that starts where it ends. And a bad day shows itself in its first hour, when drivers give back what they held for it. Every week we would check the calibration, what the system said against what happened, because a dispatcher whose odds are right can be steered with one number, the on-time aim. We have not seen real data, so these are hypotheses for it, not results.

---

# Part 3 — backup

## More questions, by slide

### Slide 1

**Q: Which single idea is worth the most?**
Measured one at a time on the same 8 practice weeks: learning the dealer's price level, +€3,543 a week (€6,824 → €10,367). Pricing a car as fee plus risk, +€2,789, and it took the ranked weeks from 5 of 8 to 8 of 8. Dropping the extra reserve, +€2,431. The second look at a gig that sits, +€1,903. They were measured at different stages, so they do not add up exactly. On weeks nobody had played, taking a part out costs most for the harm a new gig does to the cars that wait (−€2,967 a week), then the pickup-side signs (−€1,702), two-car gigs (−€1,444) and the six-hour look (−€1,394). The last idea, the audit, added +€766 a week on 32 fresh weeks. Appendix B of the deck has the whole path.

**Q: How big is it?**
1,900 lines of Python in eleven modules, standard library only, and 123 numbers fitted or set by hand: the audit counted 129 and deleted six. Each module has one stated reason; the table is in `README.md`, and `REVIEW.md` is our own reading of where a reader still stumbles.

### Slide 2

**Q: Is that not fitting to the simulator? What of it reaches the final?**
We used it to learn how dealers decide, not to store prices. What we shipped is structure: the menu at one margin, the size of the price war and of the outage as the rules state them (20% and 30%), and the decision not to ship lane or dealer tables. No price from a bisected world is used anywhere. The hold seeds were never bisected: `runs/bisect/` holds seeds 01–08 and 17–32 only.

**Q: An oracle earns €3,723 and you earn €2,103. Why is no money left?**
That oracle knows each request's own factor, 8.2% (sd) around its lane's level. We tested the request's typical fee, car, note, opening hours and hour of the day against it: nothing predicts it. The organisers' handbook also names "a small factor for the request alone". The part that can be known is the level, and there we are at the ceiling.

### Slide 3

**Q: Why the same margin on every option?**
Because of how a dealer chooses (slide 2): among the options it would buy, it takes the one with the largest threshold minus price, in euros. If every option carries the same margin over its own cost, we earn the same whichever it takes, and it takes the faster one exactly when speed is worth more to it than it costs us. Today the faster option costs a median €11 more in our quotes, and dealers value it at a median €14.5.

**Q: The competitor answers your wins. Do you model that?**
No, on evidence. We measured it: a dealer's level falls about 4% per unit of the share of its Monday requests that we won, so about 2% at the biggest dealer after we took 30% of its Monday. Trust is larger: about +1% per order delivered on time. The day part of the level absorbs the competitor's answer. (A dealer part was in the level until the audit: on 64 unseen weeks it foretold no answer, so it went.)

### Slide 4

**Q: You do change the fee. Is that not a rising fee?**
It is a compromise, and we measured both sides of it. With a fee that never moved, 26 orders a week sat for a median 70 hours and half of them arrived late. One look after six hours earned €1,903 a week (€14,935 → €16,838): 88 more orders, and the worst week no worse. Drivers do learn from it (71 / 67 / 59 / 58 / 33% booked within 15 minutes, Monday to Friday, against 73 / 71 / 65 / 67 / 48%). More looks, daily or six-hourly, or steps up to twice the typical fee, did not earn more. A raise sends no notification, so after a gig's first minutes a higher fee reaches few drivers.

**Q: Is the starter comparison on the same weeks?**
Yes, since Saturday afternoon. On our 8 tune weeks the starter makes −€63,232 a week at 52.1% on time and ranks in none; ideas 1–14 made €17,846 at 96.9%. On the 8 hold weeks: −€68,908 against €14,806, and the frozen system €15,488. That compares whole systems. The evidence for the fee alone is our own test of a fee that rises once: weeks ranked 5 of 8 → 3 of 8 on the same weeks.

**Q: How do you know the chance of a late car? Is it calibrated?**
It is a logistic model with 15 weights, fitted on our own practice weeks by `tools/fleet_fit.py`. Until Saturday night it was not: on 64 weeks the fit never saw it said 10% late where 4.8% were, and a learner inside each week corrected that, slowly, so every Monday was priced as twice as risky as Wednesday. The audit measured the missing intercept on three disjoint sets of weeks (+0.86, +0.90, +0.87), set it once at +0.88, and deleted the learner. On its own play the model now says 4.3% late where 4.0% are. On the 32 fresh weeks of the frozen system it says 4.2% where 4.5% are; only lanes over 400 km are off (7.8% said, 10.9% late; `python -m tools.fleet_fit --calibrate orch-head-record`). One weight, `known`, came back from the unseen weeks with the opposite sign and is gone; `waited` is still open (slide 10).

**Q: Why 97.5%, why €300, why the fourth power?**
The €300 and the fourth power are set by hand; the aim is measured. With a model whose level is right, caution is cheap: from 97% to 97.5% the frozen system gives up about €280 a week for half a point to 0.8 point of on-time, where the old system paid €546 for a point. At 97.5% it earns more than the old one and is on time more often on both untouched sets (+€679 and +0.52 point on 32 weeks, two samples a side). The price of the minimum is €300 × (expected late share ÷ 2.5%)⁴: about €19 at half the allowance and €300 at it. Without that steep curve a flat €300 a late order ends one week at 90.3%, and a flat €100 leaves 24 of 32 weeks unranked.

### Slide 5

**Q: You were told the rules of the events. What is creative here?**
The rules say that the events exist, not when or where. Two things are ours. First, treating the week as one of 600 possible weeks and letting every answer weigh all of them, instead of letting a "day" number chase each one: a war and an ordinary cheap day then differ in what they ask of the day, and we keep one belief for each case. Second, finding that the flu shows itself at all. We looked in views and bookings and found nothing. We ran a census with direct offers that pay nothing: in 7 of 20 weeks it found a day when 15–35% of the regular readers were silent, but that was the night that takes our bookings in only 2 of them. Then we saw that on one night a week 22–57% of the bookings held for that day come back in its first hour, against 2.7% on other nights. That count needs no extra action.

**Q: What if the final's week has no war, or two?**
Then we lose a little. In the replay a week without a war still gains €66 over the old dealer side; a week without an outage loses €2; a week with neither loses €118. If no war has been heard by Friday morning, the dealer side starts Friday about 99% sure that today is the day, and corrects itself from the answers. A flu on Monday cannot be seen in advance: Monday has no night before it with bookings to give back.

### Slide 6

**Q: Why 0.70 and 0.85, 30 km and 5 hours?**
From randomised tests inside the same worlds. Pairs with at most 4 hours of driving at 0.70 × were booked 85% of the time, in a median 4 minutes; their fees came to 0.89 × typical against 1.21 × for the same cars as two gigs. Pairs over 6 hours were booked 29% of the time. When one of the two cars already sits in the app, 0.70 × delivered 46% as a pair and 0.85 × delivered 76%, at the same cost in the end. 30 km is the radius in which the app notifies a driver of a new gig.

**Q: Why not pair more?**
We tried: a wait of 60 minutes and pairs up to 6 hours gave +€284 a week (se 304) for −0.57 point of on-time on 24 weeks. That buys volume the way a lower on-time aim does, so we left it. The pairs as they are earn €1,444 a week on weeks nobody had played (the audit took them out to see).

**Q: 100% sounds fitted. What about a note you have not seen?**
The vocabulary was built on 24 labelled worlds. On 26 fresh worlds its first run misread 2 notes of 11,432; on the hold worlds, 1 of 3,539. All three are fixed, so today's 100% includes them. With one more random typo in every note it reads 99.69%. A template with cue words outside the vocabulary would be missed silently; that is the real risk.

**Q: Why not a language model?**
The reader takes 13 microseconds a note, needs no network inside a 4.5-second deadline, and gives the same facts on a replay, which the restart depends on. We could also score it against the world's truth on every note. We did not test a language model as a reader.

### Slide 7

**Q: Is that not just tuning on more weeks?**
It is the opposite of a search. The +0.88 is a measurement, the free intercept of the model on weeks it never saw, and it comes out the same on three disjoint sets (+0.86, +0.90, +0.87); it was chosen before its neighbours were played. The deletions were decided on `halal-65..96`, confirmed once on `halal-97..128`, and then the frozen system was played once on `halal-129..160`, weeks no system of ours had touched: €14,313 against €13,547 for the old one, paired per week, se €221, 24 of 32 weeks up. The aim went from 97% to 97.5% on `halal-65..96` and was confirmed on `97..128`.

**Q: Why not the even smaller system the other agent proposed?**
It deleted 64 numbers, including the 60 of the place table, and earned the same as the old system (−€76 a week, se 184). Ours earns more on every untouched set and can be explained in one line: the level is where the unseen weeks put it. That agent's findings are on the slide: the slow Monday is mostly the world (dealers who do not trust us yet pay about 12% less on Monday), and the deleted learner was insurance against a much harder world (a model one logit too easy costs 2.8 points of on-time without it, 1.0 with it). We took the constant and accept that risk.

### Slide 9

**Q: Why should we believe your practice numbers?**
Believe the ones the code never saw. The 8 tune weeks are the ones we fitted on: €17,846 a week with ideas 1–14, which is 8 rich worlds. The 16 wide weeks were clean until Saturday afternoon, when we used them to design the surprise days. The 8 hold weeks were only played to confirm, and one of them was opened to study the flu. So the clean evidence is three things: the 32 fresh weeks `halal-129..160`, played once after the freeze, €14,313 a week, all ranked; the secret weeks of the ranking rounds, where we went from 0.96 to 1.07 to 1.28 to 1.29 times House best in nine hours; and the test finals, 2nd of 55 joined on Thursday and 18th of 75 over a full week. The limits: single weeks are noisy (±1.3 points of on-time), and the on-time aim was chosen after looking at unseen weeks.

**Q: What exactly happens when the process dies in the final?**
A shell loop starts it again within a second. The new desk reads the world's whole log and its snapshot, replays them with the journal of what we sent, and then quotes every request that is still open and posts every car that has no gig. While it is down, requests go to the competitor and booked drivers keep driving. The beliefs about the war day, the outage and the flu are rebuilt too, because they are functions of the log. On another machine, without the journal, every order and gig is still recovered, but the dealer side starts again from its prior: that cost 2 to 4% of a week in two early measurements. The test earned its keep: on Saturday it caught the fleet remembering something that the journal did not hold. The audit then deleted that memory: the fleet's state is now the books alone.

### Slide 10

**Q: What happens in a world unlike the practice ones?**
The dealer side adapts: its world and day parts are learned from the first answers, and it already handled levels from 1.20 to 1.49 times the list price. The driver side adapts less. Its weights come from practice weeks and its level from 64 weeks it never saw; during a week it learns only which day the flu is. The price of the delivery minimum cuts volume once late cars appear, but late cars show two days after we accept them. That is the risk we chose: in a world where our model is one logit too easy, on time falls 2.8 points (1.0 with the learner we deleted). Our aim is 97.5% so that a bad week still ends above 90%: on the 32 fresh weeks the mean week ended 1.2 points under the aim and the worst 4.7 points under it, at 92.8%.

**Q: What would you do with one more day?**
Two things we measured and did not finish. A booking made the day before a car's last day is given back 18% of the time, against 5% for one made that morning; holding the car back was the wrong answer, and a better one may exist. And about 30% of the bookings held for the second Monday come back at its midnight in every week; we do not handle that, and those orders are late 3 to 5% of the time. We would also play the frozen system without its three open weights (`waited`, `short`, `trade_in`).

---

### Questions that can come on any slide

**How much of this was written by agents?**
As far as the repository shows, all of the code, the experiments and the first draft of these slides. 152 of the 186 commits on `main` (Saturday 23:05) carry a `Co-Authored-By: Claude` line; the 34 others are merges, two work-in-progress commits and a reader's pass, also made by agents. The work ran from Saturday 02:25 as parallel research streams in separate git branches (dealer side, driver side, notes, direct offers and pairs, the live loop, later the surprise days, the flu, a reader's pass over the code, and at night a skeptic's audit and a rival simplification) with one coordinating agent that merged them. The rules the agents worked under are in `RESEARCH.md`: few parts, each with a reason in one sentence; every baked-in constant regenerated by a script from saved weeks; fit on 8 seeds and never on the hold seeds; for each idea the triple idea, why, effect on the same seeds; failed ideas logged too. `[FILL IN, truthfully: what the two of you did yourselves — the brief, the choice of ideas, the checks you made on Saturday and Sunday, what you changed.]` Do not claim more than that. What you can claim: every number on the slides is reproduced by a command in `OPEN_NUMBERS.md`, and you have run them.

**Did the agents see the hold weeks?**
No constant was fitted on them, but they were not locked away either. They were played about twenty times to confirm changes, and three decisions used what they showed: the on-time aim of 96% (one hold week had ended at 89.7%), dropping a rule for the flu night that helped on tune and wide weeks and did nothing on hold, and confirming the flu sign with three samples a side. The aim of 97% was chosen on tune and wide weeks. One hold week, `halal-09`, was opened on Saturday afternoon to find out why it ended near 90%: that is how the flu night was found, and that week is named as the declared test wherever it is counted. The dealers of the wide worlds were bisected; those of the hold worlds never were. The audit of Saturday night played the hold weeks four times a side to confirm, and decided on weeks that nobody had played at all (`halal-65..96`).

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
| untouched / fresh | Seeds 65–128: first played by the audit (65–96 to decide, 97–128 to confirm). Seeds 33–64 and 129–160: each played once, after a freeze, as the record of a frozen system. |
| intercept | The constant of the on-time model: how likely a car is on time before any of its own signs. Set once, where 64 unseen weeks put it. |
| stride | In practice only: the clock moves 14 minutes a turn while requests arrive. Another stride is another sample of the same policy. |
| bisect | Halve a price bracket with each replay of the same day, until the dealer's threshold is known. |
| se | Standard error: how far the measured difference could be from the true one by chance. A gain smaller than its se is not shown. |
