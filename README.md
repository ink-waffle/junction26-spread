# Spread dispatcher — Halal Team (Junction 2026, Bahn Express)

For one simulated week the system quotes prices to car dealers against a competitor it never sees, and posts each car it wins as a gig for freelance drivers at a fee it chooses.
The driver side estimates the chance that a car arrives on time, and from it what the car costs us: its fee plus the risk of a late car.
The dealer side learns from every yes and no what each dealer pays, and quotes the price with the highest expected margin over that cost.
All state is a fold over the world's events and the actions the world acknowledged, so a restart replays the log and continues as the same desk.
One loop plays a practice week and the final; only the transport differs.

Result, level 8: `[FINAL: € … margin, … % on time, place … of …]`. In practice €16,838 a week on the 8 weeks we fitted on (worst week 94.7% on time) and €13,057 a week on 18 weeks we did not (worst week 91.5%); the kit starter makes −€72,613 at 45.5% on time on its own seed `[UPDATE: see OPEN_NUMBERS.md]`.

## The modules

`dispatch/` is 1,862 lines of Python in ten modules. It uses the standard library and the kit's client, nothing else.

| Module | Job | Why it exists |
|---|---|---|
| `books.py` | Everything the desk knows, as a fold over the world's events. It decides nothing. | A restart is then a replay of the log. |
| `market.py` | `quote(request)`: a price for each option. `learn(...)`: one Kalman step per yes or no, which also weighs on which day the price war is and on which day and where the outage. | The competitor's price is never shown. A dealer's yes and no are the only signal. |
| `fleet.py` | `cost(request, option)`: what the car costs us. `plan(order, legs)`: the gig, its stops, its one fee. | A car booked before its deadline warning is on time 96% of the time, otherwise 25%. So a car's cost is its fee plus its risk. |
| `pairs.py` | Puts two cars in one gig when the second starts where the first ends. Keeps no state. | The typical fee of a trade-in is half of two single typical fees: the trip home is half a driver's cost. |
| `notes.py` | `read(note, arrived_at)`: the facts of a dealer's note. Then when the car can really be collected, and the stop windows a gig needs. | The world acts on a note whether we read it or not. |
| `desk.py` | One turn: fold the events, move the clock, issue the actions that make the world match the plan. `sent` reads the world's answers and writes the journal. `rejoin` rebuilds a desk mid-week. | One control loop, and the same path after a restart. |
| `run.py` | The practice loop (we advance the clock), the live loop of the final (the clock runs by itself), the command line. | The two loops differ only in transport; both call `Desk.step`. |
| `names.py` | The server's address when the system's resolver has none. | On Saturday the laptop's resolver refused the server's name for hours while the server answered. |
| `prior.py` | What dealers pay as far as it holds in every world: slope, trust, speed, a level per place. Generated, not edited. | The first requests of a week must be priced before the week has taught anything. |
| `atlas.py` | Road minutes between places, and when a site is open. | Shared by `fleet`, `market`, `notes` and `pairs`. |

## One car through the code

1. A request arrives. `Desk.step` folds the event into the books (`Books.observe`) and asks `Market.quote` for prices.
2. For each option `Market.quote` asks `Fleet.cost`: the note is read (`notes.read`), the hours in which the car can be collected in time are found (`notes.chances`), the on-time model picks the fee that costs least in all (`Fleet.fee`), and the cost is that fee plus the risk. The market takes the price with the highest (price − cost) × P(yes) (`Market.curve`) and quotes every option at that margin.
3. The dealer answers. `Market.learn` moves the parts of the level; a won order enters the books with the facts of its note.
4. `Desk.reconcile` plans. `Pairs.match` may put the car into one gig with a second car; if none comes within 30 minutes, `Desk.settle` posts the gig that `Fleet.plan` builds: the stops and their windows (`Fleet.stops`, `notes.windows`), the audience, one fee (`Fleet.schedule`).
5. The actions leave (`Desk.take`) and the world's answers come back (`Desk.sent`): a gig that the world took enters the books and the journal.
6. A lost driver, a deadline warning, an expired gig, a failed visit or a change of the order marks the order dirty, and `Fleet.due` adds the orders whose gig has sat to a moment of rule 1. The next `reconcile` withdraws, reprices or posts again.
7. After a restart `Desk.rejoin` folds the world's log and the journal through the same `fold` and `sent`.

## The rules it follows

