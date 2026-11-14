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

**Unconstrained price optimum** given the curve and fee ≈ typical: ≈ 0.93 × m50, winning ~65% ≈ 670 orders, which is far more than drivers take at a sane fee. So we are capacity-bound: the price should be (cost + what the driver's time is worth elsewhere), i.e. maximise (p − cost − λ)·P(win | p) with λ the shadow price of a booking.

**Baselines** (8 tune seeds): kit starter −€72.6k on `spread-1` (45% on time). Flat 1.0 × fee, 1.3 × list on everything: −€8.0k, 57.7% on time (halal-01). See `NIGHT_LOG.md` for the current best.
