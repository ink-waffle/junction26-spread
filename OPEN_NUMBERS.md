# Open numbers — every placeholder, and what fills it

State: Saturday 23:15, commit `8ae61c5` (ideas 1–15; the default policy is what the final plays). For Sunday morning. Work from the main checkout. Sections 3 to 6 date from the deck of ideas 1–14 (Saturday 17:50, `0b050b8`); their numbers are those of the system before idea 15 unless a row says otherwise.

```sh
cd /Users/ink_waffle/OverengineeringLife/Junction2026/spread
export SPREAD_SHARED=$PWD; set -a; . ./.env; set +a; PY=.venv/bin/python
vm() { ssh -i ~/.ssh/verda_junction -o BatchMode=yes "$SPREAD_VM" "$@"; }
```

Two helpers that only read saved files (paste them once):

```sh
# weeks <tag> [<tag> …]: every saved week of a tag, and the tag's mean margin, worst and mean on-time, ranked, orders
weeks() { $PY - "$@" <<'EOF'
import glob, gzip, json, os, sys
for tag in sys.argv[1:]:
    scores = [json.load(gzip.open(p, "rt"))["score"] for p in sorted(glob.glob(f"runs/{tag}/*.json.gz")) if os.path.getsize(p)]
    for path, s in zip(sorted(p for p in glob.glob(f"runs/{tag}/*.json.gz") if os.path.getsize(p)), scores):
        print(f"{tag} {os.path.basename(path)[:-8]}  €{s['marginCents']/100:,.0f}  {s['onTimeShare']:.1%}  {s['wonOrders']} orders  {'ranked' if s['ranked'] else 'NOT RANKED'}")
    n = len(scores)
    print(f"== {tag}: {n} weeks  €{sum(s['marginCents'] for s in scores)/100/n:,.0f} a week  on time worst {min(s['onTimeShare'] for s in scores):.1%} mean {sum(s['onTimeShare'] for s in scores)/n:.1%}  ranked {sum(s['ranked'] for s in scores)}/{n}  {sum(s['wonOrders'] for s in scores)/n:.0f} orders")
EOF
}
# rounds: every ranking round we played, from runs/board.jsonl (a round = the runs of one three-hour slot)
rounds() { $PY - <<'EOF'
import collections, json
rounds = collections.defaultdict(list)
for line in open("runs/board.jsonl"):
    run = json.loads(line); day, clock = run["at"].split(); rounds[(day, int(clock[:2]) // 3 * 3)].append(run)
for (day, hour), runs in rounds.items():
    print(f"{day} round {hour:02d}:00  €{sum(r['margin'] for r in runs):,.0f} for {len(runs)} weeks (€{sum(r['margin'] for r in runs)/len(runs):,.0f} a week)  on time {min(r['onTime'] for r in runs):.1%}–{max(r['onTime'] for r in runs):.1%}  ranked {sum(r['ranked'] for r in runs)}/{len(runs)}  orders {min(r['won'] for r in runs)}–{max(r['won'] for r in runs)}  {runs[-1]['commit']}  {json.dumps(runs[-1]['policy'])}")
EOF
}
```

## 1. Results still to come

| Placeholder | Where | What fills it |
|---|---|---|
| `[FINAL: € … margin, … % on time, … orders, place … of …]` | PRESENTATION slide 1, README line 10, SPEAKER_NOTES slide 1 | Margin, on-time share and orders: the last lines of the desk's log, `vm 'grep -E "^End|Ranked" /data/spread/repo/final.log \| tail -n 2'` (on the laptop: `final.log` in the checkout). Place: the leaderboard at https://spread.bahnexpress.com. |
| `[SUNDAY: closing place, leaderboard]` of the 21:00 round | PRESENTATION slide 10 | The leaderboard once the round closes (at 21:08 we were 3rd of 11 ranked). Add it to `NIGHT_LOG.md`, "Ranking rounds and test finals". |
| `[SUNDAY: rounds 00:00, 03:00, 06:00 …]` | PRESENTATION slides 1 and 10 | `rounds` prints margin, on-time and orders of each round; place and House best from the leaderboard. They are the first rounds of the frozen system (8ae61c5). "Best" on slide 1 is the round with the highest margin against House best on the same weeks: today Saturday 18:00, 1.29 × (€75,405 against €58,677), closed 10th of 67. If a Sunday round beats it, replace all three numbers. |
| Submission hash | Junction form (not in the deck) | https://spread.bahnexpress.com/team |

