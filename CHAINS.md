# CHAINS: do several cars per driver trip close the leaders' gap?

Agent "chains", branch `research/chains` from `main` 8ae61c5. `dispatch/pairs.py` here carries three test knobs (`cars`, `ahead`, `rate`), all off by
default: the default policy plays 8ae61c5 to the cent (halal-01, stride 14: EUR 14,789 both). Scripts of the measurements: scratch only, they read saved runs.

## 0. Verdict

**No. Play `main` 8ae61c5.** (Final, Sunday 01:50; section 3 has every run. No candidate for the 03:00 round; halal-161..192 not played, nothing reached the bar; no restart test, since the default policy is main.)

- Longer chains, longer holds, longer two-car gigs and a fee by the planned hour were each played against main on the same 24 weeks
  (tune + wide, stride 14; the best also at stride 13). None is ahead of main by more than its standard error, and every one that moves
  more cars per driver pays for it in on-time (-0.2 to -0.4 point). Nothing reached the bar for a judgement on halal-161..192.
- Why the hypothesis fails in our weeks: drivers are paid by the hour of their whole trip, whatever the gig holds. One car: EUR 12.7 per
  road hour (the drive, 2.6 h, plus the driver's own trips to the pickup and home, 3.2 h); two cars: 13.6; three: 14.8. A shared gig saves
  the driver's own trips only when the cars are short and close, and those are already paired: 34% of the cars under 300 km ride shared.
- Long lanes (the detective's lead): only 2% of our cars over 300 km ride shared, and when we let them (gigs up to 12 h) 22% do,
  but a shared gig of 7 to 12 h is booked 25-45% of the time and its cars end at 1.02-1.10 x typical with 6-7% late (alone: 1.01 x, 6.9%).
  Only gigs that end near their start book well at every length (70-80%), and there are 2 a week over 5 h.

## 1. What the saved weeks say (`runs/orch-head-record`: 8ae61c5, halal-129..160, no stride, 431 orders a week)

| gig | gigs a week | cars | fee x typical | fee a car | drive, h | empty between cars, h | driver to pickup, h | home, h | fee per road hour |
|---|---|---|---|---|---|---|---|---|---|
| one car | 311.5 | 311.5 | 0.991 | 73.3 | 2.55 | 0 | 1.62 | 1.60 | 12.7 |
| two cars | 57.4 | 114.9 | 0.795 | 37.1 | 2.71 | 0.46 | 1.07 | 1.23 | 13.6 |

(The driver's trips are road minutes from the driver's home town; they are an upper bound when the driver comes from another gig.)

- **What limits the two-car gigs**: two cars only; the second pickup within 30 km of the first delivery; at most 5 h of planned driving; a new car
  waits 30 minutes for a partner (or joins a car that sits in the app); at most 1 h of waiting at stops for a driver who starts 3 h from now.
- **How much more could share a trip**: with every car of a pickup day matched at once (same reach and 5 h), 194 links a week = about 265 cars
  sharing a trip against 115 now, 45 chains a week of three cars or more; with 12 h, 239 links. That is with the whole day known in advance.
- **A posted two-car gig is booked 68% of the time**, and what decides it is the fee per planned hour of driving (logit +0.17 per euro, se 0.02;
  under EUR 20: 44%, 24-26: 88% at 0.70 x), Friday (44%), a pickup today (54%), two cars from one yard (46%). At equal fee per hour the 0.70 x and
  0.85 x gigs book alike.
- The cars of a two-car gig cost 0.915 x typical in the end (booked: 0.85 x; not booked and sent alone: 1.05 x, 5.5% late) against 0.995 x for
  new cars posted alone; no class of two-car gig costs more than that.
- Drivers chain by themselves: 61 driver-days a week hold two of our gigs, 5 hold three; the second gig pays 0.93 x against 0.97 x for the first.
- The bulk order (30+ cars from one yard): 14 won a week at 0.967 x typical and 5.3% late, like every other car. Cars from one yard do not chain:
  the driver has to come back to the yard.
- The typical fee is EUR 18.4 + 21.9 per hour of driving. One-car gigs at 0.85 x: the long ones (over 4 h, EUR 22 an hour) are booked 90% within
  six hours, the short ones (EUR 35-42 an hour) 66%: a short car is mostly the driver's own trips, which is what a shared gig saves.

Longer shared gigs do what a lower on-time target does (GAP.md: half a point of on-time is worth about EUR 1,000 above 97.5%, nothing below):
about EUR +200 a week and 10-25 more orders for 0.3-0.4 point of on-time. At equal on-time they lose.

## 2. What was built (one knob each, in `dispatch/pairs.py`, all off by default)

- `cars`: the most cars in one gig; a pair takes one more car at either end while one fits.
- `ahead`: the minutes a new car waits for a partner when it is ready on a later day (today's cars: `hold`, 30).
- `rate`: a gig of several cars pays this many cents per planned hour of driving instead of 0.70 / 0.85 x the typical fees.
- `drive` (was there): the most road minutes a shared gig may plan.

## 3. Played (24 weeks tune + wide, against `gap-main` = 8ae61c5 on the same weeks and strides; `python -m tools.ablations gap-main chains-<name>`)

| Tried | samples | margin (se) | on time, points (se) | orders | worst sample | verdict |
|---|---|---|---|---|---|---|
| up to 3 cars a gig (`cars3`) | 24x1 | -55 (203) | -0.21 (0.11) | -3 | 93.9% | no: 10 three-car gigs a week, 126 cars shared against 122 |
| up to 4 cars (`cars4`) | 24x1 | -126 (212) | -0.17 (0.14) | -4 | 94.5% | no |
| later-day cars wait 2 h (`ahead120`) | 24x1 | -0 (183) | -0.06 (0.10) | +17 | 94.8% | no: 140 cars shared at 0.77 x, but the cars left alone cost 1.00 x (0.98) |
| later-day cars wait 6 h (`ahead360`) | 24x1 | -588 (245) | -0.43 (0.18) | +32 | 94.8% | no: 165 shared at 0.75 x, alone 1.03 x |
| EUR 20 per planned hour (`rate2000`) | 24x1 | -383 (233) | +0.02 (0.16) | -13 | 94.5% | no |
| EUR 22 (`rate2200`) | 24x1 | +30 (289) | -0.24 (0.14) | -6 | 94.6% | no |
| EUR 24 (`rate2400`) | 24x1 | +75 (210) | -0.31 (0.11) | +2 | 94.2% | no |
| gigs to 12 h at EUR 22 an hour (`d12r22`) | 24x2 | +198 (204) | -0.38 (0.11) | +24 | 93.7% | no: orders bought with on-time |
| gigs to 12 h at EUR 24 an hour (`d12r24`) | 24x2 | -206 (218) | -0.42 (0.12) | +26 | 93.7% | no |
| gigs to 8 h, the multiples (`d8`) | 24x2 | +178 (211) | -0.31 (0.12) | +13 | 92.8% | no: one sample under 93.5% |
| gigs to 7 h, the multiples (`d7`) | 24x2 | +71 (216) | -0.39 (0.10) | +6 | 93.8% | no |
| gigs to 7 h at EUR 22 an hour (`d7r22`) | 24x1 | +57 (259) | -0.23 (0.15) | +3 | 94.6% | no |

Shared gigs by planned hours in `chains-d12r22-s14` (EUR 22 an hour): to 3 h 57% booked, cars at 0.91 x in the end; 3-5 h 68%, 0.90 x; 5-7 h 59%, 0.95 x,
3.5% late; 7-9 h 45%, 1.02 x, 6.2% late; 9-12 h 25%, 1.10 x, 7.3% late. Gigs over 5 h that end within 60 km of their start: 2.2 a week, 79% booked, 0.94 x.

## 4. Not tried, for a successor

- At equal on-time every variant above is below main's own frontier (the on-time target buys the same orders cheaper), so a chain lever that works
  has to book better, not only hold more cars: the booking of a shared gig follows its fee per planned hour, Friday, a pickup today and one yard (section 1).
- The handbook says a driver learns "the booked fee over the first fee viewed for the order". A car that sat alone and is then booked in a two-car
  gig may teach its viewers a rise of 1.7 x. Not measured.
- Shared gigs over 5 h only when they end near their start (79% booked): 2 a week, too few to judge in a night.
