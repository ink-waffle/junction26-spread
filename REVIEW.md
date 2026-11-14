# A reader's review of `dispatch/` (Saturday 17:00, branch `research/clarity`)

Read end to end as a jury member would: `README.md`, then each module. The question for each module: can its reason be said in one sentence, and does it do only that? Two passes: 15:30 over everything but `fleet.py`, 17:00 over `fleet.py`. Line counts are those of this branch.

## Each module

| Module | Its reason, in one sentence | Only that? | Where a reader still stumbles |
|---|---|---|---|
| `books.py` (234) | What the desk knows is a fold over the world's events. | Yes. | `OrderState.late` means two things (see 3 below). |
| `market.py` (197) | Learn each dealer's level from yes and no; quote the price with the highest expected margin over the fleet's cost. | Yes. `research()` is the one path that is not a decision of the final (see 4). | `odds()`: three lines of algebra over "which week is this"; the docstring says what, the deck must say why. |
| `fleet.py` (300) | The chance that a car arrives on time, the fee that buys that chance cheapest, and so what the car costs us. | Yes, since the split: public methods, the rule, the model, the queue and the week, in that order. | See 1. |
| `timetable.py` (163) | When a car can be collected and by when it must arrive. | Yes: the hours of a site and a note (functions, from `notes.py`), then the cars of our orders against them (`Timetable`, from `fleet.py`). | `windows()` is 22 dense lines. Three steps make a stop's window (`windows`, `stops`, `timed`); they now stand in one file. |
| `pairs.py` (121) | Two cars for one driver when the second starts where the first ends. | Yes. | `idle()` walks a route with five running variables. |
| `notes.py` (249) | The facts of a dealer's note. | Yes, since the split. | `clause_of` (40 lines). |
| `desk.py` (237) | One control loop: fold the events, then make the world match the plan; a restart replays through the same path. | Yes. | `rejoin` (49 lines, two inner functions). |
| `run.py` (236) | The two transports of that loop, and the command line. | Yes. | `live()`: six timers in one line. No practice week exercises it: left alone. |
| `names.py` (75) | The server's address when the resolver has none. | Yes. | A DNS client by hand inside a dispatcher. The reason is in its first line; say it on a slide too (robust). |
| `prior.py`, `atlas.py` | A generated table; the map and the opening hours. | Yes. | Nothing. |

## Where a jury member stumbles, ranked

1. **`fleet.py`, what is left.**
   - `car()` returns the signs of a request, and the dicts it returns are called `car` all the way down (`cheapest_fee(car, …)`, `logit(car, …)`). Two tools call `fleet.car`; not renamed.
   - `known`, `KNOWN`, `Queue.known` and the weight of `waited` have no support in the fit any more (`runs/reports/fleet2.md`). Taking them out changes decisions: they stay, and the deck should not claim them.
   - `FleetPolicy.on_time` (the share we aim at) and `ON_TIME` (the model's weights) still share a name. The policy field is in every saved command line; the method that was a third `on_time` is now `chance`.
   - Numbers set by hand, with no tool behind them, each with its reason on the line or in the docstring: `DOUBT`, `GRIP`, `CALM`, the cap of the late price at twice the allowed share, four Newton steps and one logit in `learned`. In `timetable.py`: `RETRY`, noon in `facts`, and `collect >= now + 30` in `rung`, whose reason nobody wrote down.
   - `Fleet.stops` is one line that hands over to the timetable, so that the pairs talk to the fleet alone.
   - `gig_posted` recovers the fee multiple it chose from the cents it posted, because a restart sees only the journal. The docstring says so.
2. **`desk.rejoin`** is the proof of "restart = replay" and the longest function of the system. Its comments are good; its two inner functions could be methods. Not touched: the no-journal path has no exact test.
3. **`OrderState.late`** is set when a gig expires (the car can only arrive late) and also when the world refuses a post (`Desk.refused`: "the usual reason is a window that has ended"). The fleet reads it as late for certain (`late_fee`, an outcome of 0 in `Fleet.outcome`, a whole late order in `late_price`). In halal-02 all 7 refusals of the week were ended windows, so it is right in practice; the name still carries a guess.
4. **`MarketPolicy.explore`, `Market.research()`** stay in `quote`'s first lines: the random weeks (`explore1`) behind `prior.py` were played with them. The fleet's twin of it is gone (the fit reads the saved weeks). Say it if asked, or delete both and `import random` (8 lines).
5. **Long lines** outside `fleet.py` and `timetable.py` (market 8, notes 9, desk 4 over 160 characters). The house style of one comment at the end of a line makes them.

## What the documents say and the code does not

`README.md` and `RESEARCH.md` follow the code (module table with `timetable.py`, the walk of one car through the code, 16 weights, 1,947 lines, eleven modules, the default policy without an override).

Not fixed, for whoever owns them:
- `PRESENTATION.md` describes commit `07c8f21` with the `early_look` override, a target of 96%, "12 weights" (slides 3 and 9), 1,785 lines and 10 modules (slide 1), and has no idea 12, 13 or 14. `SPEAKER_NOTES.md:24` and `OPEN_NUMBERS.md:58` repeat the line count.
- `OPEN_NUMBERS.md` §6, rows 1 and 5 (`early_look` defaults to 0; `ON_TIME` has no pickup side, target 96%): true at 12:45, not now.
- `NIGHT_LOG.md` is a log and may keep its history, but three sentences read as present tense: idea 1 "the fee changes at most once" (four moments: `Fleet.looked`), idea 3 "decline (quote 4 × list)" (`market.DECLINE` is 10), idea 5 "once expected late orders pass 5%" (3% at an aim of 97%).

## What the two passes changed

No decision changed. Each push was proved on its tree: `tools.harness` on halal-02 and halal-05 to the cent against the tree the pass started from, and `tools.restart_test --seed halal-02 --restarts 8`: the same desk 8 times of 8, the same week to the cent. Beside that, offline: the old and the new market (15:30) and the old and the new fleet (17:00) replayed side by side on both weeks, every quote, cost, plan, fee and queue equal bit for bit; and the offline tools print the same text from the old tree and the new.

15:30, everything but the fleet:
- `books.py`: dead fields and handlers gone; `on_time` → `trust`; what the desk calls first, then one handler per event.
- `market.py`: research switches `reserve` and `options` gone, and two parts of the level that no prior had; `learn` in three named steps; one order of definitions.
- `desk.py`: `reconcile` + `settle`; `sent` + `record` + `refused`; `sent`'s second pass over withdraws and reprices gone.
- `pairs.py`: `match` + `dissolve` + `gig`. `run.py`: the practice loop no longer wakes on `offer_answered`.
- The market with a reserve (idea 7's comparison) and the market that quotes one option (idea 8's) can be played from `944f656` or before, not from the head.

17:00, the fleet:
- Names: `fee` → `cheapest_fee` (the model), `fee_multiple` → `fee_now` (the rule), `on_time()` → `chance()`, `chances` → `chances_left`, `step` → `rung`.
- `learned()` reads each order through `outcome()`, one case a line; `Queue.without()`; the charging test once (`charges`); the pairs' hold comes in through the constructor; `Books.drivers` is the roster itself.
- The split: `timetable.py` takes the second half of `notes.py` and the stops, windows and hours of `fleet.py`. `Fleet` is still the one object that the desk, the market and the pairs call.
- No line of `fleet.py` or `timetable.py` is over 160 characters; each constant says where its number comes from.
