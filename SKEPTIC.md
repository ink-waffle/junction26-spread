# The skeptic's audit (Saturday 19:20–, branch `research/skeptic`)

The question: is the system fitted to its own weeks, and which of its parts carry the result on weeks nobody has seen?
Read with fresh eyes from `main` 832baf6 (decisions frozen at 52aaf93). Everything below can be printed again:

```sh
python -m tools.skeptic_fit orch-base-s14 -- final-fresh skeptic-base-s14   # the on-time model against 64 weeks it never saw
python -m tools.skeptic_market final-fresh skeptic-base-s14                 # the dealer side, each part taken out, on the same 64 weeks
python -m tools.ablations skeptic-base skeptic-nolook ...                   # the table of section 4 (weeks halal-65..96, strides 12 to 15)
python -m tools.weekdays skeptic-base skeptic-candAcalnw ...                # orders by weekday, the share sold on the fastest option
```

The saved weeks are in `runs/skeptic-*` (tags as in the table's last column of names). The tools of the two fitted models read `main`'s code as it was (`tools.skeptic_fit` has the 16 weights of 832baf6 only when run from that tree or from `research/skeptic-switches`; on this branch it reports the 15 that are left).

## 0. Report for the orchestrator

**State at 21:40.** The audit is done (sections 1–3). Every part has a sample on halal-65..96, the deciding rows two to four (section 4). The simplified system is clean code at the head of this branch and has its proofs (section 5).

**Recommendation: play the simplified system, `research/skeptic` with `dispatch/` as of commit af4fd92** (later commits on the branch touch documents and tools only). It is `main` with four things deleted (the week's learned intercept of the on-time model, the `known` sign, the dealer part and the pickup-today part of the level: 1,948 → 1,900 lines, 16 → 15 weights, 7 → 5 parts, 3 hand-set numbers fewer) and two numbers changed (the on-time model's intercept, set where 64 weeks the fit never saw put it; the target, 97% → 97.5%).

| Against `main`, same weeks, paired per week | margin a week (se) | on time, points (se) | worst play (main's) | unranked |
|---|---|---|---|---|
| **the head (target 97.5%)**: halal-65..96, two samples a side | **+€679 (206)** | **+0.52 (0.11)** | 94.8% (92.8%) | 0 of 64 |
| **the head**: halal-97..128, played once as the confirmation (stride 14) | **+€395 (264)** | **+0.21 (0.16)** | 93.2% (94.5%) | 0 of 32 |
| **the head**: halal-97..128 without strides, as the final is played (`main` €15,829 → €16,266) | **+€437** | **+0.2** (96.2% → 96.4%) | 94.1% (94.3%) | 0 of 32 |
| **the head**: the 8 hold weeks, four samples a side (7 of 8 weeks up; the known hard week halal-09 94.6% → 94.5%) | **+€694 (142)** | **+0.03 (0.16)** | 93.5% (93.2%) | 0 of 32 |
| **the head**: the 24 tune and wide weeks, once (stride 14, against `orch-base-s14`) | **+€625 (331)** | **+0.43 (0.18)** | 94.5% (93.4%) | 0 of 24 |
| **the head, all 96 weeks** (weeks as weights) | **about +€580** | **about +0.36** | 93.2% | 0 of 184 plays |
| dce27f9 (the same system at 97%): halal-65..96, four samples a side | +€959 (166) | −0.27 (0.09) | 92.7% (92.8%) | 0 of 128 |
| dce27f9: halal-97..128, once | +€678 (267) | −0.28 (0.20) | 92.2% (94.5%) | 0 of 32 |
| dce27f9: the 8 hold weeks, four samples a side | +€805 (421) | −0.79 (0.27) | 93.2% (93.2%) | 0 of 32 |
| dce27f9: the 24 tune and wide weeks, two samples | +€548 (248) | −0.53 (0.16) | 93.9% (93.4%) | 0 of 48 |

- **Why the head and not dce27f9:** at 97.5% the simplified system earns more than `main` *and* is on time more often on both untouched sets; at 97% it earns about €280 more still and runs 0.3 to 0.8 point under `main`'s on-time. The first needs no judgement about risk; the second is there, fully proven, if the margin is wanted.
- **What it costs if I am wrong:** the head has 184 plays (128 of them on the 64 untouched weeks) against more than three hundred saved plays of the frozen system, and it was built in one evening; its worst week so far is 93.2%. `main` as frozen at 52aaf93 remains safe: nothing in the audit says otherwise (176 saved plays, worst 92.8%).
- **Proofs** (section 5): restart test 8 of 8 and the same week to the cent on both trees; Python 3.9 `ast` check and import; the clean code plays halal-65..96 to the cent like the switch combination it was measured as.
- The verdict in five lines: section 1. The inventory: 129 numbers and one vocabulary (section 3). The ablation table: section 4. What was deleted and what it costs: section 5.

## 1. Verdict

1. **The level is not overfitted; the headline number is.** The frozen system earns €14,360 a week on 32 fresh weeks (halal-33..64, played once) and €15,208 on 32 more that nobody had touched (halal-65..96, two samples each): 96 of 96 week-plays ranked, on time 96.3% in the mean, 92.8% in the worst. The €17,846 of the tune weeks is 8 rich worlds: a world's margin has a spread (sd) of €4,000, so the mean of 8 worlds strays by €1,400, and tune was already 10–19% above hold for the simple systems of Saturday morning. **Quote €14–15k, never €17.8k.**
2. **What the later ideas gained, they gained off the tune weeks too.** From ideas 1–10 to the frozen system: +€2,858 a week on tune (se 644) and +€2,635 on hold (se 512). The ratio final / early is the same per week on both sets (1.19 against 1.25). Against the House's best on ranking rounds, whose weeks no one tunes on: 0.96 × at 09:00 (ideas 1–7), 1.07 × at 12:00, 1.28 × at 15:00, 1.29 × at 18:00.
3. **The fitted parts mostly hold on weeks they never saw, with three exceptions.** On 64 unseen weeks the dealer side loses predictive power without its place table (64 of 64 weeks), its lane part (63), its event weighting (55) and trust (63); the driver side's large signs (fee, room, lane length, queue, pay, premium, flu) come back with the same sign and within reach of the baked weight. The exceptions: **`known`** has the wrong sign on unseen weeks (baked +0.25, they say −0.17 ± 0.06; the model is better without it); **the two supply signs** are real but baked twice too large (0.75 and 0.71 against 0.31 ± 0.04 and 0.34 ± 0.05: fitted on the rosters of 8 worlds); **the pickup-today and dealer parts** of the level predict nothing (+1.2 and −0.3 per mille of log-likelihood).
4. **The one real misfit: the model's level is wrong by a factor of two, and the part that mended it was the one with the least evidence.** On unseen weeks the on-time model says 10.0% late and 4.8% are. As baked it foretells worse than a constant (log-likelihood −0.1960 against −0.1928); with one intercept free it is good (−0.1754). `Fleet.learned` found that intercept again every week (+0.88 where it may move by 1), slowly, behind a hand-set prior (`DOUBT`) and a hand-set clamp: so Monday was priced as twice as risky as Wednesday and sold 72 orders against 89–92. Setting the level once and deleting the learner earns €700–950 a week more on 96 weeks, 64 of them never played before, for a quarter point of on-time (section 5).
5. **Where the evidence was thin, and what the untouched weeks said (section 4):** the six-hour look, the pairs, the pickup-side signs and the harm term, each measured in sample only or inside noise before, are all confirmed at 3 to 7 standard errors. Idea 14 (the flu) is the same +0.2 to +0.4 point of on-time on a third set of weeks, still under 2 se each time. Idea 13 (the events) is −€295 (se 201) without it in play and solid in the replay. The numbers set by hand that remain (`GRIP`, `CALM`, the cap of the late price, the two-car fees, `RETRY`, `MIN_SPAN`, the 30 minutes of `rung`, `SURE`) have no measurement of their own; the barrier they shape is what keeps the floor (a flat price of a late order leaves a week at 90.3% or most weeks unranked).

**What could hurt in a week unlike ours.** (a) The floor: the worst of 96 unseen plays is 92.8%, the mean 96.3%, sd 1.0 point, and the hard week is known (the flu on a Friday in the capital region: 92–94%); a week under 90% would need a world outside everything in 120 worlds, not bad luck. (b) A note in words the grammar has not seen is missed silently: on the 64 unseen weeks the reader left 0.22–0.25 failed visits a week (the kit's reader: 10.6), so the vocabulary held. (c) The events are weighed as the rules state them (one war day, one outage day, never both): a week that breaks the rule costs little by the team's own replay (−€2 to +€118). (d) The 60 numbers of the place table and the supply signs describe *our* Finland: the map and the rosters are the same in every world we played, and the final is the same simulator; on another map both would have to go, and the system would still run (section 4: what it earns without them). (e) With the learner gone (candidate B), a week whose drivers are much scarcer than in any of ours is braked by the barrier alone, which counts late orders as they show; on the hardest third of the untouched weeks B loses 0.36 point of on-time and on the poorest hold week 2.4 points (96.8% → 94.4%).

## 2. The generalisation gap in what was already saved

A week's margin, same commit, by set of weeks (from `runs/log.jsonl`):

| System | tune (01–08) | hold (09–16) | wide (17–32) | fresh (33–64) | untouched (65–96) |
|---|---|---|---|---|---|
| kit starter | −€63,232 | −€68,908 | | | |
| ideas 1–7 / 1–8 (Sat 10:40) | €12,711 / €13,512 | €11,487 (0.90 / 0.85 of tune) | | | |
| ideas 1–10 (11:14) | €14,987 | €12,170 (0.81) | | | |
| ideas 1–11, stride 14 | €16,277 | €13,472 (0.83) | €13,240 (0.81) | | |
| ideas 1–12, stride 14 | €17,421 | €13,753 (0.79) | €13,201 (0.76) | | |
| frozen, no stride | €17,846 | €14,806 (0.83) | | €14,360 (0.80) | |
| frozen, strides 14 / 13 | €17,620 / €18,070 | €14,898 / €14,497 (strides 12 / 13) | €13,418 / €13,730 (0.76) | | €15,359 / €15,057 (0.85) |

- The tune worlds were richer before anything was fitted to them: hold earned 0.85–0.90 of tune with ideas 1–8, and earns 0.83 now. Between the 88 weeks that are not tune, set means run from €13.4k to €15.4k: that is the spread of worlds (sd €4,000 a world, so ±€700 for 32 worlds and ±€1,400 for 8), not fit.
- Of tune's €17.8k against fresh's €14.4k, then: at least €2.0–2.7k is the worlds (the ratio that ideas 1–8 already showed), and at most about €1k can be fit. The paired check says the same: tune gained +€223 a week (se 823) more than hold from ideas 1–10 to the end. A fit of the size of the headline gap (€3.4k) is excluded; a fit of a few hundred euros is neither shown nor excluded.
- Two plays of one world differ by €680–1,020 (sd of one play) and 0.6–0.8 point of on-time; the mean of 32 weeks moves by €250 between strides 14 and 13. A difference under €500 on 8 weeks played once is noise, as the night log says; several decisions of Saturday morning were made on exactly that.

Each idea, in sample and out:

| Idea | On the weeks it was built on | On other weeks | Standing |
|---|---|---|---|
| 1 flat fee, 2 above list | starter −€63k on tune | starter −€69k on hold | solid (structural) |
| 4 learn the level | tune €6,824 → €10,367 | not played alone; the learner foretells answers on 64 unseen weeks far better than a fixed level (−0.468 against −1.445) | solid |
| 5 on-time model, fee + risk | tune €6,824 → €9,613 | not played alone | section 3 |
| 6 note reader | 22,099 of 22,099 notes | hold 3,539 of 3,539; 0.2 failed visits a week on 64 unseen weeks | solid |
| 7 no reserve | tune +€2,431 | hold played at 0 only | plausible, unmeasured out of sample |
| 8 every option | tune +€784 | hold +€1,375 (5 of 8 up) | confirmed |
| 8 lane and pickup-today parts | tune +€1,064 | hold +€89 | **tune only** in play; the lane part does foretell unseen answers (63 of 64 weeks), pickup-today does not |
| 9 two-car gigs | tune +€433 (8 weeks, once) | none | **thin** |
| 10 refit, barrier, world intercept | tune +€1,203 | hold +€683, worst week 91.3% | partly confirmed |
| 11 six-hour look | tune +€1,900 | no clean pair on hold or wide | **in sample only** until section 4 |
| 11 board pairs | tune +€895 | hold +€1,215, one hold week unranked at the target of then (95%) | confirmed, at a cost in on-time |
| 12 pickup-side signs, 97% | tune +€1,144 | wide −€39 with +0.9 point on time; hold +€281 with +1.8 points | **margin: tune only**; on time: confirmed |
| 13 the week's events | replay +€202 (se 66) on 24 weeks | the 4 weeks probed after the design: +€19; played +€335 on wide (se 427) | replay only; it foretells unseen answers better (49 of 64 weeks) |
| 14 the flu | 25 weeks: on time +0.38 (se 0.20), margin −€23 (se 232) | hold, 3 samples: on time +0.30 (se 0.26), margin −€252 (se 209) | **under 2 se both times** |

## 3. Inventory of everything fitted or set by hand in `dispatch/`

129 numbers and one vocabulary: 91 come out of a fitting tool (60 of them are the place table), 38 are set by hand. Every fit used the 8 tune worlds only, except the flu's three numbers and the day spread (tune + wide).

| Where | What | Value | How obtained | On which weeks | Checked on other weeks? |
|---|---|---|---|---|---|
| `fleet.ON_TIME` (10) | one, fee, level, slack, short, long, trade_in, backlog, known, waited | −5.75, 3.96, 0.88, 1.13, −1.85, −0.44, −3.35, −0.58, 0.25, −0.75 | `tools.fleet_fit` (logistic; `waited` on later looks) | tune, 10 tags of random and one-fee weeks | hold/wide only through the whole system. On 64 unseen weeks (below): fee, slack, long, backlog hold; `known` reverses; short, trade_in, waited undecided (we win almost none) |
| `fleet.ON_TIME` (5) | supply_pickup, supply_delivery, private_delivery, premium, pay | 0.75, 0.71, −0.75, −0.82, 1.97 | `fleet_fit --add`, rest held, mean chance kept | tune, 5 tags | wide/hold: on time up, margin flat. Unseen weeks: pay, premium, private delivery hold; both supply weights half the baked size |
| `fleet.ON_TIME` (1) | flu | −2.6 | `fleet_fit --add flu` | 48 weeks, tune + wide | unseen weeks give −3.07 ± 0.65 |
| `fleet` | BOOKED_LATE, REFUND | 0.030, 0.54 | `fleet_fit` | tune | no |
| `fleet` | SICK, WELL | 0.33, 0.03 | `tools.night_study` | 24 tune + wide | no |
| `fleet`, by hand (7) | DOUBT, GRIP, CALM, KNOWN, LAST_DAY, cap of the late price, clamp of the world's intercept | 4, 4, 20, 100, 1 day, 2 ×, ±1 logit | tried on tune; LAST_DAY has `late_study` behind it | tune | **no**; "no learning of the intercept" was judged on one week (halal-02) |
| `fleet`, shapes of signs (5) | short under 40 km; long between 100 and 800 km; waited capped at 1 h; supply kernel (1 + km/30)⁻² | | by hand | tune | no |
| `FleetPolicy` (10) | fees 0.85–1.5 (5), urgent 1.6, late 1.3, on_time 0.97, late_price €300, early_look 6 h | | by hand, then bracketed | fees, target, look: 24 tune + wide weeks × 2 samples a side | target chosen after a look at hold; the look at 12 h gave −€342 in one bracket and +€447 in another: **inside noise**. urgent, late fee, €300: tune only |
| `prior.py` (11) | SLOPE, SPEED, TRUST, LEVEL; SPREAD of 7 parts | 11.92, 0.085, 0.0105, 0.322; 0.022–0.07 | `tools.winmodel fit`; day 0.059 from `probe_week` | tune (5 tags); day: 24 tune + wide | `winmodel cv` leaves each tune world out. Lane 0.07 and pickup-today 0.04: **tune +€1,064, hold +€89** |
| `prior.PLACES` (60) | a level per pickup and per delivery place | −0.15 … +0.10 | `tools.winmodel fit` | tune | cross-world r = 0.39 through the delivery place; on 64 unseen weeks it improves the forecast of answers in 64 of 64 |
| `market`, by hand (3) | SURE, DECLINE, the price grid 0.80–3.50 | 200, 10 ×, 0.01 | by hand | | no measurement (none needed for DECLINE and the grid) |
| `market`, the rules | WAR −20%, OUTAGE +30%, 80 km, 08–18, 5 days | | the challenge's rules, confirmed by `probe_week` | 24 tune + wide | exact replay; not counted as fitted |
| `PairsPolicy` (7) | hold 30 min, fee 0.70, board 0.85, drive 5 h, patience 60, lead 3 h, idle 1 h | | `tools.offers_study` (randomised) then by hand | tune; hold and drive bracketed on 24 weeks | **idea 9 itself: +€433 on 8 tune weeks, once**; board pairs dropped a hold week to 89.7% at the old target |
| `timetable` (5) | SLOW_DRIVE 15%, RETRY 2 h, MIN_SPAN 1 h, noon in `facts`, 30 min in `rung` | | `drive_times` (first), by hand (rest) | tune | no |
| `desk` (1) | four refusals | 4 | by hand | | no |
| `notes` | the vocabulary (cues in three languages), one typo in six letters | | `tools.label`, `tools.notes_eval` | 50 labelled weeks | hold 3,539 of 3,539; 0.2 failed visits a week on unseen weeks |

**Resting on one 8-week comparison inside its noise (±€400–500), or on none:** the two-car gig's fees and limits; the lane and pickup-today spreads; `known`/`KNOWN` (one tune run, €16,802 against €17,421); `waited`; `DOUBT` and the clamp; `GRIP`, `CALM`, the cap; `urgent_fee`, `late_fee`; `RETRY`, `MIN_SPAN`, the 30 minutes; `SURE`.

### The on-time model against 64 weeks it never saw

`python -m tools.skeptic_fit orch-base-s14 -- final-fresh skeptic-base-s14`: 14,746 orders of halal-33..96 as the frozen system played them; each sign's weight refitted alone with the rest of the model held and the intercept free; standard errors by leaving out one week at a time. "Loss without it" is the log-likelihood the model loses on these weeks when the sign is dropped (negative: the model is better without).

| Sign | Baked | Unseen weeks say | se | Loss without it |
|---|---|---|---|---|
| fee | 3.96 | 4.10 | 0.40 | 0.0037 |
| level | 0.88 | 2.76 | 0.84 | 0.0003 |
| slack (room) | 1.13 | 1.30 | 0.07 | 0.0218 |
| long | −0.44 | −0.55 | 0.04 | 0.0199 |
| backlog (queue) | −0.58 | −0.96 | 0.08 | 0.0077 |
| pay | 1.97 | 2.71 | 0.42 | 0.0033 |
| premium | −0.82 | −1.45 | 0.20 | 0.0013 |
| flu | −2.60 | −3.07 | 0.65 | 0.0008 |
| private_delivery | −0.75 | −0.71 | 0.22 | 0.0004 |
| short | −1.85 | −0.89 | 0.55 | −0.0001 |
| trade_in | −3.35 | −1.54 | 0.90 | 0.0000 |
| supply_delivery | 0.71 | 0.34 | 0.05 | −0.0006 |
| supply_pickup | 0.75 | 0.31 | 0.04 | −0.0023 |
| known | 0.25 | −0.17 | 0.06 | −0.0025 |
| waited (later looks only) | −0.75 | −2.13 with the intercept free, +0.19 with it held | 0.78 | undecided |

The orders are the ones our own policy chose and paid, so a sign the policy acts on is seen through its own selection (we win one trade-in a week; short lanes are priced out): "undecided" is the honest word for `short`, `trade_in` and `waited`, and the randomised weeks of Saturday morning remain their evidence. Three signs carry almost all of the model's discrimination: room, lane length, queue. As baked the model says 10.0% late where 4.8% are; with its intercept free (+0.88) its log-likelihood goes from −0.1960 to −0.1754 (a constant: −0.1928).

### The dealer side against the same 64 weeks

`python -m tools.skeptic_market final-fresh skeptic-base-s14`: each week replayed through the learner; log-likelihood of a dealer's answer × 1000 under the chance the market gave, as a paired difference to the whole market over weeks.

| Market | Log-likelihood × 1000 | Against the whole | se | Weeks worse |
|---|---|---|---|---|
| as it is | −468.2 | | | |
| no place table | −483.6 | −15.3 | 0.9 | 64 of 64 |
| no lane part | −483.4 | −15.2 | 1.0 | 63 |
| no pickup-today part | −467.0 | **+1.2** | 0.3 | 20 |
| no dealer part | −468.5 | −0.3 | 0.2 | 33 |
| no lane, pickup-today, dealer | −484.2 | −16.0 | 1.2 | 62 |
| no event weighting | −483.8 | −15.5 | 1.8 | 55 |
| the market before idea 13 (day spread 0.125) | −478.9 | −10.7 | 1.6 | 49 |
| no trust | −498.1 | −29.9 | 1.6 | 63 |
| world, day and the events only | −561.1 | −92.9 | 4.9 | 64 |
| world and day only | −585.6 | −117.4 | 5.4 | 64 |
| one fixed level | −1,445.0 | −976.8 | 41.9 | 64 |

The same replay with each fitted number of `prior.py` moved both ways (`--numbers`) says the numbers sit where unseen weeks want them: speed × 0.5 −5.6 and × 1.5 −0.4; trust × 0.5 −6.4 and × 1.5 −10.4; the level −0.05 −1.9 and +0.05 +0.5; the lane spread × 0.5 −7.4 and × 2 −2.4; **the place table × 0.5 −3.6 and × 1.5 −4.7** (se 0.5: its 60 numbers have the right size on weeks they never saw); the day, world, from and to spreads within 3 either way. One exception: the slope a quarter steeper is better in 56 of 64 weeks (+2.6, se 0.3), a fifth flatter worse in 64 (−6.2). The tool printed this table from the tree of 404f62a (`research/skeptic-switches`), which still has the dealer and pickup-today parts.

## 4. Ablations on untouched weeks (halal-65..96)

Weeks halal-65..96 had never been played. Baseline = `main`'s default; one part is removed at a time through a research switch (`research/skeptic-switches`, 404f62a: with every switch at its default the 32 weeks reproduce `main`'s to the cent). A sample is the same seed at one stride (14, 13, and 12 and 15 for the close calls); a variant is set against the baseline's samples of the same strides, the samples of a week are averaged, and the standard error is over the 32 weeks. Minus = the part earns that much. Where a sign of the on-time model is removed, the intercept is moved so that the model's mean chance on the weeks of the fit stays (`known` is set to its end value; the model before idea 12 is the one of that commit). "Margin at equal on time" pays the variant's on-time difference at the price the target sets on these weeks, so a part that only trades on-time for margin shows about zero there. A row with × 1 is a first reading: one sample moves by about ±€250.

<!-- ABLATIONS -->
Baseline `skeptic-base`: 32 weeks, 128 samples: margin EUR 15,259 a week, on time 96.3% (worst sample 92.8%), 412 orders, 15.1 late a week.
A point of on-time costs EUR 512 of margin through the target (`skeptic-t965`: +200 and -0.48 points; `skeptic-t975`: -546 and +0.97).

| Without | weeks × samples | margin (se) | on time, points (se) | margin at equal on time (se) | late orders a week (se) | orders | worst sample | samples < 93.5% | not ranked |
|---|---|---|---|---|---|---|---|---|---|
| **The dealer side** | | | | | | | | | |
| the place table of the prior (60 numbers, all zero) (`places0`) | 32×2 | +146 (222) | +0.11 (0.11) | +202 (223) | -0.8 (0.5) | -6 | 94.5% | 0 | 0 |
| the lane part of the level (`nolane`) | 32×2 | -65 (145) | -0.00 (0.10) | -66 (156) | +0.2 (0.4) | +4 | 93.9% | 0 | 0 |
| the pickup-today part (`nofromtoday`) | 32×1 | -28 (209) | +0.17 (0.15) | +58 (234) | -0.7 (0.6) | +1 | 94.3% | 0 | 0 |
| the dealer part (`nodealer`) | 32×1 | -98 (166) | +0.23 (0.11) | +20 (184) | -1.0 (0.5) | -1 | 94.1% | 0 | 0 |
| the weighting of the week's events (idea 13) (`nosurprises`) | 32×2 | -259 (149) | +0.08 (0.11) | -220 (163) | -0.1 (0.4) | +1 | 93.6% | 0 | 0 |
| quoting every option (one option only) (`oneoption`) | 32×2 | -271 (178) | +0.08 (0.10) | -231 (184) | -0.2 (0.4) | +1 | 93.1% | 1 | 0 |
| **The driver side: the on-time model** | | | | | | | | | |
| the pickup-side signs (the model before idea 12, target still 97%) (`pre12`) | 32×1 | -1,702 (298) | -0.31 (0.23) | -1,862 (281) | -2.3 (0.9) | -83 | 93.6% | 0 | 0 |
| idea 12 whole (the model before it, target 96%) (`pre12t96`) | 32×1 | -592 (249) | -1.58 (0.22) | -1,402 (284) | +5.2 (1.0) | -26 | 92.6% | 7 | 0 |
| the flu sign (idea 14) (`noflu`) | 32×2 | +432 (205) | -0.21 (0.21) | +323 (261) | +1.2 (0.9) | +7 | 90.9% | 3 | 0 |
| `known` (the week's first hundred bookings) (`noknown`) | 32×1 | +200 (232) | +0.20 (0.15) | +300 (241) | -0.6 (0.7) | +6 | 94.1% | 0 | 0 |
| `waited` (an hour in the app) (`nowaited`) | 32×2 | +601 (187) | -0.29 (0.11) | +451 (208) | +2.1 (0.5) | +22 | 93.0% | 1 | 0 |
| `known` and `waited` (`noknownwaited`) | 32×1 | +410 (269) | +0.09 (0.18) | +454 (279) | +0.2 (0.8) | +16 | 94.5% | 0 | 0 |
| the two supply signs (drivers near pickup and delivery) (`nosupply`) | 32×1 | -1,607 (248) | -1.07 (0.25) | -2,155 (281) | +1.1 (1.0) | -67 | 91.7% | 4 | 0 |
| `pay` (typical fee as a share of list) (`nopay`) | 32×1 | -150 (220) | -0.03 (0.15) | -163 (233) | +0.4 (0.6) | +5 | 94.6% | 0 | 0 |
| `premium` (`nopremium`) | 32×1 | -322 (232) | +0.05 (0.13) | -294 (252) | -0.3 (0.6) | -1 | 93.6% | 0 | 0 |
| `private_delivery` (`noprivdel`) | 32×1 | +72 (196) | +0.24 (0.14) | +193 (210) | -1.0 (0.6) | -2 | 94.6% | 0 | 0 |
| `short` (lanes under 40 km) (`noshort`) | 32×1 | +365 (225) | -0.09 (0.17) | +317 (279) | +1.7 (0.7) | +33 | 93.4% | 1 | 0 |
| `trade_in` (`notradein`) | 32×1 | +26 (194) | -0.03 (0.13) | +10 (205) | -0.0 (0.6) | -4 | 94.0% | 0 | 0 |
| `long` (lane length) (`nolong`) | 32×1 | -3,133 (319) | -1.78 (0.29) | -4,046 (390) | +1.4 (0.8) | -97 | 89.1% | 8 | 1 |
| the week's learned intercept (`noworld`) | 32×1 | -505 (228) | +1.16 (0.15) | +90 (243) | -6.1 (0.7) | -48 | 96.0% | 0 | 0 |
| the harm to the cars that wait (`noharm`) | 32×1 | -2,967 (403) | -0.32 (0.20) | -3,131 (436) | +4.2 (0.9) | +73 | 92.8% | 1 | 0 |
| the barrier (a flat EUR 300 a late order) (`flat300`) | 32×1 | +1,498 (232) | -0.96 (0.30) | +1,004 (261) | +4.7 (1.3) | +16 | 90.3% | 4 | 0 |
| the barrier (a flat EUR 100) (`flat100`) | 32×1 | +398 (261) | -7.91 (0.44) | -3,648 (352) | +41.5 (2.3) | +76 | 82.0% | 32 | 24 |
| **The driver side: the rule for the fee** | | | | | | | | | |
| the six-hour look (`nolook`) | 32×1 | -1,394 (278) | +0.02 (0.17) | -1,382 (301) | -3.3 (0.6) | -88 | 93.7% | 0 | 0 |
| the look when a gig's last day begins (`nolastday`) | 32×1 | -403 (181) | -0.01 (0.14) | -410 (198) | -0.8 (0.6) | -19 | 93.6% | 0 | 0 |
| the choice of the fee (every gig at 1.0 x typical) (`onefee`) | 32×1 | -3,005 (521) | -0.44 (0.24) | -3,228 (598) | -3.7 (0.7) | -119 | 91.7% | 2 | 0 |
| **Pairs and notes** | | | | | | | | | |
| two-car gigs (`nopairs`) | 32×1 | -1,444 (286) | +0.65 (0.13) | -1,110 (301) | -3.8 (0.6) | -33 | 94.7% | 0 | 0 |
| pairs with a car that sits in the app (new pairs stay) (`noboard`) | 32×1 | -672 (221) | +0.19 (0.18) | -573 (244) | -1.0 (0.8) | -9 | 93.7% | 0 | 0 |
| the note grammar (the kit's keyword reader instead) (`kitnotes`) | 32×1 | -998 (235) | -0.19 (0.14) | -1,097 (253) | +0.1 (0.5) | -17 | 93.3% | 1 | 0 |
| **The target, for scale (not a part)** | | | | | | | | | |
| target 96.5% instead of 97% (`t965`) | 32×1 | +200 (251) | -0.48 (0.14) | -47 (258) | +2.7 (0.7) | +15 | 93.5% | 1 | 0 |
| target 97.5% (`t975`) | 32×1 | -546 (258) | +0.97 (0.10) | -47 (269) | -4.7 (0.5) | -24 | 95.1% | 0 | 0 |
| **A deliberately small system, and back up** | | | | | | | | | |
| small: model of fee, room, queue only; level = world + day; one fee of 1.0 x, never chosen again; no pairs (`small1`) | 32×1 | -9,153 (440) | -6.51 (0.74) | -12,485 (649) | +1.8 (1.1) | -225 | 77.3% | 27 | 15 |
| the same with the model choosing the fee once (`small`) | 32×1 | -11,322 (453) | -10.50 (0.76) | -16,698 (577) | -0.8 (1.0) | -299 | 78.7% | 32 | 28 |
| + the whole on-time model (`smallM`) | 32×1 | -5,517 (428) | -0.85 (0.21) | -5,953 (455) | -4.6 (0.7) | -170 | 91.3% | 2 | 0 |
| + the looks (six hours, last day) (`smallML`) | 32×1 | -2,411 (356) | +0.66 (0.11) | -2,072 (363) | -4.0 (0.5) | -40 | 94.1% | 0 | 0 |
| + pairs (what is still missing: places, lane and events in the level) (`smallMLP`) | 32×1 | -1,388 (244) | +0.17 (0.16) | -1,303 (248) | -1.2 (0.8) | -15 | 94.5% | 0 | 0 |
| **The start of the week (rows that ADD something to main)** | | | | | | | | | |
| WITH the baked intercept moved by +0.88, the learner as it is (`cal`) | 32×1 | +227 (294) | -0.54 (0.15) | -51 (321) | +4.1 (0.7) | +44 | 93.2% | 1 | 0 |
| WITH the intercept +0.88 and no learned intercept (`calnw`) | 32×2 | +778 (187) | -0.20 (0.11) | +675 (206) | +2.2 (0.5) | +37 | 93.8% | 0 | 0 |
| WITH the learned intercept starting at +0.88 (its limits as they are) (`start88`) | 32×1 | +445 (236) | -0.38 (0.13) | +250 (245) | +2.9 (0.6) | +33 | 94.1% | 0 | 0 |
| WITH the intercept +0.5 and no learned intercept (`cal05nw`) | 32×1 | +483 (228) | +0.30 (0.14) | +639 (243) | -1.2 (0.6) | +2 | 94.8% | 0 | 0 |
| WITH the intercept +0.7 and no learned intercept (`cal07nw`) | 32×1 | +493 (194) | -0.04 (0.16) | +475 (206) | +0.8 (0.8) | +21 | 94.2% | 0 | 0 |
| **Candidates (section 5)** | | | | | | | | | |
| A: without `known`, the dealer part and the pickup-today part (`candA`) | 32×1 | -109 (267) | +0.24 (0.14) | +15 (273) | -0.9 (0.6) | +0 | 94.8% | 0 | 0 |
| **B: A, without the learned intercept, with the model's level moved by +0.88** (dce27f9 plays the same weeks to the cent) (`candAcalnw`) | 32×4 | +959 (166) | -0.27 (0.09) | +819 (180) | +2.6 (0.4) | +40 | 92.7% | 1 | 0 |
| **B at a target of 97.5%: the head of the branch** (af4fd92 plays the same weeks to the cent) (`B975`) | 32×2 | +679 (206) | +0.52 (0.11) | +946 (215) | -1.6 (0.5) | +18 | 94.8% | 0 | 0 |
<!-- /ABLATIONS -->

**How to read it** (the numbers are the table's: rows marked × 1 have one sample, the close calls two, the candidates two to four).

- **Load-bearing, each beyond 2.5 standard errors on weeks it never saw:** the harm to the cars that wait (−€2,967), the pickup-side signs of idea 12 (−€1,702 at the same target; against the whole of idea 12 the old system is −€592 *and* −1.6 points of on-time, with 7 of 32 weeks under 93.5%), two-car gigs (−€1,444, though they cost 0.65 point of on-time), the six-hour look (−€1,394), the note grammar against the kit's keyword reader (−€998), pairs with a car that sits (−€672), the look when the last day begins (−€403, 2.2 se).
- **The barrier is what keeps the floor, not what earns the margin.** A flat €300 a late order earns €1,498 *more* and loses a point of on-time, with one week at 90.3% and four under 93.5%; a flat €100 leaves 24 of 32 weeks unranked. No flat price is safe in every week; the barrier finds each week's price.
- **Parts that trade on-time for margin, as the target does** (a point of on-time costs €512 through the target on these weeks): the week's learned intercept (without it −€505 and +1.16 points, +€90 at equal on-time: the model stays as cautious all week as it is on Monday); the flu sign (two samples: without it +€432, se 205, and −0.21 point, +€323 at equal on-time, but the worst week falls from 92.8% to 90.9% and three plays end under 93.5% for one: the sign is there for the floor, and that is where it shows); `waited` (two samples: without it +€601, se 187, and −0.29 point, se 0.11; +€451, se 208, at equal on-time). **`waited` is the third open candidate for a deletion**: it costs more margin than the on-time it buys is worth at the target's price, and unseen weeks cannot decide its weight (section 3). It was not taken out tonight: the change moves on-time, and the head was not played with it.
- **Nothing measurable in play:** the place table (two samples: +€146 without it, se 222), the lane part (two samples: −€65, se 145), the dealer part (−€98, se 166), the pickup-today part (−€28, se 209), `known` (+€200, se 232: the system earns more without it, 6 more orders on Monday). The events (two samples: −€259, se 149) and the menu of options (−€271, se 178) are each under two standard errors alone. Together the dealer side's parts are worth €1,390 (se 244; the ladder below), and the replay of section 3 can tell them apart where play cannot: the place table, the lane part and the events foretell answers in 64, 63 and 55 of 64 unseen weeks and stay; the dealer and pickup-today parts foretell nothing and are out. The menu has the team's two earlier measurements behind it (+€784 tune, +€1,375 hold).
- **A deliberately small system does not rank, and the way back up says what each part is for** (one sample each, halal-65..96):

| System | margin a week | on time | weeks ranked |
|---|---|---|---|
| small: on-time model of fee, room and queue only; level = world + day; every gig at 1.0 × the typical fee, never chosen again; no pairs | €6,206 | 89.7% | 17 of 32 |
| the same, with that small model choosing the fee once | €4,037 | 85.7% | 4 of 32 |
| + the whole on-time model (lane length, supply, pay, premium, private delivery, trade-in, flu, waited) | €9,842 | 95.3% | 32 of 32 |
| + the looks (six hours, the last day) | €12,948 | 96.9% | 32 |
| + two-car gigs | €13,971 | 96.4% | 32 |
| + the places, the lane and the events in the level = `main` (the same stride) | €15,359 | 96.2% | 32 |
| − the learner, `known`, two parts; the level and the target set on unseen weeks = the head of this branch (the same stride) | €15,914 | 96.8% | 32 |

  The on-time model's car signs are what turns an unranked system into a ranked one (+€5,800 and ten points of on-time); a model without them does worse when it is allowed to choose the fee than when it is not. The looks are worth €3,100, the pairs €1,000, the dealer side's parts together €1,390 (se 244), though no one of them alone passes two standard errors. The two supply signs alone carry €1,607 (se 248) and a point of on-time (their weights are twice what unseen weeks give them, and still the system is far worse without them); choosing the fee at all, against every gig at 1.0 ×, carries €3,005 (se 521).
- **The other weights of the on-time model, one at a time** (the weight set to zero, the intercept moved by the sign's mean on the weeks of the fit; one sample each): lane length −€3,133 (se 319) and 1.8 points, with one week unranked: load-bearing. `premium` −€322 (se 232), `pay` −€150 (se 220), `private_delivery` +€72 (se 196), `trade_in` +€26 (se 194), `short` +€365 (se 225, 33 more orders): none of the five is seen in play. Unseen weeks support `pay`, `premium` and `private_delivery` in the fit (section 3), so they stay; **`short` and `trade_in` are the two open candidates for a deletion that this pass did not make**: one sample is too little, and both guard classes of cars that the randomised weeks of Saturday morning showed to arrive late (trade-ins 17–61% on time).

### The start of the week (asked by the orchestrator at 20:10, after Monday and Tuesday of the 20:00 test final)

On halal-65..96 the frozen system wins 72 / 89 / 89 / 92 / 74 orders from Monday to Friday (`python -m tools.weekdays skeptic-base ...`); Monday is the week's lowest day in 42% of plays, and its spread is wide (sd 28; a Monday of 49 orders or fewer in 22% of plays, so the test final's 49 + 99 is an ordinary start for us, 0.3 sd under the mean). Monday is not sold on slower options: 74% of Monday's orders with a choice go on the fastest option, 52% over the week. Why Monday is thin: the model's pessimism (it says 10% late where 5% are) meets the barrier while the week has few orders. Replaying 16 of the weeks through the fleet (`tools.control_study`): the learned intercept is +0.35 at Monday noon, +0.54 on Monday evening, +0.65 on Tuesday, +0.75 from Thursday (never the +0.88 that the week's end shows); the price of a late order averages €1,325 at Monday noon against €400–900 later, because every car won so far still waits and counts as a tenth of a late order. `known` adds a second Monday penalty of up to 1.15 logits on the first bookings. The ablations of this are the rows "The start of the week" of the table. What they say:

| On halal-65..96, against `main` | margin (se) | on time (se) | orders Mon / Tue / Wed / Thu / Fri | fastest option, week |
|---|---|---|---|---|
| `main` | | | 72 / 89 / 89 / 92 / 74 | 52% |
| the intercept moved by +0.88, the learner as it is | +€227 (294) | −0.54 (0.15) | 91 / 101 / 94 / 97 / 80 | 56% |
| the learner started at +0.88 | +€445 (236) | −0.38 (0.13) | | |
| **the intercept moved by +0.88, no learner** (two samples) | **+€778 (187)** | −0.20 (0.11) | 87 / 97 / 93 / 96 / 80 | 53% |
| no learner, intercept as fitted | −€505 (228) | +1.16 (0.15) | 67 / 76 / 80 / 81 / 65 | 49% |

Monday can be bought back, and it is only worth buying without the learner. With the learner kept on top of a level that is already right, the week wins 44 more orders, earns nothing for them and loses half a point of on-time: the learner counts a booked car as nearly on time before it has arrived, so its number drifts upward (+0.35 by Monday noon on nothing but bookings), and added to a right level that drift is plain risk. The learner was the mend for a fit that said twice the lateness; with the level set right once it has no job left. A week's own outcomes pin its intercept to ±0.35 by Friday while weeks truly differ by 0.28 (64 weeks, the spread of the weekly intercepts less their sampling error), so there was never much to learn within one week.

## 5. The simplest system that is as good

**Rule for a deletion:** on the untouched weeks its removal costs less than about one standard error of margin and no on-time; and where the replay of section 3 can judge the part, it agrees.

| Part | In play (section 4) | On 64 unseen weeks offline (section 3) | Decision |
|---|---|---|---|
| the week's learned intercept (`Fleet.learned`, `outcome`, `forecast`, `gig_posted`, `DOUBT`, the clamp) | alone −€505 with +1.16 points; with the level set right once **+€778 (se 187)** at −0.20 point | the model is off by one intercept, +0.88, the same on the weeks of the fit (+0.86), the fresh weeks (+0.90) and the untouched ones (+0.87) | **out; `ON_TIME["one"]` moves by +0.88** |
| `known`, `KNOWN`, `Queue.known` | +€200 (se 232), +0.20 point, 6 more orders on Monday | opposite sign (baked +0.25, unseen −0.17 ± 0.06) | **out** (its end value, 1.15, goes into the intercept) |
| the dealer part of the level | −€98 (se 166), +0.23 point | −0.3 per mille (se 0.2) | **out** |
| the pickup-today part | −€28 (se 209), +0.17 point | **+1.2** per mille without it (se 0.3) | **out** |
| the place table (60 numbers) | +€146 (se 222), two samples | −15.3 per mille (se 0.9), 64 of 64 weeks; its size is right (× 0.5 and × 1.5 both worse) | stays: play cannot see it, the replay can |
| `waited` | +€601 (se 187) with −0.29 point (se 0.11), two samples | undecided | stays for tonight; **open candidate** (it moves on-time, and the head was not played without it) |
| `short`, `trade_in` | +€365 (se 225), +€26 (se 194), one sample | undecided (we win almost none of these cars) | stay; **open candidates** |
| the flu sign | +€432 (se 205) with −0.21 point, two samples; the worst week 92.8% → 90.9% | −3.07 ± 0.65 (baked −2.6) | stays: it is there for the floor, and without it a week at 90.9% appears |
| the events, the lane part, the menu | −€259 (se 149), −€65 (se 145), −€271 (se 178), two samples each | events 55 of 64 weeks, lane 63 of 64 | stay (with the places they are worth €1,390 together) |
| everything else in the table | 2 to 10 standard errors | | stays |

**The candidate (B)** is `main` with the four deletions of the table and one number changed. As clean code on this branch: `dispatch/` goes from 1,948 to 1,900 lines; the on-time model from 16 weights to 15; the level from 7 parts to 5; the numbers set by hand in `fleet.py` from 7 to 4 (`DOUBT`, `KNOWN` and the clamp are gone); the inventory of section 3 from 129 numbers to 123; the fleet remembers nothing that a restart must rebuild (`Fleet.forecast` and `gig_posted` are gone: its state is the books).

| B against `main`, same weeks, paired per week | margin (se) | on time, points (se) | late orders a week | orders | worst play | plays under 93.5% | unranked |
|---|---|---|---|---|---|---|---|
| halal-65..96, four samples a side (strides 12–15; 128 plays each) | **+€959 (166)** | −0.27 (0.09) | +2.6 (0.4) | +40 | 92.7% (main 92.8%) | 1 | 0 |
| halal-97..128, played once, the confirmation (stride 14) | **+€678 (267)** | −0.28 (0.20) | +3.0 (0.9) | +47 | 92.2% (main 94.5%) | 1 | 0 |
| the 24 tune and wide weeks, once (stride 14, against `orch-base-s14`) | +€707 (297) | −0.36 (0.25) | +3.7 (1.0) | +49 | 94.2% (main 93.4%) | 0 | 0 |
| the 8 hold weeks, four samples a side (strides 12–15) | +€805 (421) | **−0.79 (0.27)** | +5.7 (1.1) | +64 | 93.2% (main 93.2%) | 1 (main 1) | 0 |

96 different weeks in all, 216 plays of B, none unranked, the worst 92.2%.

- By thirds of the weeks of 65..96, from the hardest drivers to the easiest (the week's own intercept, measured with hindsight on `main`'s play): margin +€1,419 / +€1,186 / +€385, on time −0.36 / −0.30 / −0.18 point. The week whose level is most wrong for B (halal-71, 1.16 logits under what B assumes) goes from 94.7% to 94.1% on time over four samples and gains €1,069.
- Orders by weekday on 97..128: 73 / 94 / 89 / 98 / 80 → 95 / 104 / 95 / 104 / 86; Monday's sales +€1,984 (se 311); the fastest option 54% → 55% of the orders with a choice.
- The known hard week (halal-09, the flu on a Friday in the capital region) is where it was: 96.0 / 93.8 / 93.2 / 95.4% on `main` and 95.0 / 95.1 / 93.9 / 94.4% on B over the four strides (mean 94.6% both). The hold week that B hurts is halal-10, the poorest world of the set (€9,180 a week on `main`): 96.8% → 94.4%, €961 less; there the right level for the average week is too hopeful.
- What B costs: a quarter to a third of a point of on-time on the untouched weeks (16 → 19 late orders a week), 0.8 point on the hold weeks, and a floor about half a point lower (worst of 216 plays 92.2%; `main`'s worst of 176 saved plays 92.8%). The 90% minimum is two points under B's worst play. B is not the target turned by another name: on these weeks `main`'s target trades a point of on-time for €512 (96.5%: +€200, −0.48 point; 97.5%: −€546, +0.97 point; the last group of the table), and at that price B at 97% is +€819 (se 180) at equal on-time and B at 97.5% +€946 (se 215).
- What B was *not* fitted on: the +0.88 is a measurement (the free intercept of the model on weeks it never saw), not the best of a search; the same number comes out of three disjoint sets of weeks. It was chosen before its neighbours (+0.5, +0.7 without the learner) were played; they are in the table for scale.

**The target, with B.** B at the target of 97% runs a quarter to three quarters of a point under `main`'s on-time. The target gives it back cheaply, because a model whose level is right pays little for caution:

| B against `main`, same weeks | margin (se) | on time, points (se) | late orders a week | worst play (main's) | plays under 93.5% |
|---|---|---|---|---|---|
| B, target 97%: halal-65..96, four samples a side | +€959 (166) | −0.27 (0.09) | +2.6 | 92.7% (92.8%) | 1 |
| B, target 97%: halal-97..128, once | +€678 (267) | −0.28 (0.20) | +3.0 | 92.2% (94.5%) | 1 |
| **B, target 97.5%: halal-65..96, two samples a side** | **+€679 (206)** | **+0.52 (0.11)** | −1.6 | 94.8% (92.8%) | 0 |
| **B, target 97.5%: halal-97..128, once (the confirmation of the head of the branch)** | **+€395 (264)** | **+0.21 (0.16)** | −0.4 | 93.2% (94.5%) | 1 |

From 97% to 97.5% B gives up about €280 for 0.5 to 0.8 point of on-time; `main` gives up €546 for 0.97 point at the same step on the same weeks. The level and the target are near substitutes once the learner is gone (the intercept moved by +0.5 instead of +0.88, at 97%: +€483 and +0.30 point), so the head sits on a flat stretch, not on an edge. **At 97.5% B earns more than `main` and is on time more often on both untouched sets (+€537 a week and +0.37 point over the 64 weeks), with a floor no lower (worst of 96 plays 93.2%; `main`'s worst of its 96 plays on the same weeks 92.8%).** That is the form at the head of this branch (`FleetPolicy.on_time = 0.975`, one number on top of dce27f9). B at 97% (dce27f9 itself) is the form with about €280 more margin, on time 0.3 point *under* `main` and a floor half a point lower.

**Proofs of the candidate.** Two trees: dce27f9 (B at 97%) and the head of the branch (the same `dispatch/` with one line changed, `FleetPolicy.on_time = 0.975` and its comment: `git diff dce27f9 -- dispatch`).

- **Restart = replay, the head:** `python -m tools.restart_test --seed halal-02 --restarts 8 --baseline skeptic-C975ns-x-s0`: 8 of 8 restarts rebuilt the same desk; €21,126.94, 96.1% on time and 482 orders with restarts and without: the same week to the cent. (`main` plays this week, without strides, at €21,071.78 and 93.4%.) **dce27f9:** 8 of 8, €22,034.37, 95.4%, 547 orders both ways. The fleet now has no memory of its own to rebuild.
- **The model of the head is calibrated on its own play:** `python -m tools.skeptic_fit -- skeptic-base-s14 skeptic-B975-s14` from this tree: on `main`'s play of halal-65..96 the 15-weight model says 4.5% late where 5.0% are (log-likelihood −0.1730; `main`'s 16 weights as baked −0.1957, with their intercept free −0.1752, a constant −0.1975); on the head's own play of the same weeks it says 4.3% where 4.0% are (−0.1482; a free intercept would move by +0.08 and gain nothing).
- **The head is the measured thing:** its tree plays the 32 weeks of halal-65..96 at stride 14 to the cent like dce27f9 with the override `{"fleet": {"on_time": 0.975}}` (32 of 32).
- **Python 3.9:** `ast.parse(source, feature_version=(3, 9))` passes for every file of `dispatch/`, and `dispatch.run` imports under `/usr/bin/python3` 3.9.6 with `PYTHONPATH=kit/python`.
- **The clean code is the measured thing:** the clean tree and the switch combination of `research/skeptic-switches` (`{"fleet": {"weights": {"known": 0, "one": -3.72}, "world": false}, "market": {"spread": {day, from, lane, to, world}}}`) play the 32 weeks of halal-65..96 at stride 14 to the cent (32 of 32), so every sample of the combination is a sample of the clean code. The same holds for A alone (32 of 32).
- **No leftover:** nothing in `dispatch/` or `tools/` refers to `learned`, `outcome`, `forecast`, `gig_posted` of the fleet, `Queue.world`, `Queue.known`, `KNOWN` or `DOUBT`; `tools/fleet_fit.py`, `control_study.py`, `crisis_study.py` and `winmodel.py` follow the code.
- **If it is merged, the documents that still describe `main`:** `PRESENTATION.md` (slide 1: 1,948 lines; slide 3: 16 weights; the parts of the level; "What we do not know": the two weights without support, of which `known` is now out and `waited` measured), `SPEAKER_NOTES.md` (lines 25 and 52: 1,948 lines, 16 weights, "one number per week mends it"), `OPEN_NUMBERS.md` (row "1,948 lines, eleven modules, 16 weights"), `RUNBOOK.md` nothing. `README.md` and `NIGHT_LOG.md` (idea 15) are updated on this branch.
