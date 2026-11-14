# Night log — Halal Team, Spread

Level 8 throughout. "tune" = our seeds halal-01..08, "hold" = halal-09..16 (never tuned on). Margin is per week; a week counts only when ≥ 90% of its orders are on time.

## Status

| When | Best version | tune: margin / min on-time / ranked | hold | Trying now |
|---|---|---|---|---|
| Sat 03:10 | `main-m1` = base1 + online price-level learner (idea 4) + live final loop | €10,367 / 89.1% / 7 of 8 | — | Fleet cost model with a capacity price (to lift the worst week over 90%), note reader (100% of facts on 24 labelled weeks), two-car gigs (fees 0.89 × vs 1.21 × typical on short pairs) |
| Sat 02:35 | `base1` (flat 1.15 × fee, 1.45 × list, ≥ 8 h slack, no private pickup / trade-in / premium) | €6,824 / 83.9% / 5 of 8 | — | Five parallel research streams: notes reader, win-curve pricing, fleet cost model, direct offers, live final loop |

## Ideas

### 1. One flat fee per gig (no rising schedule)
- **The idea.** Every gig is posted at a single fee and stays there. The fee changes at most once, at the deadline warning.
- **Why.** In the kit starter's week (fee +10%/h to 1.5 × typical, then to 2.5 ×), Monday's 186 bookings came a median 7 minutes after posting at 1.0 × typical. From Tuesday the median booked fee was exactly the cap, 1.5 ×, and from Friday 2.5 ×: drivers had learned that our fees rise, and waited. The starter paid €118.6k in fees on €71.3k revenue.
- **The effect.** Starter on `spread-1`: −€72,613, 45.5% on time. Same quotes with a flat 1.0 × fee (halal-01): fees €52k on 591 orders (fee × 1.15 of typical on average instead of × 1.67).

### 2. Sell above list, because typical fee ≈ 0.9 × list
- **The idea.** Quote a multiple of the list price well above 1.
- **Why.** Typical fee / list price is 0.90 on average (0.6 under 40 km). At list price a delivered car earns nothing. Dealers' win curve (8 weeks of random quotes, `explore1`): 85% at 1.05 ×, 50% at 1.3–1.4 ×, 10% at 1.8 ×.
- **The effect.** 1.45 × list with a flat 1.15 × fee and idea 3: €6,824/week on tune, against −€72,613 for the starter on its own seed and −€8,001 for 1.3 × list without selection (halal-01).

### 3. Only win cars that will be booked before the deadline warning
- **The idea.** A request is quoted only when the time from the dealer's answer to the last possible pickup is at least 8 hours; otherwise we decline (quote 4 × list).
- **Why.** `explore1`: a car booked before its deadline warning is on time 96% of the time; one that is not, 25%. At a flat 1.15–1.5 × typical, 90–100% of cars with ≥ 8 h of slack are booked before the warning, 77% with 5–8 h, ≤ 58% under 5 h.
- **The effect.** Tune seeds, same price (1.45 × list) and fee (flat 1.15 ×): with the rule €6,824/week, on-time 91.6% mean (83.9% worst), 5 of 8 weeks ranked; without it €6,640/week, 82.8% mean (68.3% worst), 3 of 8 ranked. (Rule here also refuses private pickups, trade-ins and premium cars.)

## Did not work
- Flat 1.0 × typical on everything we could win at 1.3 × list (halal-01): −€8,001, 57.7% on time. We won 591 cars; drivers booked ~150 a day.

## Ranking rounds and test finals
- none played yet
