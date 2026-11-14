# Research brief (shared by every agent working on this repo)

Read `OVERVIEW.md` (Russian summary) or `kit/RULES.md` + `kit/HANDBOOK.md` first if you do not know the game. This file holds what we measured, how to run experiments, and the conventions. `NIGHT_LOG.md` is the jury-facing log of ideas and effects.

## Goal

Final: Sunday 08:00, level 8, live clock. We need a top-10 margin among ~130 teams **while ≥ 90% of won orders are on time** (not ranked otherwise), then a jury judges the system: elegant (few parts, each with a reason), clear, creative, robust (many unseen weeks, restarts, slow network). Leaderboard, Saturday 00:00 round, sum of 5 level-8 weeks: best team €80k (€16k/week), House best €72k, 10th €58.5k (€11.7k/week). Teams improve fast; aim for ≥ €16k/week, ≥ 94% on time on every seed.

## The system (keep it this small)

| Module | Job | One-line reason |
|---|---|---|
| `dispatch/books.py` | State = fold over the event log. Decides nothing. | Restart = replay the log. |
| `dispatch/market.py` | `Market.quote(request)` → price per option. | Price = what the dealer will pay, never below what the car costs us. |
| `dispatch/fleet.py` | `Fleet.cost(request, option)` (expected cost or None = do not win) and `Fleet.plan(order, legs)` (gigs: stops, audience, fee schedule). | The driver side: which cars we can move, and at what fee. |
| `dispatch/notes.py` | `read(note, arrived_at)` → `NoteFacts`. | The world acts on the note whether we read it or not. |
| `dispatch/desk.py` | Loop: observe event → `reconcile()` issues the actions that make the world match the plan; `rejoin()` after a restart. | One control loop, same path after a restart. |
| `dispatch/run.py` | Practice loop (advance) and CLI. Live final loop: to be built. | |
| `tools/harness.py`, `tools/study.py` | Experiments: N seeds in parallel; saved runs → one pandas table. | |

`Policy` (in `desk.py`) = `MarketPolicy` + `FleetPolicy` dataclasses; every tunable lives there, so an experiment is a JSON override.

## How to run experiments

```sh
export SPREAD_SHARED=/Users/ink_waffle/OverengineeringLife/Junction2026/spread   # shared runs/ and .slots/ for all worktrees
set -a; . $SPREAD_SHARED/.env; set +a                                            # never print SPREAD_KEY
PY=$SPREAD_SHARED/.venv/bin/python
$PY -m tools.harness --tag <yourname>-<what> --seeds quick --policy '{"fleet": {"fee": 1.1}, "market": {"price": 1.5}}'
$PY -m tools.study <tag>            # or: from tools.study import table; t = table("<tag>")
```

- Seeds: `quick` = halal-01..04, `tune` = halal-01..08 (tune on these), `hold` = halal-09..16 (**never tune on them**; confirm a finished change there), `wide` = halal-17..32. The world is deterministic per seed and actions, so one run per (version, seed) is enough; compare versions on the same seeds.
- **Use `--stride 14` while exploring** (`$PY -m tools.harness --tag x --seeds tune --stride 14`): the clock moves 14 minutes a turn while requests arrive instead of waking on every event, so a week costs ~350 requests instead of ~1,500 and ~30 s instead of 60–110 s. The server's rate limit is per team (150–240 requests a second at busy hours, shared by every run), so this is what makes experiments faster, not more parallel runs. Answers come up to 14 minutes later than in the final (a dealer waits 15), which moves single seeds by €1–3k but not the mean (main default on tune: €15,317 / worst week 93.9% with the stride, €14,937 / 94.5% without). Confirm a candidate without the stride before it is adopted.
- A level 8 week takes ~90–120 s from this laptop. The team has **8 practice slots shared by every agent**; the harness queues through `.slots/` file locks, so just run it, but prefer `--seeds quick` while iterating and do not start more than one harness at a time per agent. Never call `client.create` outside the harness, never delete worlds by hand (`--clean` deletes only orphans), never use `--board`, never join a final.
- Every run is saved to `$SPREAD_SHARED/runs/<tag>/<seed>.json.gz`: score, policy, our quotes, all events, gigs, the reveal (truth of won orders, views), roster. Prefix your tags with your agent name. `runs/log.jsonl` has one line per harness call.
- A margin only counts when on-time ≥ 90% on **every** seed. Report: mean margin, min and mean on-time, ranked x/8, on `tune` and, for a final candidate, on `hold`.
- `fork` (same future, two decisions) is available via the kit client for surgical A/B tests, but a fork takes a slot: go through `tools.harness.Slot`.

