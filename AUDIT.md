# Loss audit of main (Saturday 10:40)

Per week on the eight tune seeds, level 8. Runs: `main-m4-r0.3` (main as merged, reserve 0.3), `main-m4-r0.15`, `main-m4-r0.0` (all eight seeds each), and 26 older runs on the same seeds for what dealers and drivers did with the same requests at other prices and fees. `python -m tools.audit main-m4-r0.0` prints the tables and the pair and requote estimates; the checks marked "one-off" below were scripts outside the repo.

## Bottom line

| | orders | margin | on time (worst seed) | price × list | fee × typical | margin per order |
|---|---|---|---|---|---|---|
| reserve 0.3 | 207 | €10,280 | 96.8% (96.2%) | 1.57 | 0.94 | €49.7 |
| reserve 0.15 | 272 | €11,881 | 96.5% (95.5%) | 1.51 | 0.95 | €43.7 |
| reserve 0 | 342 | €12,711 | 95.5% (94.4%) | 1.45 | 0.98 | €37.2 |

There is no single hidden leak. On the orders we win almost nothing is lost (refunds €295–640, every other line under €40). The one big lever, volume, is measured and nearly spent: the last 70 orders bought by the reserve brought €12 each. What separates €12.7k from €15–17k at the same 340 orders is €7–12 per order: cheaper driving (two cars in one gig), a dearer option, and the 26 orders a week that reach the deadline warning without a driver.

## Levers, ranked

| # | Lever | € per week | Kind | Evidence |
|---|---|---|---|---|
| 1 | Reserve 0.3 → 0 | **+2,430** | measured, 8 seeds | €10,280 → €11,881 → €12,711 with 207 → 272 → 342 orders; late 3.3% → 3.5% → 4.5% (worst seed 94.4% on time); warned share flat at 7.2–7.6%. The extra 66 orders brought €24 each, the next 70 only €12: do not expect more from this knob. |
| 2 | Two cars in one gig | **+1,100 to +1,800** (30 min hold), up to +3,000 (2 h hold) | estimate from main's own won orders and the offers agent's fee measurement | Of 316 plain cars won per week at reserve 0, 114 (36%) have a partner whose pickup is within 30 road km of their delivery, inside 12 h of driving and both windows, if a car waits 30 min before it is posted; 182 (58%) with 2 h. Their typical fees are €7,128 (€11,821) a week. offers-x3 measured such pairs at 0.89 × typical all-in against 1.21 × as two gigs, 94% on time; main pays 0.96 × for singles, so 0.15–0.25 × typical is saved on each paired car. Not in main. |
| 3 | Sell the faster option | **up to +1,090**; realistic +300 to +600 | estimate | 201 of 342 orders are won on a slower option than the dealer's fastest. For 134 of them the faster option had 8 h or more in which the car could really be collected (73 with 12 h or more). A dealer pays 8.6% more per faster option (`prior.SPEED`): €1,094 (€606) a week on the same wins. Same-day orders are late 7% against 4%. We always price one option; pricing two lets the dealer choose. |
| 4 | The warned tail | **+300 to +800**, and 8 fewer late orders a week | estimate | 26 orders a week (7.6%) reach the warning with no driver, after a median 70 h in the app (87% a day or more, 94% never booked). The fee then goes from 0.85 to 1.6 × with 3 h left: 52% arrive late. They earn −€4 each, the others +€41: €1,344 of fees above the floor and €592 of refunds. 12–24 h before the warning 37 orders are still open and 60–65% of them end warned: one step of 0.3 × typical then costs €880–900 and reaches 22–24 of the 26. Warned share: 14% over 200 km, 3% under; 25% of private pickups; 19% of private deliveries. |
| 5 | Steadier quotes | **+300 to +800** | estimate | Our quotes sit with a spread of 0.215 (log) around the day's level; 0.143 inside the same world, day, lane band, option, room and class. Dealers' own thresholds spread 0.135, and earlier requests of the week explain 18% of that. At equal wins a quote at a constant distance from the day's level sells dearer: on the dearest quarter of days, safe cars, ×1.63 at 85 wins against our ×1.57 at 78 (+€252 on 157 requests). The floor moves with the book (fee grid, shadow price, backlog), not with the dealer. |
| 6 | Premium, private delivery, trade-in | **+300 to +600** | estimate | Premium: 44 requests, 6.5 won, 3.6% late, €43 each; we quote ×1.83 against a threshold of ×1.34. Private delivery: 33 requests, 4.4 won, €32 each, 3% late but 20% warned. Trade-in: 22 requests, 3.5 won, €84 each, 21% late. Requoting premium cars with 8 h of room 5% above the day's level wins 13 instead of 6 (+€105). Private pickups (78 requests, 12.6 won, €31 each, 25% warned) are rightly dear. |
| 7 | Windows on the refund ladder (`fleet.ladder`, coded, off) | **0 to +700** | one run pair, 7 seeds | fleet-v3 €9,953 → fleet-v3-ladder €10,612 on the same seeds; late share (4.7%) and the refund of a late order (26–27% of its price) did not move, so the gain is not yet explained. Seed noise is ±€300–500. |
| 8 | Trust | **+200 to +400** | estimate | Trust already pays €3,390 a week (9.2% of revenue; 0% on Monday, 16% on Friday). Three dealers send 51% of all requests (one sends 300 a week) and reach a count of 20–24. Dealers ranked 4–21 send 420 requests and reach 2–9. Late orders halve a count 5.1 times a week: about €210. 22% of dealers never buy from us (47 requests a week). |
| 9 | Long hauls over 400 km | **−400 to +750**: test first | estimate, sensitive | 194 requests, 45 won (23%, against 40–43% for 100–400 km), €78 each, the best margin per booking. We quote ×1.79 against a threshold of ×1.34. Requoting the safe ones at the day's level wins 62 instead of 40: +€735 if they book at 1.0 × typical with 2.4% refunds as today, −€375 at 1.1 × and 3.5%. 14% of orders over 200 km are warned today. |
| 10 | Dear days | +250 | estimate | On the dearest quarter of days (level ×1.57 to ×1.64) we already win 50% of the safe requests at 4% under the level. A uniform 5% under wins 102 instead of 80: +€260. |

