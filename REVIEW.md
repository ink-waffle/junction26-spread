# A reader's review of `dispatch/` (Saturday 15:30, branch `research/clarity`)

Read end to end as a jury member would: `README.md`, then each module. The question for each module: can its reason be said in one sentence, and does it do only that? Line numbers are those of this branch.

## Each module

| Module | Its reason, in one sentence | Only that? | Where a reader still stumbles |
|---|---|---|---|
| `books.py` (231) | What the desk knows is a fold over the world's events. | Yes, after this pass. | `OrderState.late` means two things (see 5 below). `DriverState` holds one field, because `fleet.py` reads `driver.profile`. |
| `market.py` (197) | Learn each dealer's level from yes and no; quote the price with the highest expected margin over the fleet's cost. | Yes. `research()` is the one path that is not a decision of the final (see 6). | `odds()`: three lines of algebra over "which week is this"; the docstring says what, the deck must say why. |
| `fleet.py` (318) | A car costs its fee plus its risk; the same model picks the fee. | It also builds stops and windows, reads failed visits, and keeps the rule for when a fee is chosen again. | The file a reader gets lost in. See 1. |
| `pairs.py` (120) | Two cars for one driver when the second starts where the first ends. | Yes. | `idle()` walks a route with five running variables. |
| `notes.py` (313) | The facts of a dealer's note. | No: the second half (`real`, `arrive_by`, `collect_spans`, `chances`, `windows`) turns facts into stop windows. The README says so; it is still two jobs in one file. | `clause_of` (40 lines) and `windows` (22 dense lines). |
| `desk.py` (241) | One control loop: fold the events, then make the world match the plan; a restart replays through the same path. | Yes. | `rejoin` (49 lines, two inner functions). `sent` applies a withdraw and a reprice twice (see 4). |
| `run.py` (235) | The two transports of that loop, and the command line. | Yes. | `live()`: six timers in one line. It is the code that kept Saturday's runs alive, and no practice week exercises it: left alone. |
| `names.py` (74) | The server's address when the resolver has none. | Yes. | A DNS client by hand inside a dispatcher. The reason is stated in the first line; say it on a slide too (robust). |
| `prior.py`, `atlas.py` | A generated table; the map and the opening hours. | Yes. | Nothing. |

## Where a jury member stumbles, ranked