## Conventions

- Work in your own git worktree/branch; commit small, with a message that states the measured effect; push your branch (`git push origin <branch>`). Do not rewrite pushed history. Never commit `.env`, `.venv`, `runs/`, `reveal-*`. Do not edit `kit/`, `OVERVIEW.md`, `challenge.md`.
- Stay inside your module(s). If you need a new field in the books or a new call between modules, add the smallest thing and say so in your report.
- Code is judged: few parts, each with a reason you can state in one sentence. No pile of special cases: if a rule needs three exceptions, find the principle. Comments and docstrings: one line at most, only where the code cannot explain itself. Use the challenge's words (dealer, request, order, gig, fee, typical fee, deadline). Standard library only inside `dispatch/` (numpy/pandas are fine in `tools/`).
- Anything learned offline and baked in (a table, a coefficient) must come from a script in `tools/` that regenerates it from saved runs, and must be validated on `hold` seeds.
- For each idea keep the jury's triple: **the idea** (what the system does, when), **why** (what you saw), **the effect** (margin and on-time with and without, same seeds). Ideas that failed are worth a line too.

## What we know so far (level 8)

Sources: kit starter reveal on `spread-1`; `explore1` = 8 tune seeds with every quote at a random U(1.0, 1.9) × list on a random subset of options and every order posted at a random flat fee of {0.7, 0.85, 1.0, 1.15, 1.3, 1.5} × typical, one raise to 1.6 × at the deadline warning.

**Money.** Typical fee ≈ 0.9 × list price (0.6 × under 40 km). At list price there is no margin: margin = how far above list we sell minus how far above typical we pay. A world has ~1,035 requests, ~750–830 drivers, 40 dealers; ~41% of requests carry a note; 10% private pickup, 5.6% private delivery, 4.7% premium, 16% electric, 1.4% trade-in.

**Drivers learn to wait, fast.** Starter (fee rises 10%/h to 1.5 ×, then to 2.5 × after the warning): Monday 186 bookings, median 7 min after posting at 1.0 × typical. From Tuesday the median booked fee is exactly the cap, 1.5 ×, and from Friday 2.5 ×. → We post **one flat fee per gig**.

**A car booked before its deadline warning is on time; a car that is not, is late.** `explore1`: booked before `deadline_close` → 96% on time; not → 25%. The whole fleet problem is: get a booking before the warning.

**Supply curve** (share booked before the warning, flat fee as a multiple of typical): 0.70 → 39%, 0.85 → 61%, 1.00 → 81%, 1.15 → 91%, 1.30 → 88%, 1.50 → 91%. Above ~1.15 × more money buys nothing; what is left is structural:
- slack (hours from win to `lastPickupAt`): < 5 h → ≤ 58% even at 1.5 ×; 5–8 h → ~77%; ≥ 8 h → 90–100%;
- private pickup: 59–73% at ≥ 1.15 ×; trade-in: 45–73%; premium (needs one of the ~7% experienced drivers): 71–84%;
- under 40 km needs ≥ 1.15 × (typical is tiny there); over 400 km tops out at ~83%;
- Friday is worst (requests won late on Friday); booking within 30 min falls from 80% on Monday to 41% on Friday at 1.15 ×.
- ~10–12% of bookings are dropped, independent of the fee.
- ~440–520 distinct drivers view gigs each day, but only ~100 book (1.5 gigs each): ~150 bookings/day is what a world gave at 1.0–1.6 × typical.

**Win curve.** P(win) is logistic in log(price/list) with slope ≈ −10 (10% dearer ≈ −1 logit). Median winning multiple m50 (quoting one random option): 1.20–1.49 by world; by world × day 1.01–1.78 (price-war day ≈ −20%; outage region-day up). Fitting per world-day intercepts lifts log-likelihood from −0.505 to −0.418; adding pickup and delivery place effects to −0.378 (delivery in Kajaani/Kemi/Mikkeli/Ylivieska/Kokkola/Rovaniemi tolerates +17–23%; Vantaa/Helsinki −3%); world × dealer effects to −0.369. Quoting only a later option when a faster one exists costs ≈ 12% of price at equal win chance (dealers value speed). So: the day's level must be learned online within the first hour of each day; the place effects can be a prior learned offline.