Levers 2–10 overlap little except 5 with 9 and 10. If half of each lands, main at reserve 0 reaches about €15k.

## 1. Where money leaks on orders we won (reserve 0)

Account per week: revenue €36,681, driver fees −€23,245, late refunds −€640, undelivered −€17, release fees −€33, waiting −€22, fines −€12, failed visits €0. Cancelled orders cost €53 (fees and release of drivers already booked).

Late orders: 15.4 of 342 (4.5%).

| Cause | orders | € |
|---|---|---|
| no driver before the warning | 10.0 | −456 |
| private slot missed | 1.5 | −68 |
| collected in time by the map, slow drive (snow: 0.1) | 1.6 | −41 |
| redirected by the dealer | 0.5 | −26 |
| late by the note's deadline or real hours | 0.6 | −24 |
| booked in time, then dropped | 0.6 | −23 |
| booked in time, collected too late | 0.5 | −20 |

Fees. 234 of 342 orders are booked from a gig that stays at 0.85 × typical, the lowest fee the fleet allows: 1% of them late, 38% booked within 5 minutes. That floor is right, not a leak: the very cars we booked at 0.85 without a warning were also won in the random-fee week (460 orders); there, at 0.70 ×, 52% of them found a driver before the warning, at 0.85 × 76%, at 1.00 × 99%. So a lower fee loses a quarter of the easiest cars, and a heavier week needs 1.0 ×: +€11 on every order, as much as the marginal order earns. 38 bookings a week are dropped; 6% of those orders end late.

Failed visits: 2 in 24 weeks of main (10.6 a week before the note reader). Both were a booked driver who announced (`driver_late`) a pickup after the site's real closing time and came anyway: the desk can release such a driver free of charge when the announced minute is outside `notes.collect_spans`. Waiting (€22): a driver who reaches a delivery site after its real closing time on a day before the deadline, mostly on Friday evening. Fines: one in 24 weeks, an electric car that the dealer redirected to a route over 200 km after a driver had booked it without a charging stop.

## 2. What we leave on requests we lost or declined

For every request the audit fits the multiple of the list price at which its dealer buys half the time ("threshold"), from the answers to the same request in 29 runs. Held-out check on `main-m4-r0.3`: log-likelihood −0.207 against −0.375 for the day's level alone; predicted wins within 10% of actual. Thresholds: median ×1.31; ×1.22 at a dealer with no trust, ×1.55 at a count of 10–25. The tables below are the tool's output with its default pool (every saved run on these seeds) and move by a few requests with the pool.

Our quote against the request's own threshold (reserve 0; reserve 0.3 in brackets):

| quote | requests | won |
|---|---|---|
| 5% or more below | 261 (152) | 249 (147) |
| within 5% | 123 (84) | 77 (49) |
| 5–15% above | 135 (114) | 17 (9) |
| 15–30% above | 202 (192) | 3 (3) |
| 30% or more above | 241 (378) | 0 |
| declined (4 × list) | 76 (117) | 0 |

