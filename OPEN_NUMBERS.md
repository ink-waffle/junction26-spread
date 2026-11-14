# Open numbers — every placeholder, and what fills it

For Sunday morning. Work from the main checkout. `<POLICY>` is the policy that plays the final; on Saturday 12:35 that was `{"fleet": {"early_look": 6}}` on commit `07c8f21`.

```sh
cd /Users/ink_waffle/OverengineeringLife/Junction2026/spread
export SPREAD_SHARED=$PWD; set -a; . ./.env; set +a; PY=.venv/bin/python
vm() { ssh -i ~/.ssh/verda_junction -o BatchMode=yes root@95.133.254.35 "$@"; }
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

## 1. Results (cannot be known before Sunday)

| Placeholder | Where | What fills it |
|---|---|---|
| `[FINAL: € … margin, … % on time, … orders, place … of …]` | PRESENTATION slide 1, README, SPEAKER_NOTES slide 1 | Margin, on-time share and orders: the last lines of the desk's log, `vm 'grep -E "^End|Ranked" /data/spread/repo/final.log \| tail -n 2'` (on the laptop: `final.log` in the checkout). Place: the leaderboard at https://spread.bahnexpress.com. |
| `[BEST ROUND: …]` | PRESENTATION slide 1 and slide 8 table, SPEAKER_NOTES slide 1 | `rounds` prints every round we played; take the best. Today: Saturday 12:00, €82,785 for five weeks (€16,557 a week), on time 94.2–96.9%, 5 of 5 ranked, commit `07c8f21`, `{"fleet": {"early_look": 6}}`. Our place, the top, the 10th, House best and House starter of that round: the leaderboard (not saved anywhere; write them down when you look). |
| `[TEST FINAL 14:00: …]`, `[TEST FINAL 20:00: …]` | PRESENTATION slide 8 | After each test final: `vm 'grep -E "^End|Ranked|joined" /data/spread/repo/final.log \| tail -n 3'` for margin, on-time and orders; the last hour line before `End` has `N of M requests quoted` and `slowest turn`. Note any `No desk for` line: it is a restart. |
| Submission hash | Junction form (not in the deck) | https://spread.bahnexpress.com/team |

## 2. Numbers that move if the final's commit or policy changes

Each needs practice worlds. The team has 8 slots; one harness call on 8 seeds takes 3–4 minutes.

| Number (today's value) | Where | Command |
|---|---|---|
| Tune: €16,838 a week, worst week 94.7%, mean 95.4%, 8 of 8, 438 orders, fee 0.94 × typical, price 1.42 × list | slides 1, 2, 6, 8; README; Appendix A and B | Saved: `weeks main-m9-look6-ot96` (the same numbers again on `07c8f21`: `weeks fleet2-base-look6`). New: `$PY -m tools.harness --tag final-tune --seeds tune --policy '<POLICY>'`, then its last line, or `weeks final-tune`. Fee and price: columns `fee x`, `price x` of the harness lines, `grep -E "^halal" runs/final-tune.out`. |
| Hold: €14,588 a week, worst week 92.2%, mean 93.7%, 4 of 4 (4 of 8 played) | slides 1, 6, 8; Appendix A | Saved: `weeks main-m9-look6-ot96-hold`. The 4 missing weeks: `$PY -m tools.harness --tag main-m9-look6-ot96-hold --seeds halal-09,halal-10,halal-13,halal-16 --policy '{"fleet": {"early_look": 6, "on_time": 0.96}}'`, then `weeks main-m9-look6-ot96-hold` again. For a new commit: `--tag final-hold --seeds hold`. |
| Wide: €12,619 a week, worst week 91.5%, mean 95.1%, 14 of 14 (14 of 16 played) | slides 1, 8; Appendix A | Saved: `weeks main-m9-look6-ot96-wide`. Missing: `--seeds halal-18,halal-25` with the same tag and policy. For a new commit: `--tag final-wide --seeds wide` (about 8 minutes). |
| "€13,057 a week on 18 weeks never fitted on", "26 of 26 ranked", "22% less than tune", "3 points lower" | slides 1, 8; README; SPEAKER_NOTES slide 8 | Arithmetic on the two lines above: (hold sum + wide sum) ÷ weeks; tune against it. `weeks final-hold final-wide` prints both means and counts. |
| Second look on hold: €13,016 → €14,588, worst week 93.7% → 92.2% (seeds 11, 12, 14, 15) | slide 6; SPEAKER_NOTES slide 6 | `weeks offers-mh-board96 main-m9-look6-ot96-hold` and compare the seeds both have. With all 8 hold weeks played the pair is 8 against 8. |
| 26% of cars in a two-car gig at 0.80 × typical, 99.3% on time; never paired 0.97 ×, 93.5% | slide 6; SPEAKER_NOTES slide 6 | `$PY -m tools.offers_study paired main-m9-look6-ot96` (or the new tune tag). Reads saved weeks only. |
| 1,785 lines, 10 modules | slide 1; README; SPEAKER_NOTES | `wc -l dispatch/*.py \| tail -n 1`; `ls dispatch/*.py` less `__init__.py` and `__main__.py`. |
| Appendix A (every week) | PRESENTATION | `weeks final-tune final-hold final-wide`; ranking round rows: `cat runs/board.jsonl`. |
| The override `{"fleet": {"early_look": 6}}` in the run commands | README "Run it"; PRESENTATION header | `grep -n "early_look" dispatch/fleet.py`: if the default is no longer `0.0`, drop the override from the README and the header. If the final runs without the second look, slide 6 (a) describes something the final did not do: cut it or say so. |

## 3. Numbers that were never measured, or only on an older system

| Placeholder | Where | Command | Cost |
|---|---|---|---|
| Kit starter on our own seeds (today only `spread-1`: −€72,613, 45.5%, from `kit/HANDBOOK.md`) | slides 1, 2, 8; README; SPEAKER_NOTES slide 2 | `for i in 01 02 03 04 05 06 07 08; do .venv/bin/spread-starter --level 8 --seed halal-$i \| tail -n 2; done`. It runs outside the harness's slot lock: start it only when no harness is running. Then slide 2 can say "on the same 8 weeks". | 8 × 2 minutes, one slot |
| The starter's median booked fee by weekday (Mon 1.0, Tue–Thu 1.5, Fri 2.5 × typical), 186 Monday bookings, €118.6k fees | slide 2 figure | From the starter's reveal of `spread-1` in `reveal-w7b05a9e2208ac23c76f8/` (CSV export of the kit: `.venv/bin/spread-reveal-csv <world>`). The numbers are in `NIGHT_LOG.md` idea 1 and `RESEARCH.md`; the script that made them is not in the repository. | none |
| Restart test with the final's policy (today: `07c8f21`, default policy, halal-02: 12 of 12, €20,151.83 both ways, `runs/restart-main-m10.out`; `ae60d61`, halal-09: 11 of 12) | slide 8; SPEAKER_NOTES slide 8 | `$PY -m tools.harness --tag final-tune --seeds halal-02 --policy '<POLICY>'` (the baseline), then `$PY -m tools.restart_test --seed halal-02 --restarts 12 --policy '<POLICY>' --baseline final-tune`. Last three lines: `N/12 restarts rebuilt the same desk`, margin with and without. Repeat with `--seed halal-09` to see whether the one differing restart is gone; its differences are printed per restart. | 5 minutes each |
| Rehearsals on the final commit (today's numbers are Saturday morning's system) | slide 8; SPEAKER_NOTES slide 8 | The cloud machine at the real clock from Thursday with one kill: `$PY -m tools.rehearse_remote --commit <commit> --seed halal-03 --speed 1 --start 4320 --kill 4980`. A whole week at 4 ×: `… --seed halal-01 --speed 4 --kill 2100`. Local with trouble: `$PY -m tools.rehearse --tag live-check --seeds halal-01 --speed 4 --until 1440 --trouble kill:2,dead:1,cut:1,fail:1`. Each prints `unquoted`, the milliseconds of a quote, margin and on-time. Not between 14:00–14:20 or 20:00–20:20. | 19 / 9 / 5 minutes |
| Round trip to the server (10 ms from the cloud machine, 40–70 ms from the laptop) | slide 8 | `vm 'cd /data/spread/repo && set -a && . ./.env && set +a && PYTHONPATH=kit/python:. python3 -m tools.rtt'` | seconds |
| `[UPDATE if traced]`: the one restart of 12 on halal-09 that was not identical | SPEAKER_NOTES slide 8 | The restart test above with `--seed halal-09 --show 20` prints the differing objects. | 5 minutes |
| `[FILL IN …]`: what the two of you did yourselves | SPEAKER_NOTES, "How much of this was written by agents?" | Only you know. Facts you can cite: `git log --format=%b \| grep -c Co-Authored-By` gives 76 of `git rev-list --count HEAD` = 78 commits (Saturday 12:25); recount on Sunday. | — |

## 4. Numbers that are final, with the command that reprints them

No practice worlds needed; all read `runs/`.

| Number | Command |
|---|---|
| Any before/after pair on a slide (margin, worst on-time, ranked, orders of a tag) | `weeks <tag-before> <tag-after>`; or `grep '"tag": "<tag>"' runs/log.jsonl` |
| Bisection: 10,181 options, 5,581 requests, 24 worlds, 87.7% within 3%, median bracket 0.5%; sd 8.2% inside a lane; 98.1% of 2,397 menus; €14.5 and €6.1 for speed; trust +0.9% per order; competitor −4% per unit of share; r = 0.38 lanes, 0.01 dealers | `$PY -m tools.probe_read` |
| Notes: 22,099 of 22,099; 6,152 facts | `$PY -m tools.notes_eval --tag notes-label,notes-val1,notes-val2` |
| Notes on hold: 3,539 of 3,539 | `$PY -m tools.notes_eval --tag notes-label-hold` |
| Notes with one more typo: 99.69% | `$PY -m tools.notes_eval --tag notes-label,notes-val1,notes-val2 --typos` |
| The real note of slide 7 | World `halal-03`, request arrived Friday 09:46: `$PY -c "from dispatch import notes; print(notes.read({'text': 'Liike auki arkisin klo 7-20. Huolto kesken, valmis klo 15, ei kun klo 14. Lisäksi 4 kesärengasta tavaratilassa'}, 4*1440+586))"` gives ready at minute 6600 (Friday 14:00), pickup open 420–1200 (07:00–20:00), no tyre flag. |
| Direct offers: 75,390 offers, 85 yes; by fee and driver class | `$PY -m tools.offers_study offers offers-x2` and `… offers offers-x1` |
| Two-car gigs against the same cars as two gigs (0.89 × against 1.21 ×; 85% booked; 29% over 6 hours) | `$PY -m tools.offers_study shared offers-x3` |
| A new car with a car that sits (0.70 × → 46%, 0.85 × → 76% delivered as a pair) | `$PY -m tools.offers_study board offers-mx3` |
| Loss audit tables (26 orders a week reach the warning after a median 70 hours; 52% late) | `$PY -m tools.audit main-m4-r0.0` |
| On-time model against outcomes (6.6% late against 7.5% predicted) | `$PY -m tools.fleet_fit --calibrate main-m7-r-0.15 main-m6` |
| Dealer model out of world (log-likelihood −0.3672 with the place prior) | `$PY -m tools.winmodel cv explore1 market-r30 market-r15 main-m4-r0.15 market-z0` |

## 5. Numbers on the slides that no command in the repository reprints

Say them as measured once, or cut them. They come from the agents' progress lines (`runs/reports/progress.md`) and reports; the scripts were scratch files.

| Number | Slide | Source |
|---|---|---|
| "96% on time when booked before the deadline warning, 25% when not"; the six-point supply curve (39 / 61 / 81 / 91 / 88 / 91%) | 3 | `RESEARCH.md`, from `explore1`. Can be recomputed from `tools.study.table("explore1")`, but no tool prints it. |
| Monday replay in euros: €2,103 (our learner), €2,065 (oracle of lane levels), €3,723 (oracle of thresholds) | 5 | progress line 11:02 and `reports/market.md`. The replay script is not in `tools/`. |
| The day's part is within 5% of its end-of-day value by 10:00 | 4 | `reports/market.md` |
| Drivers and the second look: bookings within 15 minutes, Monday to Friday, with and without | 9 | progress line 11:45 (fleet) |
| The second look raises 31% of gigs | SPEAKER_NOTES slide 2 | progress line 11:45 (fleet) |
| Calibration on its own weeks: 10.3% predicted, 6.0% late; 9.0% after the refit | 9; SPEAKER_NOTES slide 3 | progress lines 11:15 and 11:25 (fleet) |
| The faster option costs a median 0.33 × list more (0.48 × before the barrier price) | 9; SPEAKER_NOTES | `reports/market.md`, progress line 10:55 |
| Restart without a journal costs 2–4% | 9; SPEAKER_NOTES slide 8 | `reports/live.md`; two measurements on older systems. Rerun: `$PY -m tools.restart_test --seed halal-01 --restarts 12 --no-journal --policy '<POLICY>' --baseline final-tune`. |
| The Thursday join sold at 1.56 × list against 1.90 × | 9 | `RUNBOOK.md`, `reports/live.md` |
| Saturday 09:00 round: place 35 of 45, top €79,003, 10th €69,979, House best €50,660 | 8 | `NIGHT_LOG.md`, read from the leaderboard at 10:45 |

## 6. Where the log and the code disagree (the deck follows the code and the saved runs)

Checked on Saturday 12:45 against commit `07c8f21`.

| The log says | The code or the saved run says | What the deck does |
|---|---|---|
| `NIGHT_LOG.md` idea 11: a gig with no driver after six hours has its fee chosen again. | `FleetPolicy.early_look` defaults to `0.0`: off. It runs only with `--policy '{"fleet": {"early_look": 6}}'`. Default policy on tune: €14,937 (`main-m10`); with the override: €16,838 (`fleet2-base-look6`). `RUNBOOK.md` starts `final.sh` without a policy. | Describes the override as the configuration, and says so in the header. **Start the final with the policy, or change the default.** |
| `NIGHT_LOG.md` idea 1: "The fee changes at most once, at the deadline warning." | `Fleet.looked`: the fee is chosen again after six hours (with the override), on the last day before the last possible pickup, at the deadline warning, and when a driver is lost. | Slide 2 names the four moments. |
| `NIGHT_LOG.md` idea 3, `AUDIT.md`: a decline is a quote of 4 × list. | `market.DECLINE = 10.0`. | Slide 4 says 10 × list. |
| `NIGHT_LOG.md` idea 4: the level's parts are world, day, dealer, pickup place, delivery place. | `prior.SPREAD` also has the lane and the pickup place today. | Slide 4 lists seven parts. |
| `NIGHT_LOG.md` idea 5: the model knows who lives near pickup and delivery and private stops; the price rises once expected late orders pass 5%; average fee 1.16 → 0.95 × typical. | `fleet.ON_TIME` has drivers near the delivery only and no sign for a private stop; the target is 96%, so 4%; the saved runs give fee 1.17 × (`base1`) → 1.08 × (`fleet-v3`). 0.95 × is the merged system (`main-m4-r0.3`). | Slide 3 uses 4% and 1.17 → 1.08. |
| `RESEARCH.md`, `NIGHT_LOG.md`: 5,516 options known to 0.5%; sd 0.176 / 0.128 / 0.084; 2,291 menus. | `python -m tools.probe_read` today: 10,181 options, 87.7% within 3%, median bracket 0.5%; sd 0.155 / 0.126 / 0.082; 2,397 menus. The older figures are snapshots at 7 and 15 seeds. | Slide 5 uses the tool's output. |
| `NIGHT_LOG.md`: the Monday replay (€2,103 / €2,065 / €3,723) is "on 24 seeds". | The progress line of 11:02 and `reports/market.md`: the replay ran on 7 tune worlds. `RESEARCH.md` mixes it with the 8-world run (€2,032). | Slide 5 says 7 tune worlds. |
| Reserve 0 on tune: €12,711 (`NIGHT_LOG.md`, `AUDIT.md`) and €12,707 (`reports/market.md`). | Two runs: `main-m4-r0.0` €12,711, `market-z0` €12,707. | Uses `main-m4-r0.0`. |
| `OVERVIEW.md`: the starter makes −€72,612 at 44% on time. | `kit/HANDBOOK.md`: −€72,612.51, 45.5%. | −€72,613, 45.5%. |
| `NIGHT_LOG.md` status 12:25: 11 of 16 wide weeks, €12,680, worst 92.5%; "restart test fails since the refit". | Saved: 14 of 16 wide weeks, €12,619, worst 91.5% (halal-30). Restart: 11 of 12 on halal-09 (`ae60d61`), 12 of 12 on halal-02 (`runs/restart-main-m10.out`), the week identical both times. | Slide 8 uses the saved runs. |
| `RESEARCH.md` (Saturday 00:00 round): House best €72k, 10th €58.5k. `NIGHT_LOG.md` (09:00 round): House best €50,660, 10th €69,979. | Different secret weeks; neither is saved anywhere but in these two files. | Slide 8 quotes the 09:00 round only. Read House best again from the leaderboard before you say it. |