**Dealers, measured exactly** (`tools/probe.py`: Monday of 24 seeds bisected, 5,516 options known to 0.5%; `runs/bisect/`). A request has one threshold per option, and the dealer buys the offered option with the largest (threshold − price) in euros: right in 98.1% of 2,291 probed two-option menus, never "none". The log threshold of a request's fastest option spreads 0.176 over worlds, 0.128 inside a world's Monday, 0.084 inside one world and lane, and no less with dealer, hour or batch added: a logistic (slope 21.7 around the lane's level), not a step. That last 8.4% is the request's own factor; nothing in the request predicts it (typical fee, car, private ends, note, hours, charge, batch, neighbours: |r| < 0.1). A lane's level is mostly new in each world (other worlds predict it with r = 0.39 through the delivery place, nothing more); dealers differ by under 5%. A slower option's threshold is the faster one's minus a sum of euros that is one number per dealer and world: same day over next day median €14.5 (quartiles 9.5–19.9, sd inside a dealer €0.39), next day over within 3 days €6.1 (3.8–9.9, €0.45); new in each world. Exact replay of Monday on tune (the fleet's cost of 10:00): our learner with every option at one margin €2,032; an oracle of each lane's level €2,065; an oracle of every threshold €3,7xx. So price precision is spent; what the dealer side can still give is the faster option, sold wherever the dealer's euros for speed exceed what speed really costs the fleet.

**The surprise days, measured exactly** (`tools/probe_week.py`: 24 of our own weeks, 8 tune and 16 wide, each day bisected on forks of the played week at midnight, 24,127 thresholds within 2%; `python -m tools.surprises exact | find | money | fleet`). The outage raises the threshold of the cars that *leave* its region by 0.20–0.33 log, mean 0.260 (the rule: 30% = 0.262), from 08:00 to 18:00, and nothing for cars that arrive there. In 13 of 24 weeks it fell on the capital region (83–131 requests that day), in 6 it reached 4–15 requests, in 5 too few to see. The war day lies 0.14–0.31 under the week's calm days, mean 0.23 (the rule: 0.223, plus the day's own factor); calm days stray by 0.04, so the day part's 0.125 was the events. Before the market weighed the events its level followed a war after a median 18 requests (09:45) and an outage after 67 or never: a median 14% under in the region and 6% over elsewhere. Now (idea 13) it is within 5% after 4 requests on a war day and 7 on an outage day. In an exact replay at the fleet's cost a war day costs €1,650 against the same day without it, an outage gives €1,100, and a market that is told both at 08:00 earns €300 a week more than the old one: ours takes €202 of that. Orders won on a war day earn €22 each against €36 on a calm day (59 a day against 86); in the outage region we win 65% of the requests at 1.65 × list and €51 an order. The bulk order (31–39 cars from one yard in one batch; we win 2–31, median 15) is on time and paid like the week's other orders (93.6% against 94.4%, €37 against €36 an order). The flu day does not show in views or in who books; it shows in who reads a direct offer that pays nothing, sent at the same minute of each day (`tools/census.py`): the drivers who read on every other working day read today too, 97–100 in 100, but 28% were silent on halal-01's Wednesday and 15% on halal-05's Friday, the same nights on which most bookings are given back after midnight (`tools/flu_study.py`). In the other six tune weeks no working day is above 5%: there the flu falls on a day without requests, or does not reach the drivers who read.

**Unconstrained price optimum** given the curve and fee ≈ typical: ≈ 0.93 × m50, winning ~65% ≈ 670 orders, which is far more than drivers take at a sane fee. So we are capacity-bound: the price should be (cost + what the driver's time is worth elsewhere), i.e. maximise (p − cost − λ)·P(win | p) with λ the shadow price of a booking.

**Baselines** (8 tune seeds): kit starter −€72.6k on `spread-1` (45% on time). Flat 1.0 × fee, 1.3 × list on everything: −€8.0k, 57.7% on time (halal-01). See `NIGHT_LOG.md` for the current best.