At reserve 0 we still do not compete for 519 of 1,037 requests (quoted 15% or more above the threshold, or declined). By class (reserve 0):

| class | requests | won | our quote / threshold | margin per order | late |
|---|---|---|---|---|---|
| under 40 km | 107 | 20 (18%) | 1.46 / 1.25 | €14 | 1% |
| 40–100 km | 204 | 61 (30%) | 1.51 / 1.32 | €18 | 1% |
| 100–200 km | 299 | 119 (40%) | 1.45 / 1.33 | €30 | 2% |
| 200–400 km | 233 | 101 (43%) | 1.46 / 1.36 | €43 | 8% |
| over 400 km | 194 | 45 (23%) | 1.79 / 1.34 | €78 | 9% |
| premium | 44 | 6.5 (15%) | 1.83 / 1.34 | €43 | 4% |
| private delivery | 33 | 4.4 (13%) | 1.84 / 1.39 | €32 | 3% |
| private pickup | 78 | 12.6 (16%) | 1.78 / 1.38 | €31 | 7% |
| trade-in | 22 | 3.5 (16%) | 1.92 / 1.42 | €84 | 21% |
| quoted same day | 167 | 43 (26%) | 1.57 / 1.35 | €37 | 7% |
| quoted next day | 674 | 207 (31%) | 1.55 / 1.33 | €39 | 4% |
| quoted within 3 days | 195 | 95 (48%) | 1.39 / 1.29 | €32 | 4% |

Short lanes earn €14–18 a booking and long ones €43–78: a booking is worth three to five times more on a long lane, and a week that must grow should grow there (lever 9) before it adds short lanes. Cars with under 5 h in which they can really be collected (139 requests on the option we priced) are quoted at ×1.80 against a threshold of ×1.38 and 14% are won; of those 21% are warned and 11% late. That caution is right: in the random-fee weeks such cars were booked before the warning at most 58% of the time at any fee.

By weekday the won share is even (30–35%); Monday earns least per order (€31, no trust yet). By hour nothing stands out (26–39% won from 9 to 18). By dealer: the biggest sends 300 requests and gives 114 orders and €4,800; the next two 228 requests, 96 orders, €3,555; dealers ranked 22 and below 89 requests, 22 orders.

A static replay of pricing rules on the same request stream (truth = thresholds, cost = what each lane band really cost) puts a pricer that knows each day's level from its first request at €21k for the same 342 orders. Do not read that as reachable: the three concrete requotes above (dear days, long hauls, premium) each give a tenth of what the replay suggests, because our scattered quotes already win where thresholds are high.

## 3. Timing of capacity (reserve 0)

| day | requests | won | bookings | drivers who looked / who booked (per world) | orders waiting for a first driver, 9–18 h |
|---|---|---|---|---|---|
| Mon | 237 | 76 | 60 | 415 / 41 | 16 |
| Tue | 204 | 64 | 67 | 465 / 49 | 23 |
| Wed | 191 | 68 | 70 | 468 / 51 | 25 |
| Thu | 226 | 77 | 81 | 477 / 59 | 26 |
| Fri | 179 | 61 | 54 | 529 / 46 | 33 |
| Sat | – | – | 23 | 349 / 21 | 20 |
| Mon+ | – | – | 26 | 215 / 23 | 7 |

Gigs posted Monday to Thursday: 41–43% booked within 5 minutes, 64% within 30, 75% within 3 h, at every hour from 9 to 18 (34–45% within 5 minutes). Friday: 28%, 39%, 49%, median wait 5.3 h, because most drivers know only their next working day; Friday's orders are still on time (3.8% late) since they are due on Monday.

Drivers do not run out at 342 orders: one in ten of those who open our gigs books one on a given day, against about 100 bookers a day in the 460-order weeks. They are least used on Monday, when we also earn least per order and trust is zero. They did run out at 460 orders (the same cars at 0.85 ×: 76% booked before the warning instead of 100%).

## How the numbers were made, and what is weak

- Leaks, classes and timing are counts from the saved runs: exact.
- Thresholds pool runs in which the competitor and trust had moved differently; quotes far from any price ever tried on a request are extrapolated. Lever sizes that rest on them (5, 6, 9, 10) are estimates.
- One-off checks, not in the tool: the held-out score of the thresholds, the same cars in the random-fee week (`runs/explore1.pkl`), the static replay, the 18% that earlier requests explain, the trust lost to halvings, the ladder pair on common seeds, and the two failed visits and the fine traced event by event.
- Lever 2 uses a simple pairing rule on orders already won and the offers agent's fee measurement on base1; pairs longer than 6 h of driving booked badly there.
- Everything is tune seeds. None of it is confirmed on hold.
