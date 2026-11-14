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