1. **One flat fee per gig.** A fee schedule has one step. The fee is chosen again only when the gig has sat six hours without a driver, on the last day before the last possible pickup, at the deadline warning, or when a driver is lost. Drivers learn from fees that rise.
2. **Cost = fee + risk.** `Fleet.cost` is the fee, the expected refund of a late car, the car's use of the room under the delivery minimum, and its harm to the cars that already wait. There is no list of forbidden cars.
3. **Quote = argmax (price − cost) × P(yes).** Every other option of the request is quoted at the same margin over its own cost, so the dealer chooses its speed.
4. **State = a fold of events and acknowledged actions.** A module may remember only what follows from the world's log and the journal of `Desk.sent`. `tools/restart_test.py` checks it object by object.
5. **Every knob of an experiment is a field of `Policy`** (`MarketPolicy`, `FleetPolicy`, `PairsPolicy`). An experiment is a JSON override, never an edit. What is not a knob is a named constant at the top of its module, with its reason on the line: a number of the rules, a fitted weight, or one of the few set by hand (`fleet.GRIP`, `DOUBT`, `CALM`, `KNOWN`; `market.SURE`; `notes.MIN_SPAN`).
6. **A constant learned offline comes from a script** in `tools/` that regenerates it from saved weeks (table below).
7. **Fit on `halal-01..08`, confirm on `halal-09..16`.** No constant was fitted on the second set. One number was chosen after looking at it: the on-time target, 96% at that time (idea 11); idea 12 set it to 97% on the tune and wide weeks.

## Run it

```sh
python3 -m venv .venv && .venv/bin/pip install kit/spread-0.1.0-py3-none-any.whl pandas numpy   # pandas and numpy are for tools/ only
export SPREAD_URL=https://spread.bahnexpress.com SPREAD_KEY=<team key>

.venv/bin/python -m dispatch --level 8 --seed halal-01           # one practice week, about two minutes
.venv/bin/python -m tools.harness --tag my-run --seeds tune      # 8 weeks in parallel, saved to runs/my-run/
.venv/bin/python -m tools.study my-run                           # saved weeks -> one row per request
./final.sh                                                       # the final: waits for it, plays it, restarts itself
```

The default policy is the one the final plays. An experiment overrides it, for example `--policy '{"fleet": {"on_time": 0.96}, "pairs": {"hold": 0}}'`.
`RUNBOOK.md` is the procedure for a final: where to run it, how to tell that it is healthy, what to do if it dies.

## Where the evidence is

| File | What it holds |
|---|---|
| `PRESENTATION.md` | The deck: each idea, why we tried it, its effect on the same weeks. Appendix A lists every week of the final configuration. |
| `NIGHT_LOG.md` | The log of every idea in the order we had it, with the measured effect, and what did not work. |
| `RESEARCH.md` | What we measured about the world (drivers, dealers, the competitor) and how experiments are run. |
| `AUDIT.md` | A loss audit of Saturday morning's system: where money leaked, ranked by size. |
| `RUNBOOK.md` | The final, step by step, with the numbers of each rehearsal. |

The saved weeks themselves (`runs/`, 468 MB) are not in the repository. With a team key each tool below plays or reads them again.

| Baked-in number | Where | Regenerated by |
|---|---|---|
| Dealers: slope, trust, speed, level, a level per place | `dispatch/prior.py` | `python -m tools.winmodel fit explore1 market-r30 market-r15 main-m4-r0.15 market-z0` |
| Drivers: the 15 weights of the on-time model, the late share of booked cars, the average refund | `fleet.ON_TIME`, `BOOKED_LATE`, `REFUND` | `python -m tools.fleet_fit <tags>`; `--calibrate <tags>` compares it with outcomes |
| A real drive against the map's minutes | `notes.SLOW_DRIVE` | `python -m tools.drive_times base1,explore1` |
| The note reader's score | `dispatch/notes.py` | `python -m tools.label` (labels a world), `python -m tools.notes_eval` |
| Two-car gigs: fees, the 5-hour limit, the 60 minutes of patience | `pairs.PairsPolicy` | `python -m tools.offers_study shared offers-x3`, `… board offers-mx3` |
| What dealers do, exactly (thresholds by bisection) | `RESEARCH.md` | `python -m tools.probe`, `python -m tools.probe_read` |
| Restart = replay | — | `python -m tools.restart_test --seed halal-02 --restarts 12 --baseline <tag>` |
| The live loop under trouble | `RUNBOOK.md` | `python -m tools.rehearse`, `python -m tools.rehearse_remote` |

Set by hand and tested on the 8 tune weeks, not fitted: the fee steps (0.85 to 1.5 × the typical fee), 1.6 × after a deadline warning, the on-time target, the €300 and the fourth power in the price of the delivery minimum.

## What is weak

The on-time model is fitted on our practice weeks; a week can move only one number of it. A note in words outside the vocabulary is missed silently. Eight weeks do not resolve differences under about €500 a week. `PRESENTATION.md`, slide 9, has the list.