1. **`fleet.py` is three modules in one, written in lines of 200 characters.** Twenty lines are longer than 160 characters; its functions look short only because of that. What a reader meets, in order of cost:
   - Three functions set a stop's window (`stops` → `notes.windows`, then `timed` → `step`), and `pairs` calls `stops` without `timed`. Nobody can say in one sentence who decides a window.
   - `fee()` (the model's cheapest fee), `fee_multiple()` (the rule for when a fee is chosen again, which calls `fee`) and `schedule()` (which calls `fee_multiple`): the names do not say which is which.
   - `on_time` is a target share (`FleetPolicy.on_time`), a chance (`Fleet.on_time()`) and the weights (`ON_TIME`).
   - `learned()` line 119 (`or`/`and` without brackets) and line 121 (four outcomes in one conditional expression).
   - `late_price()`: `min(2.0, used)` has no reason on the line; with `GRIP` it is the cap of €4,800 that the night log speaks of.
   - `chances()` exists twice (`fleet.chances(state)`, `notes.chances(request, option, …)`) with nearly the same body.
   - The charging test (electric, under 30%, over 200 km) is written out twice (`road`, `stops`), the comment "the world refused our windows once" twice (`timed`, `stops`).
   - `self.held = lambda state: False`, replaced from outside by the desk (`desk.py:44`): a hidden wire. The tools build a `Fleet` without it.
   - Research switches in the decision path: `crowding` (the term is needed, the knob is not: no tool reads it), `explore` + `seed` + `import random` (last line of `fee_multiple`, and `gig_posted`).
   - `Fleet` has no docstring; public methods (`cost`, `plan`, `schedule`, `due`, `gig_posted`, `stops`, `audience`) are scattered among helpers.
   - Eight numbers set by hand sit outside `Policy` (`DOUBT`, `GRIP`, `CALM`, `KNOWN`, `RETRY`, `LAST_DAY`, the 2.0 above, 12:00 in `facts`). The README's rule 5 now says so.
2. **`notes.py` does two jobs.** Moving the second half to its own module needs four import lines in `fleet.py`; not done because `fleet.py` was being edited.
3. **`desk.rejoin`** is the proof of "restart = replay" and the longest function of the system. Its comments are good; its two inner functions (`adopt`, `recall`) could be methods. Not touched: the no-journal path has no exact test.
4. **`desk.sent` lines 132–136 and 150–153** do the same thing twice (withdraw, reprice): once for every action, once for every accepted one. The second is redundant in every case a week produces; removing it is not provably neutral for two reprices of one gig in one batch, so it stays and is reported.
5. **`OrderState.late`** is set when a gig expires (the car can only arrive late) and also when the world refuses a post (`desk.py:178`, "the usual reason is a window that has ended"). The fleet then reads it as "late for certain" (`late_fee`, an outcome of 0 in `learned`, a whole late order in `late_price`). In halal-02 all 7 refusals of the week were ended windows, so it is right in practice; the name still carries a guess.
6. **`MarketPolicy.explore`, `Market.research()`** stay in `quote`'s first lines. Reason: the random weeks (`explore1`) that `prior.py` is fitted on are played with them. Say it if asked; or delete both and `import random` (8 lines) if those weeks need never be played again.
7. **Long lines everywhere** (market 7, notes 10, desk 4 over 160 characters). The house style of one-line comments at the end of a line makes them; a jury member reading on GitHub scrolls sideways.

## What the documents say and the code does not

Fixed in this branch (`README.md`, `RESEARCH.md`, `tools/harness.py`'s example):
- README "Run it" passed `{"fleet": {"early_look": 6}}` and said the default is off. The default is 6.
- README rule 5 said every tunable is a field of `Policy`; a dozen named constants are not. Rule 7 named a target of 96%; the code has 97%.
- README: 12 weights of the on-time model (15), `read(note)` (`read(note, arrived_at)`), 1,785 lines (1,863 on this branch; count again after the fleet merge).
- `RESEARCH.md` and the harness docstring gave example overrides with fields that no longer exist (`fleet.fee`, `market.price`): a first run with them dies.

Not fixed (not this branch's files to rewrite; for whoever owns them):
- `PRESENTATION.md` describes commit `07c8f21` with the `early_look` override, a target of 96%, "12 weights" (slides 3 and 9) and 1,785 lines (slide 1). The code is ideas 1–13: default look, 97%, 15 weights, the events weighed.
- `OPEN_NUMBERS.md` §6, rows 1 and 5 (`early_look` defaults to 0; `ON_TIME` has no pickup side, target 96%): true at 12:45, not now.
- `NIGHT_LOG.md` is a log and may keep its history, but three sentences read as present tense: idea 1 "the fee changes at most once" (four moments: `Fleet.looked`), idea 3 "decline (quote 4 × list)" (`market.DECLINE` is 10), idea 5 "once expected late orders pass 5%" (3% at a target of 97%).
- `SPEAKER_NOTES.md:24`: 1,785 lines.

## What this pass changed

Every commit leaves the decisions as they were: `tools.harness` on halal-02 and halal-05 gives €21,071.78 and €24,033.59, 517 and 594 orders, as on `944f656`; `tools.restart_test --seed halal-02 --restarts 8` rebuilds the same desk 8 times of 8 and plays the same week to the cent. For `market.py` also a replay of both weeks through the old and the new market: every quote, level and belief equal, bit for bit.

- `books.py`: dead fields and handlers gone (33 lines: what the dropped direct offers needed); `on_time` → `trust`; the fold first, then one handler per event.
- `market.py`: two research switches gone (`reserve`, `options`) and two parts of the level that no prior had; `learn` in three named steps; one order of definitions; a docstring for every method.
- `desk.py`: `reconcile` → `reconcile` + `settle`; `sent` → `sent` + `record` + `refused`.
- `pairs.py`: `match` → `match` + `dissolve` + `gig`; the public methods first.
- `run.py`: the practice loop no longer wakes on `offer_answered`; the `--policy` help names a field that exists.
- Kept on purpose: `MarketPolicy.surprises` and `spread` (`tools/surprises.py` replays the market before idea 13 with them; `tools/winmodel.py` fits through `spread` and `places`), `explore` and `seed` (see 6), every field of `PairsPolicy` (each is a knob of a logged experiment and has its reason on the line).
