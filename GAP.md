# GAP: where the leaders' margin comes from, and what we can take of it

Agent "gap", branch `research/gap` from `main` 8ae61c5 (dispatch/ and tools/ unchanged unless section 0 says so). Scripts of this report: scratch only
(`.../scratchpad/gap/*.py`, they read saved runs); every number below names its run folder under `$SPREAD_SHARED/runs/`.

## 0. Verdict

(first verdict due 02:15; see the end of this file for the current state)

## 1. The gap, as far as the leaderboard shows it

- Test final 20:00 (one week): we sold at EUR 106.8 an order and paid 69.7 (65% of revenue); Juhus 102.5 and 60.7 (59%); the top ten 103.0 and 62.7.
- Rounds (same secret weeks, `runs/board-sat21.json`): 18:00 Juhus 2,299 orders at EUR 41.1 of margin each, we 2,081 at 36.2; 21:00 Juhus 2,419 at 43.6, we 2,166 at 36.7.
  Teams with fewer orders than ours earn 42-44 an order (Northbound 2,008 at 42.1; katalyst 1,763 at 43.2; monkey 1,652 at 43.7; one week 287 orders at 58.4):
  they sell dearer and win less. Only Juhus has both more orders and more margin on each.
- We see no other team's actions: everything below is our own weeks.

## 2. Our cost of an order, decomposed (`runs/orch-head-record`: 8ae61c5, halal-129..160, no stride, 431 orders a week)

Revenue EUR 98.2 an order; fees 63.1 (0.947 x the typical fee 66.6); refunds 1.7; fines and releases 0.2; margin 33.2. Price 1.40 x list.

| The fee was chosen | orders a week | at (x typical) | over 0.85 x, EUR a week | late |
|---|---|---|---|---|
| at the win, one car | 165 | 0.85 (154), 1.0 (9) | ~0 | 0.8% |
| two-car gig | 115 | 0.70 (45), 0.85 (70) | -300 | 0.9% |
| six-hour look | 41 | 1.0 (35) | ~550 | 1.1% |
| last-day look | 36 | 1.0-1.5, mean 1.13 | ~725 | 3.3% |
| after it lost its driver | 32 | 0.85-1.5, mean 1.05 | ~400 | 1.7% |
| after the deadline warning | 24 | 1.6 (14), 1.3 once late (10.5) | ~980 | 45% |

- All of the fee above 0.85 x is EUR 2,650 a week = 6.2 an order, and the refunds (1.7 an order) are the last row's. That is the size of the gap to Juhus.
- By hours to the first booking: within 3 h, 307 orders a week at 0.87-0.91 x and a margin of 37-40% of revenue (Juhus: 40.8% on everything);
  after 6 h, 100 orders a week at 1.08-1.42 x.
- No class of request loses money: by length, slack, private ends, premium, electric, hour, town, every class earns 24-38% of its revenue
  (the poorest: slack under 5 h, EUR 14 an order, 56% reach the deadline warning; private pickup EUR 22, 30%).
- 25 orders a week reach the deadline warning without a driver (18.6 never had one, 6.4 lost one); they are 11 of the week's 15 late orders.

## 3. Leads measured and rejected (no play needed)

1. **Price a request cheaper when a car of ours waits that it could share a gig with.** 557 requests a week arrive while such a car waits and we win half,
   but an order won with a partner in reach costs 0.92 x against 0.98 x without: two-car gigs are already 100 a week posted, two thirds booked in a
   median 3 minutes, 115 orders a week delivered in them. The saving is in the queue, not in the fee, and the price already has it.
2. **Hold back cars that are ready days ahead** (drivers know their next day): only 45 such orders a week, booked in a median 1.1 h at 0.92 x.
3. **Dealer trust.** One dealer (D01) sends 32% of all requests and two send 45%, the same dealers in every week (size from week to week r = 0.97).
   Trust already adds EUR 3,684 a week to revenue (mean count 8.6 at the quote; D01 at 0.8 / 10.7 / 20.7 / 20.6 / 22.2 by day). Late orders' halvings
   cost EUR 327 a week. Every large dealer at 25 from Tuesday morning would add at most ~EUR 1,700 a week before what it costs to win Monday's cars;
   an order's worth in trust in the quote was tried by `simple` (-479, se 283).

## 4. Played

(filled as runs finish)

All runs here: 24 weeks (tune halal-01..08 + wide halal-17..32), strides 14 and 13 where two samples are said, against `gap-main` = 8ae61c5 on the same
weeks and strides (EUR 15,352 a week, 96.8% on time, 440 orders, worst sample 93.5%); `python -m tools.ablations gap-main gap-<name> ...`.

| Tried (one change each) | samples | margin (se) | on time (se) | orders | verdict |
|---|---|---|---|---|---|
| **The price knows a partner** (`gap-back`; patch in scratch `backhaul.patch`): a request whose car would share a two-car gig with a car of ours without a driver costs 0.66 x the gig's fee share + 0.34 x its cost alone | 24x2 | -146 (184) | -0.47 (0.16) | +27 | rejected: it buys orders with on-time like every other lever |
| **A pair's driver may start later** (`gap-later`): the plan of a two-car gig starts where the wait on the way is least (35 more orders a week pass the pairs' rule) | 24x1 | -90 (205) | -0.30 (0.09) | -2 | rejected |
| Pairs up to 6 h of driving (`gap-drive6`) | 24x1 | +103 (195) | -0.46 (0.11) | +5 | no: two-car gigs of 5-6 h are booked 36% at 0.70 x and 56% at 0.85 x (3-5 h: 57% / 70%) |