## 2. Filled on Saturday 23:15 for the frozen commit `8ae61c5` (from saved runs only)

| Number | Where | Source |
|---|---|---|
| 32 fresh weeks `halal-129..160`, no stride, once: €14,313 against €13,547 (+€766, se 221), on time 96.3% both (−0.03 point, se 0.15), worst 92.8% against 93.1%, 32 of 32 both, 426 against 402 orders, 24 of 32 weeks up | PRESENTATION slides 1, 9, 10, Appendix A; README; SPEAKER_NOTES 1, 9, 10 | `weeks orch-head-record orch-old-record`; `$PY -m tools.ablations orch-oldrec orch-headrec` |
| Orders by weekday 82 / 91 / 88 / 95 / 76 against 71 / 85 / 81 / 96 / 73; Monday +10.8 (se 3.0); Monday's sales +€1,178 (se 232) | slide 9 | `$PY -m tools.weekdays orch-oldrec orch-headrec` |
| `halal-97..128` without strides: €16,266, worst 94.1%, mean 96.4%, 454 orders; the old system €15,829, 94.3%, 96.2% | slides 9, 10 | `weeks skeptic-C975-B-s0 skeptic-Bbase-B-s0` |
| Hold, stride 14: €15,488, worst 94.6%; tune and wide, stride 14: €15,444, worst 94.5%, 24 of 24 | slide 10 | `weeks skeptic-holdC975-x-s14 skeptic-twC975-x-s14` |
| +€679 (se 206) and +0.52 point on `halal-65..96`; hold four samples +€694 (se 142); tune and wide +€625 (se 331); 216 plays, none unranked | slides 9, 10, Appendix B | `SKEPTIC.md` section 0 (tags `skeptic-*`; `python -m tools.ablations`) |
| What idea 15 found and what stayed: 10.0% said against 4.8% late; +0.86 / +0.90 / +0.87; `known` +0.25 against −0.17 ± 0.06; −0.3 and +1.2 per mille; 4.3% said against 4.0%; −€2,967 / −€1,702 / −€1,444 / −€1,394 / −€998; 4 of 32 | slide 9, slide 11 | `python -m tools.skeptic_fit orch-base-s14 -- final-fresh skeptic-base-s14`; `python -m tools.skeptic_market final-fresh skeptic-base-s14`; `SKEPTIC.md` sections 1, 3, 5; `NIGHT_LOG.md` idea 15 |
| Agent simple's D: −€76 (se 184); Monday's dealers pay 12% less; one logit too easy: −2.8 points without the learner, −1.0 with it, a week at 90.5% | slides 9, 11; README; SPEAKER_NOTES 9, 11 | `runs/reports/simple.md` (branch `research/simple`) |
| 1,900 lines, eleven modules, 15 weights, five parts, 123 numbers | slides 1, 3, 4, 9; README | `wc -l dispatch/*.py \| tail -n 1`; `python -c "from dispatch.fleet import ON_TIME; print(len(ON_TIME))"`; `dispatch/prior.py` `SPREAD`; `SKEPTIC.md` section 5 (129 → 123) |
| Average fee 0.95 × typical; 27% of cars in a two-car gig at 0.80 × and 99.1% on time, never paired 0.98 × and 95.5% | slides 2, 7; SPEAKER_NOTES 7 | `$PY -m tools.offers_study paired orch-head-record` |
| Restart test 8 of 8, €21,126.94 with and without (halal-02); halal-98 to the cent (€9,309.09) | slide 10 | `SKEPTIC.md` section 5; `NIGHT_LOG.md` status 23:00 (`runs/orch-headverify.out`) |
| Test final 20:00: €15,752.50, 424 orders, 97.2%, 18th of 75 (first €19,592, 10th €16,623); 49 / 99 / 73 / 109 / 94 orders; 1,030 requests, slowest turn under 0.25 s | slides 1, 10 | `NIGHT_LOG.md`, "Ranking rounds and test finals" |
| Rounds: 15:00 closed 19th of 63; 18:00 €75,405, 1.29 × (€58,677), closed 10th of 67; 21:00 €79,391, 1.20 × (€66,136) | slides 1, 10 | `rounds`; `NIGHT_LOG.md`, "Ranking rounds and test finals" (the 14th of 42 of the first draft was read before the 15:00 round closed) |
| 152 of 186 commits on `main` carry an agent's co-author line | SPEAKER_NOTES, "How much of this was written by agents?" | `git log --format=%H --grep=Co-Authored-By main \| wc -l`; `git rev-list --count main` (at `cce0985`) |
| `[FILL IN …]`: what the two of you did yourselves | SPEAKER_NOTES, same answer | Only you know. |

