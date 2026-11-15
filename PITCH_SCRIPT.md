# Spread pitch — narration (about 3 minutes)

Deck: https://claude.ai/artifact/9noPvECK9TWSh9MYYHkJ8m (press Play top right for full screen, arrow keys to move).
Read at a calm pace; each slide is 20–30 seconds. [FINAL] is filled in on the last slide once the final has ended (~09:40); read the number from the slide.

---

**Slide 1 — One formula. Two probabilities.** (~20 s)
We are Halal Team. Our dispatcher for Spread is one expected-money formula with two probabilities in it: will the dealer buy at our price, and will a driver deliver the car on time at our fee. Everything else in the system exists to fit those two probabilities to the week we are in, and to know which of those fits we can trust.

**Slide 2 — Every quote is one expected-money calculation.** (~30 s)
For every request we choose the price with the highest expected margin: the price minus what the car will cost us, times the chance the dealer buys. What the car costs is the cheapest driver fee once we add the expected refund of a late car, and a shadow price, lambda, for using up our room under the ninety-percent line. Lambda is almost nothing while late cars are rare, and climbs steeply as we get close to the line. Two probabilities, q and r, and one price for lateness. That is the whole desk.

**Slide 3 — Everything else fits q and r.** (~25 s)
The dealer side learns each lane's price level from the answers of the week, and weighs the week's unannounced events: the price-war day and the competitor's outage. The driver side is a logistic model: hours of room, distance, how many of our cars are waiting, drivers living nearby, and even the night when sick drivers give their bookings back. And both are calibrated: the market expects to win 44.4 percent of quotes and wins 45.2; the fleet expects 4.2 percent late and gets 4.5.

**Slide 4 — Every fitted number, audited.** (~30 s)
Then we turned on ourselves. We listed all 129 numbers that were fitted or set by hand, and tested each one on weeks nobody had ever tuned on. Three things did not hold. A learner was quietly patching a model that expected twice as many late cars as really happened. One sign pointed the wrong way. And two parts predicted nothing at all. We cut them. On thirty-two fresh weeks the system earned 766 euros a week more, with the same on-time rate, and won more orders on Mondays.

**Slide 5 — What we kept on purpose.** (~30 s)
We also kept things on purpose. Our town table, sixty numbers that say how much more dealers pay to deliver into Lapland than into Helsinki, earns nothing measurable in the simulator, because every simulated world draws its lanes again. But it predicts dealers better on every unseen week, and in the real Finland those regional price levels are stable. So our rule was: cut what is wrong, not what a simulator happens not to reward.

**Slide 6 — It holds on weeks it has never seen.** (~25 s)
It holds. On ninety-six weeks nobody had tuned on, every single play stayed above the ninety-percent line, the worst at 92.3. If the desk crashes, it restarts and rebuilds the same week to the cent; we killed it mid-week on a cloud machine and it came back by itself. About fifty more ideas we tried overnight did not beat it, and each is logged with its numbers. For the final we took one risk on purpose, a lower on-time target, and we measured that risk on sixty-four weeks before we took it.

**Slide 7 — The final.** (~20 s)
In the final we earned [read the number on the slide]. What we would hand to Bahn Express is not a score but three habits: price what the dealer will pay, never below what the car costs; audit every fitted number on data it has never seen; and keep the numbers the real world has, even when a simulator doesn't reward them. One formula, two probabilities, every number accounted for. Thank you.

---

## How to record and submit (Max)
1. Open the deck, press Play (full screen). Record the screen with your voice: QuickTime → File → New Screen Recording (choose the microphone in Options), or Loom. Move to the next slide as you finish each paragraph.
2. Upload: YouTube (unlisted), Loom or Google Drive (anyone with the link can view). Copy the link.
3. Junction: https://hackjunction.app/participate/45/submissions → "Spread desk: one formula" (draft, already filled: name, punchline, description, challenge Spread, source code). Paste the link into **Video**. Optional: on the deck page, Download → PDF, and upload it under **Presentation**.
4. Check that `[FINAL]` in the description is replaced by the final's result (Damir's Claude fills it in the draft and on the deck by ~09:45; the number is also on spread.bahnexpress.com/team).
5. Press **Submit Final**.