More leads measured on saved weeks and dropped:

4. **The on-time model by class** (`python -m tools.fleet_fit --calibrate orch-head-record`): it says 4.2% late where 4.5% are; only lanes over 400 km are off
   (7.8% said, 10.9% late, 53 orders a week = 1.6 late orders a week more than it thinks). Worth a quarter point of on-time at most.
5. **The market's chance of a yes at our own quotes** (scratch `mcal.py`, 30,517 quotes replayed): said 44.4%, dealers 45.2%, within 3 points in every
   bin of chance, day, trust count and price. Nothing to take.
6. **Round trips** (a two-car gig that ends where it starts frees the driver's trip home): 5 orders a week have such a partner over 5 h. Too few.
7. **Do drivers learn to wait on us?** A one-car gig at 0.85 x posted 09-15 with a day of slack is booked within the hour 82% on Monday, 68 / 67 / 68% Tuesday
   to Thursday, 35% on Friday (weekend work): one step after Monday, no slide through the week.
8. **What we price out**: 288 requests a week get a quote over 1.8 x list (81 declined): trade-ins (97% of them), private delivery (68%), private pickup (60%),
   over 600 km (49%), under 40 km (41%), pickups with two drivers or fewer near (47%). All are the on-time model's refusals.
9. **The whole pack, not only Juhus** (`runs/board-sun00.json`, the closed 21:00 round, 57 ranked teams): places 3-14 all earn EUR 39.7-42.1 an order on
   2,008-2,352 orders at 96.4-98.1% on time; we earn 36.7 on 2,166 at 96.8%. Across teams margin goes with orders (r = 0.80). MathNet1 moves 2,629 orders
   at 96.9% (36.8 an order): at that volume our own frontier (below) is at 92.6% on time. So others get cars booked on time that we do not.
10. **The competitor answers what we win** (HANDBOOK: each morning it lowers its prices for a dealer where we won most, raises them where we won few).
    Seen (scratch `answer.py`, 487 dealer-days of 8 requests or more): after a day on which we won under 30% of a dealer's requests the dealer says yes
    4 points more often than the market expects, after 30-50% 1-3 points less, over 50% as expected. A few points of yes = about 2% of price: too small to steer.
11. **A driver hears of each order once** (HANDBOOK). The cars of a two-car gig that found no driver (64 a week) then go alone without a notification:
    the first car waits a median 1.0 h and is paid 0.98 x, the second 6.7 h and 1.02 x, a car that sat before 14 h and 1.01-1.12 x with 10-12% late
    (a new car posted alone: 0.2 h, 0.87 x, 0.8% late). A failed pair costs about EUR 11 a car; `gap-hold0` / `gap-hold15` below test not holding new cars.

### The on-time target and the fee floor: our frontier (24 weeks, stride 14; the target also at stride 13)

| on-time target | margin | on time (worst week) | weeks under 93.5% / 92% | orders | fee x typical | margin an order |
|---|---|---|---|---|---|---|
| 98.5% | 14,050 | 97.9% (96.1) | 0 / 0 | 380 | 0.930 | 37.0 |
| 98% | 14,400 | 97.3% (94.9) | 0 / 0 | 410 | 0.938 | 35.1 |
| **97.5% (main)** | 15,444 | 96.8% (94.5) | 0 / 0 | 444 | 0.939 | 34.8 |
| 97% | 15,526 | 96.0% (94.2) | 0 / 0 | 469 | 0.946 | 33.1 |
| 96% | 15,774 | 94.9% (92.6) | 8 / 0 | 499 | 0.953 | 31.6 |
| 95% | 15,637 | 93.7% (90.3; 89.8 at stride 13) | 7 / 5 | 528 | 0.964 | 29.6 |
| 94% | 15,065 | 92.6% (89.0) | 14 / 8 | 546 | 0.975 | 27.6 |

Two samples a side: 97% +190, 96.5% +135, 96% +290, 95.5% +130, 95% +150, 94% -245 against main. **Below 97.5% the margin is flat and the tail arrives;
above it a half point costs EUR 1,000.** The leaders' weeks at 93% are not where their money comes from, for a system like ours.
A lower fee floor does lower what we pay (floor 0.80: 0.908 x typical, on time 96.5%, worst 94.5%; floor 0.75: 0.897 x, 96.0%) but the model wins
13-17 fewer orders, and the margin is -200 / -826.

Single knobs, stride 14, one sample (se about 200): two-car fee 0.65 x -388, 0.75 x -120; board pairs 0.80 x -47, 0.75 x +167; patience 30 min +19,
120 min -83; idle 2 h -101; hold 45 min -88; urgent fee 1.3 x -152, 2.0 x -536; late fee 1.0 x +120, 1.6 x -628; look at 4 h -707, 9 h -409;
fee grid with half steps -282; late price 200 +28 (-0.4 point), 450 -151 (+0.2).