The numbers of ideas 1–14 that the deck keeps (tune €17,846; hold €14,806; wide €13,418; the restart 12 of 12 at €20,493.78; 28% of cars paired at 0.81 ×) are the system before idea 15 and are labelled so: `weeks fleet3-cand-ns fleet3-cand-hold orch-base-s14`.

## 3. Filled since the first draft (no longer open; the source, in case a number is questioned)

| Number | Source |
|---|---|
| Kit starter on our own weeks: tune −€63,232, 52.1% on time, 0 of 8; hold −€68,908, 47.8%, 0 of 8 | `tail -n 9 runs/starter-tune.out`, `tail -n 9 runs/starter-hold.out`; played by `$PY -m tools.starter_weeks --seeds tune` and `--seeds hold`. |
| Test final Saturday 14:00: €3,747.26, 167 orders, 97.6% on time, 2nd of 55 ranked teams (217 entered); first €4,023, 10th €3,292; every request quoted, no action refused, slowest turn 0.86 s | `NIGHT_LOG.md`, "Ranking rounds and test finals"; the desk's `final.log` on the cloud machine; the places from the leaderboard. |
| Ranking rounds: 09:00 €48,860 (House best €50,660), 12:00 €82,785 (€77,560), 15:00 €82,278 (€64,249) | Margins: `rounds`. House best: `NIGHT_LOG.md`, read from the leaderboard. |
| Places: 09:00 35th of 45, 12:00 22nd of 58, 15:00 19th of 63 (read as 14th of 42 at 17:36, before it closed) | The coordinator's reading of the closed rounds; the 15:00 one from the 18:00 entry of `NIGHT_LOG.md`. `NIGHT_LOG.md` still has the standings while the 12:00 and 15:00 rounds were open (15th of 33; first of 7): use the closed ones. |
| The six-hour look and the 97% aim are the defaults; `final.sh` needs no `--policy` | `grep -n "early_look\|on_time:" dispatch/fleet.py` |

## 4. Final numbers, with the command that reprints them

No practice worlds needed; all read `runs/`.

