# A simpler system that starts the week at full speed (Saturday 20:30–22:40, branch `research/simple`)

The question: is the slow Monday ours, which numbers can go or be learned in the week, and what does that cost on weeks nobody has played?
Everything below prints again:

```sh
python -m tools.weekdays final-fresh skeptic-base-s14          # orders won by weekday, saved runs
python -m tools.start_study final-fresh                        # the price of a late order hour by hour, Monday against the other days
python -m tools.trust_study final-fresh                        # dealers' trust through the week
python -m tools.replicates simple-main-s14,simple-main-s13 simple-D-s14,simple-D-s13   # the candidate against the frozen main, halal-97..128
```

## 0. Verdict

*(written last; see the end of `runs/progress.md` for the line that starts with `simple DONE`)*

## 1. Where Monday's orders go (saved runs, no new plays)

| Weeks | Mon | Tue | Wed | Thu | Fri | Mon / Wed |
|---|---|---|---|---|---|---|
| frozen main, halal-33..64, no stride (`final-fresh`) | 72.5 | 81.2 | 84.4 | 90.0 | 77.3 | 0.86 |
| frozen main, halal-65..96, stride 14 / 13 (`skeptic-base`) | 72.5 / 71.3 | 89.1 | 89.8 / 88.7 | 90.4 | 75.9 | 0.81 / 0.80 |
| frozen main, tune + wide, stride 14 / 13 (`orch-base`) | 75.0 / 76.2 | | 90.3 / 90.3 | | | 0.83 / 0.84 |
| the 20:00 test final (live clock, one week) | 49 | 99 | 73 | 109 | 94 | 0.67 |

- **The slow Monday is in practice weeks too, as −15 to −20%, not as a half.** Monday is the week's lowest day in 34 of 64 unseen weeks, and its spread is wide: in 11 of 64 weeks Monday is at 0.55 × the week's median day or under. The test final's 49 is an ordinary bad Monday.
- **Most of it is the world.** A dealer accepts 1% more for each order we delivered to it on time, up to 25 (the rules of level 8). The dealers' level fitted per weekday on the 32 fresh weeks (slope held): × 1.33 of the list price on Monday, × 1.38 on Tuesday, × 1.50 from Wednesday; net of trust it is the same on all three days. Monday's dealers pay 12% less, so fewer requests clear our cost: we win 32% of Monday's requests at 1.30 × list and 42–45% of Wednesday's at 1.45–1.49 ×.
- **A part is ours: the price of a late order in the week's first hours.** `late_price` divides the late orders the books expect by 20 + the orders so far. On Monday at 10:00 the week has 13 orders, 6 of them without a driver yet, each counted as a fifth of a late order: the price of a late order is €2,356 in the mean and €1,500 or more in 53% of weeks (Tuesday to Friday: €465–789, 1–11% of hours), and a quarter of that hour's quotes are above 2.9 × list (Tuesday: 1.64 ×). In the test final the desk sold nothing between 12:00 and 15:00 on Monday (0 of 75 requests; median cheapest quote €200–242 against €80–100 before and after) with 13 orders in the books and 3 without a driver. Without `known` (which makes the model 1.15 logits more pessimistic on the week's first bookings) the same replay gives €1,246 and 31% at 10:00, and the rest of Monday as any other day (`tools.start_study`).
- **What it is worth:** a flat price (`skeptic-flat300`) wins 80 orders on Monday, no `known` 78, against 72.5: 6–8 orders, about €200–300 a week. The larger sum is in the trust itself (section 2).

## 2. Trust is bought on Monday and Tuesday, and the desk does not count it

`python -m tools.trust_study final-fresh` (frozen main, 32 fresh weeks):

- Requests are concentrated: about 40 dealers a week, the largest sends 30% of all requests, the five largest 62%.
- A request from a dealer at 25 is won 51.5% of the time at 1.57 × list; one from a dealer under 5 orders 34.5% at 1.31 ×. 57% of the week's requests arrive at trust under 5, 13% at 25.
- The largest dealer ends Monday at 2.8 counted orders, Tuesday at 16, and is at 25 by Wednesday night in 59% of weeks; the second and third largest are at 14 and 12 on Wednesday night and never reach 25.

The quote maximises this order's margin only. An order on time to a dealer under 25 also raises what that dealer pays on every later request of the week: for the largest dealer on Monday morning that is worth more than the order's margin. *(the rule that counts it, and its measurement: section 4)*

## 3. What was deleted, and what each deletion costs

*(follows)*

## 4. The candidates against the frozen main on halal-97..128

*(follows)*
