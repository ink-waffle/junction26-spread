# Direct offers to the right driver at the right moment (agent "offers2")

Sunday 02:15. Branch `research/offers2`; `dispatch/` at its head is main `8ae61c5` unchanged.

## 0. Verdict

**No offer policy pays. Play `8ae61c5` as frozen.** The leaders' €4–9 an order is not in direct offers, as far as our weeks can show.

- **The lead as stated fails on saved data.** A driver who has delivered a gig of ours within 30 km of a car that can be collected now: 210 offers, 43% read, 1 accepted.
- **The best class we can name fails when played.** Offers to experienced drivers who hold a gig of ours ending near the pickup: 2 accepted of 178 a week, margin −183 a week (se 136), on time −0.08 point.
- **halal-161..192 are not played by me.** Nothing reached the bar for a judgement, so no restart test and no Python 3.9 check were needed.

## 1. Why offers are not taken

The answer depends on the driver's day, which we cannot see, and hardly on the fee, the place or the moment.
All numbers are from 91,195 offers of the earlier agent (`offers-x1`: random drivers at random fees of 0.5–1.5 × typical; `offers-x2`: the likeliest drivers at the app's fee), joined with each driver's gigs of ours. `python -m tools.offers2_study answers offers-x1 offers-x2` prints them.

| What the driver does for us when the offer comes | Offers | Read | Accepted |
|---|---|---|---|
| Delivered a gig today within 30 km of the pickup, car can be collected now | 210 | 43% | 0.5% (1) |
| Driving a gig that ends within 30 km, car can be collected now | 639 | 38% | 0.9% (6) |
| Booked for today, ends within 30 km, car can be collected now | 1,150 | 38% | 0.9% (10) |
| Driving or booked for today, ends further away | 4,784 | 44% | 0.9% (41) |
| Delivered today, any place | 1,049 | 45% | 0.1% (1) |
| No gig of ours | 77,297 | 13% | 0.1% (76) |

- **The fee:** 0.1% accepted at up to 0.75 × typical, 0.4% at 0.75–1.05 ×, 0.2% above. A lower fee is refused; a higher fee is refused almost as often.
- **The place and the moment:** near or far, car ready now or later, the share stays between 0% and 1.6%.
- **The same driver, later, in the app:** 77 offers were read and refused by the driver who then booked that same car in the app. 21 of them offered at least the fee the driver then took (one refused 1.5 × and booked at 1.15 × 25 minutes later). `tools.offers2_study bookers` prints this.
- **A driver who has delivered does not take another gig.** In `orch-head-record` (8ae61c5, halal-129..160) a driver books a next gig of ours for the same day 62 times a week before the first one starts, 10 times while driving it, and 0.9 times after delivering it.
- **Opportunities are not scarce.** Of 243 one-car orders a week that have no driver after 30 minutes, 210 have a driver of ours ending a gig within 30 km in time (2,035 driver-car pairs a week). `tools.offers2_study waiting orch-head-record` prints this.
- **After the deadline warning:** 0 of 556 accepted, as the earlier agent found.
- **The three offers a day:** not the limit that binds. The played policy sent 178 offers a week to about 30 drivers and got 2 yes.

## 2. The one thing that moves the answer: experience

| Completed gigs | Offers | Read | Accepted |
|---|---|---|---|
| Up to 50 | 72,880 | 15% | 0.1% |
| 51–150 | 12,939 | 24% | 0.4% |
| 151–300 | 3,712 | 42% | 0.9% |
| Over 300 | 1,664 | 66% | 1.7% |

- **Best class in the saved offers:** over 150 completed gigs, holding a gig of ours for today that ends within 30 km, car ready now: 209 offers, 66% read, 5.3% accepted (11). A week has about 30 such drivers of 899, and 373 such driver-car pairs.
- **That share falls with the gig's age:** for drivers with 150 gigs or more, 3.3% at posting, 2.2% in the first 30 minutes, 1.0% up to 2 hours, 0.4% after. The experienced driver who wants the car takes it in the app in its first minutes.

## 3. What I played

One candidate, `dispatch/offers.py` (commit `5f03aec`, reverted at the head; 62 lines, restart-safe by design: the offers sent are folded from the journal in `Desk.sent`).
An open gig that has been in the app for 30 minutes is offered to at most three drivers with 150 completed gigs or more who hold a gig of ours ending within 30 km of its pickup on a day the car can be collected, at the app's fee, inside the rules' limits, never after the deadline warning.

Tune + wide (24 weeks), stride 14, against `gap-main-s14` (8ae61c5, €15,444, on time 96.8%), `python -m tools.ablations gap-main offers2-vet offers2-vet0`:

| Variant | Margin a week (se) | On time, points (se) | Worst week | Offers a week | Accepted a week | Fee of the accepted |
|---|---|---|---|---|---|---|
| `offers2-vet` (after 30 minutes) | −183 (136) | −0.08 (0.08) | 93.7% | 178 | 2.0 | 1.02 × typical |
| `offers2-vet0` (at posting, `{"offers": {"wait": 0}}`) | −207 (131) | −0.15 (0.09) | 93.5% | 189 | 2.4 | 0.98 × typical |

- **Both are within 1.6 se of zero and on the wrong side**, with 24 of 24 weeks ranked.
- **Accepted share when played: 1.1–1.3%**, under the 5.3% of the saved offers. That number came from 11 yes; the played one from 105.
- **The accepted offers do not pay less.** They are taken at about the typical fee, where the app's average is 0.95 ×.
- **Upper bound:** 2.4 accepted a week, at a saving of even €20 each, is under €50 a week, against a standard error of €130–190.

## 4. Not tried, and why

- **A fee under the app's:** in the saved offers, experienced drivers holding a gig for today took 1 of 132 at up to 0.75 × typical.
- **Offers to every driver seen that day:** the earlier agent's `offers-x2` did that, 75,390 offers for 85 yes and no gain.
- **A judgement on halal-161..192, restart test, Python 3.9 check:** only for a candidate that wins on tune + wide.

## 5. What is on the branch

- `tools/offers2_study.py`: the tables above from saved runs (`answers`, `bookers`, `waiting`, `played`).
- The candidate's commit, for the record, and its revert. `git diff main -- dispatch/` at the head is empty.
- Runs: `runs/offers2-vet-s14`, `runs/offers2-vet0-s14`.