| Number | Command |
|---|---|
| Any before/after pair on a slide (margin, worst on-time, ranked, orders of a tag) | `weeks <tag-before> <tag-after>`; or `$PY -m tools.compare <tag-before> <tag-after>` |
| Monday bisection: 10,181 options, 5,581 requests, 24 worlds, 87.7% within 3%, median bracket 0.5%; sd 8.2% inside a lane; 98.1% of 2,397 menus; €14.5 and €6.1 for speed; trust +0.9% per order; competitor −4% per unit of share; r = 0.38 lanes, 0.01 dealers | `$PY -m tools.probe_read` |
| The surprise days in the replay: €12,082 → €12,284 a week (+€202, se 66, 19 of 24 weeks up); told at 08:00 +€300; requests until within 5%: war 18 → 4, outage 67 → 7 | `$PY -m tools.surprises money` (three minutes; the last 80 lines) |
| War day 0.23 log under calm days, outage +0.26, calm days stray by 0.04; 24,127 thresholds | `$PY -m tools.surprises exact` |
| War day named in 24 of 24 weeks, outage day in 16 of 19 | `$PY -m tools.surprises find surprise-weighs surprise-weighs-wide` |
| Played weeks with and without the events: tune €17,421 → €17,813, wide €13,201 → €13,536 | `weeks surprise-before surprise-weighs surprise-before-wide surprise-weighs-wide` |
| The flu's night: 33% and 3% (`fleet.SICK`, `WELL`); 2.7% given back on other nights; 19 such nights in 19 of 24 weeks; cars of a bulk order come back like the others | `$PY -m tools.night_study surprise-weighs surprise-weighs-wide` |
| The flu sign: 25 weeks, 49 samples a side: on time +0.38 point (se 0.20), late orders −1.6 a week (se 0.9), margin −€23 (se 232), 18 of 25 weeks up, worst sample 91.4% → 92.6%; halal-09 92.3% → 94.6% | `$PY -m tools.replicates surprise-weighs,surprise-weighs-wide,fleet3-main-s12,fleet3-main-s13,fleet3-main-s15,fleet3-before-hold fleet3-flu4-s12,fleet3-flu4-s13,fleet3-flu4-s14,fleet3-flu4-s15` |
| The flu sign on hold, three samples a side: +0.30 point (se 0.26), margin −€252 (se 209) | `$PY -m tools.replicates fleet3-before-hold,fleet3-before-hold-s12,fleet3-before-hold-s13 fleet3-cand-hold,fleet3-cand-hold-s12,fleet3-cand-hold-s13` |
| Every knob, 24 weeks, two samples a side: fee floor 0.75 × −€771 (se 222), 0.90 × −€47 (se 246); aim 96.5% +€112 (se 176) for −0.51 point; look at 12 h −€342 (se 160); pairs 60 min and 6 h +€284 (se 304) for −0.57 point; finer fee grid −€624 (se 284) | `$PY -m tools.replicates orch-base-s14,orch-base-s13 orch-<knob>-s14,orch-<knob>-s13` with `<knob>` = `low75`, `low70`, `hi90`, `hi95`, `hi100`, `t965`, `t96`, `look12`, `pair`, `fine` |
| The pickup side: hold €13,472 → €13,753, late 23.1 → 15.7 a week; wide €13,240 → €13,201, late 17.8 → 14.6 | `$PY -m tools.compare main-look6-s14-hold fleet2-s-v2b-hold`; `$PY -m tools.compare main-look6-s14-wide fleet2-s-v2b-wide` |
| The aim as a knob (96.5% / 97% / 97.5% on 24 weeks) | `runs/reports/progress.md`, line of 13:30; the tags are `fleet2-s-*` in `runs/log.jsonl` |
| Drivers and the look: booked at the first fee within 15 minutes, Monday to Friday (73 / 71 / 65 / 67 / 48% and 71 / 67 / 59 / 58 / 33%) | `$PY -m tools.waiting_study main-m10 fleet2-base-look6` |
| A gig still open on its last day ends late one time in four (47 a week, 24%) | `$PY -m tools.late_study main-m9-look6-ot96 main-m9-look6-ot96-wide` |
| A booking as a promise: given back 18% when made the day before, 5% when made that morning | `$PY -m tools.promise_study fleet2-s-v2b fleet2-s-v2b-wide` |
| Meeting the drivers on the day: late 11.1% against 7.0% | `$PY -m tools.meet_study fleet3-meet6-par` |
| The census: a silent day in 7 of 20 weeks | `runs/census/<seed>.json`; `tools/census.py` prints the table when it plays a seed |
| Notes: 22,099 of 22,099; 6,152 facts | `$PY -m tools.notes_eval --tag notes-label,notes-val1,notes-val2` |
| Notes on hold: 3,539 of 3,539 | `$PY -m tools.notes_eval --tag notes-label-hold` |
| Notes with one more typo: 99.69% | `$PY -m tools.notes_eval --tag notes-label,notes-val1,notes-val2 --typos` |
| The real note of slide 8 | World `halal-03`, request arrived Friday 09:46: `$PY -c "from dispatch import notes; print(notes.read({'text': 'Liike auki arkisin klo 7-20. Huolto kesken, valmis klo 15, ei kun klo 14. Lisäksi 4 kesärengasta tavaratilassa'}, 4*1440+586))"` gives ready at minute 6600 (Friday 14:00), pickup open 420–1200 (07:00–20:00), no tyre flag. |
| Direct offers: 75,390 offers, 85 yes | `$PY -m tools.offers_study offers offers-x2` |
| Two-car gigs against the same cars as two gigs (0.89 × against 1.21 ×; 85% booked; 29% over 6 hours) | `$PY -m tools.offers_study shared offers-x3` |
| A new car with a car that sits (0.70 × → 46%, 0.85 × → 76% delivered as a pair) | `$PY -m tools.offers_study board offers-mx3` |
| 26 orders a week reached the warning after a median 70 hours; 52% late | `$PY -m tools.audit main-m4-r0.0` |
| The five pickup-side signs as fitted | `$PY -m tools.fleet_fit --add supply_pickup,supply_delivery,private_delivery,premium,pay main-m8 main-m9-look6 main-m9-look6-ot96 fleet2-s-base fleet2-s-k5-signs` |
| The flu sign as fitted (−2.6, intercept −5.75) | `$PY -m tools.fleet_fit --add flu <tags>`. It was fitted on 48 saved weeks, 11,008 orders (progress line 15:52); the log does not name the tags, so the exact figures may not reprint. |

Two comparisons can be read from saved runs but not played again from the head: the market with a reserve (slide 3, row 2) and the market that quotes one option (slide 4, rows 2 and 3). Their switches left the code in the reader's pass; they play from commit `944f656` or earlier.

## 5. Numbers on the slides that no command in the repository reprints

Say them as measured once, or cut them. They come from the agents' progress lines (`runs/progress.md`) and reports (`runs/reports/`); the scripts were scratch files.

| Number | Slide | Source |
|---|---|---|
| "96% on time when booked before the deadline warning, 25% when not"; the six-point supply curve | 3 | `RESEARCH.md`, from `explore1`. Can be recomputed from `tools.study.table("explore1")`, but no tool prints it. |
| Late 12.6 / 10.0 / 6.5 / 3.3% by drivers within 30 km of the pickup | 3 | `NIGHT_LOG.md` idea 12; progress line 13:14 (fleet2) |
| The faster option costs a median €11 more (was €16); fastest sold in 57% of two-option wins (was 49%) | 4 | `NIGHT_LOG.md` idea 12; `runs/reports/fleet2.md` |
| Monday replay in euros: €2,103 / €2,065 / €3,723, on 7 tune worlds | 5 | progress line 11:02 and `runs/reports/market.md` |
| The starter's median booked fee by weekday (1.0, then 1.5, then 2.5 × typical), 186 Monday bookings, €118.6k of fees | 2 | `NIGHT_LOG.md` idea 1, from the starter's reveal of `spread-1` (`reveal-w7b05a9e2208ac23c76f8/`) |
| The model says 12.9% late where 6.4% are; the week's intercept corrects it within about forty orders | no longer on the slides: idea 15 deleted the week's intercept (the level is now set once, slide 9) | `runs/reports/fleet2.md`, "What is fragile" |
| Without a war the replay still gains €66; without both events it loses €118 | 11; SPEAKER_NOTES slide 6 | `NIGHT_LOG.md` idea 13; `runs/reports/surprises.md` |
| About 30% of the bookings held for the second Monday come back at its midnight | SPEAKER_NOTES slide 11 | `runs/reports/fleet3.md`, "What is fragile" |
| Restart without a journal costs 2–4% | SPEAKER_NOTES slide 10 | `runs/reports/live.md`; two measurements on Saturday morning's system. Rerun: `$PY -m tools.restart_test --seed halal-01 --restarts 12 --no-journal --baseline final-tune`. |
| The restart bug: 1 of 12, €16,942 against €19,251 | 10 | `runs/reports/offers.md`; `runs/offers-restart-halal-09.out` |

## 6. Where the log and the code disagree

Checked on Saturday 17:50 against commit `0b050b8`. The deck follows the code and the saved runs. Rows of the first draft that the code has since resolved are gone (the six-hour look is the default; the model has the pickup side; the aim is 97%).

| The log says | The code or the saved run says | What was done |
|---|---|---|
| `NIGHT_LOG.md` idea 1: "The fee changes at most once, at the deadline warning." | `Fleet.looked`: four moments. | A dated "Now:" line under idea 1. Slide 2 names the four moments. |
| `NIGHT_LOG.md` idea 3: a decline is a quote of 4 × list; a request with under 8 hours of slack is declined. | `market.DECLINE = 10.0`; no slack rule since idea 5. | A dated "Now:" line under idea 3. |
| `NIGHT_LOG.md` idea 4: five parts of the level, one option quoted. | `prior.SPREAD` has seven parts; the day part has two beliefs; every option is quoted. | A dated "Now:" line under idea 4. |
| `NIGHT_LOG.md` idea 5: signs "who lives near pickup and delivery, private stops"; the price rises past 5%; fee 1.16 → 0.95 × typical. | `fleet.ON_TIME`: 16 weights; the aim is 97%, so 3%; the saved runs give 1.17 × (`base1`) → 1.08 × (`fleet-v3`). | A dated "Now:" line under idea 5. Slide 3 uses 3%. |
| `RESEARCH.md`, `NIGHT_LOG.md` idea 8: 5,516 (2,515) options known to 0.5%; sd 0.176 / 0.128 / 0.084; 2,291 menus; two options of a request are "nearly independent". | `python -m tools.probe_read` today: 10,181 options, sd 0.155 / 0.126 / 0.082, 2,397 menus. The independence was withdrawn the same morning (progress line 11:13): a slower option's threshold is the faster one's minus a number of euros per dealer. | Slide 5 uses the tool's output. Not edited in the log. |
| `NIGHT_LOG.md`, "Price precision": the Monday replay is "on 24 seeds". | Progress line 11:02 and `runs/reports/market.md`: 7 tune worlds. | Slide 5 says 7 tune worlds. Not edited in the log. |
| `NIGHT_LOG.md`, rounds: 12:00 "15th of 33", 15:00 "first of the 7 ranked teams that had finished". | Closed rounds: 22nd of 58, 19th of 63 (the 12:00 figure is also in the 15:00 entry; the 15:00 one in the 18:00 entry). | Slides 1 and 10 use the closed rounds. |
| `NIGHT_LOG.md` status 15:10: "the big midnight give-back nights … not the flu, it seems: they follow the bulk order". | Idea 14 and `tools/night_study.py`: they are the flu's night; cars of a bulk order come back like the others. | The status row is history; slide 6 follows idea 14. |
| `README.md`: 1,947 lines; `runs/` is 945 MB; the starter on its own seed. | `wc -l dispatch/*.py`: 1,948; `du -sh runs`: 1.2 GB at 17:40; the starter on our weeks is in `runs/starter-*.out`. | Fixed in `README.md`. |
| `REVIEW.md`: the fleet's `known` and `waited` weights have no support in a refit. | Idea 15 deleted `known` (wrong sign on unseen weeks); `waited` is in `fleet.ON_TIME` and decides. | Slide 11 names `waited`, `short`, `trade_in` as open under "What we do not know". |

## 7. Added by the story pass (Sunday 02:50, branch `research/story`)

The deck now has ten slides; old slide numbers in sections 1–6 map as 1→1, 2→4, 3→4, 4→3, 5→2, 6→5, 7→6, 8→6, 9→7, 10→9, 11→8 and 10. `[FINAL …]` is on slides 1 and 10 and in SPEAKER_NOTES part 1; `[SUNDAY …]` on slides 1 and 9 and in SPEAKER_NOTES question 1.

| Number | Slide | Source |
|---|---|---|
| On-time model on the 32 fresh weeks: 4.2% said, 4.5% late; lanes over 400 km 7.8% said, 10.9% late (53 orders a week) | 1, 3, 4, 10 | `$PY -m tools.fleet_fit --calibrate orch-head-record`; `GAP.md` on `research/gap`, §1 item 4 |
| Dealer side: 44.4% said yes, 45.2% yes, 30,517 quotes, within 3 points in every bin | 1, 3, 10 | `GAP.md` §1 item 5, from the gap agent's scratch `mcal.py`: no tool in the repository reprints it, and GAP.md does not name the weeks (the items around it read `orch-head-record`) |
| 160 of 160 plays on the 96 unseen weeks `halal-97..192`, mean €15,327 a week, mean on time 96.4%, worst 92.3% (halal-189); `halal-161..192` €14,964, 96.4%; 273 distinct plays of 160 weeks of the frozen system, all ranked | 1, 9 | the snippet below, over `runs/log.jsonl` |
| 98.1% of 2,397 menus (RESEARCH.md's 2,291 is an earlier snapshot of 7–15 seeds) | 2 | `$PY -m tools.probe_read` |
| The graveyard's rows | 8 | `NIGHT_LOG.md`, "Did not work" (hunt, trade-ins, chains, offers2, gap, the knob brackets, the finer grid, meeting the drivers, the crisis price, the early look); `runs/progress.md` 23:59–01:51 |
| The leader: +11% orders, +€3.2 an order, 97.2% against 97.3% on time, about 470 orders at 641 or 933 drivers; 164 variants on −0.13 × orders% − 0.9; the audit's step +4.6% orders, +€0.25 an order, +0.45 point | 7, 8 | `runs/reports/detective.md` §0, §3; `runs/detective/variants.py`, `levers.py` |
| Sunday 00:00 round: €81,046, 1.33 × House best (€60,812), 2nd of 18 ranked at 00:06 | 1, 9 | `NIGHT_LOG.md`, "Ranking rounds and test finals"; `rounds` |

From the main checkout, paste this into `$PY -I -`:

```python
import json
tags = {"unseen": ["skeptic-C975-B-s0", "skeptic-C975-B-s14", "orch-head-record", "orch-main161-s14", "orch-main161-s13"],
        "all": ["skeptic-C975-s14", "skeptic-C975-B-s14", "skeptic-C975ns-x-s0", "skeptic-C975-B-s0", "skeptic-twC975-x-s14",
                "gap-main-s13", "orch-head-record", "orch-main161-s14", "orch-main161-s13"]
                + [f"skeptic-holdC975-x-s{s}" for s in (12, 13, 14, 15)]}
rows = {d["tag"]: d["results"] for d in map(json.loads, open("runs/log.jsonl")) if d["results"]}
for name, ts in tags.items():
    plays = list({(x["seed"], round(x["margin"], 2)): x for t in ts for x in rows[t]}.values())
    worst = min(plays, key=lambda x: x["onTime"])
    print(name, len(plays), "plays", len({x["seed"] for x in plays}), "weeks", sum(x["ranked"] for x in plays), "ranked",
          "mean %.0f" % (sum(x["margin"] for x in plays) / len(plays)),
          "on time %.4f" % (sum(x["onTime"] for x in plays) / len(plays)), "worst %.4f" % worst["onTime"], worst["seed"])
```
