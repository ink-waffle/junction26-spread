# The skeptic's audit (Saturday 19:20–, branch `research/skeptic`)

The question: is the system fitted to its own weeks, and which of its parts carry the result on weeks nobody has seen?
Read with fresh eyes from `main` 832baf6 (decisions frozen at 52aaf93). Everything below can be printed again:

```sh
python -m tools.skeptic_fit orch-base-s14 -- final-fresh skeptic-base-s14   # the on-time model against 64 weeks it never saw
python -m tools.skeptic_market final-fresh skeptic-base-s14                 # the dealer side, each part taken out, on the same 64 weeks
python -m tools.ablations skeptic-base skeptic-nolook ...                   # the table of section 2 (weeks halal-65..96, strides 14 and 13)
```

## 1. Verdict

1. **The level is not overfitted; the headline number is.** The frozen system earns €14,360 a week on 32 fresh weeks (halal-33..64, played once) and €15,208 on 32 more that nobody had touched (halal-65..96, two samples each): 96 of 96 week-plays ranked, on time 96.3% in the mean, 92.8% in the worst. The €17,846 of the tune weeks is 8 rich worlds: a world's margin has a spread (sd) of €4,000, so the mean of 8 worlds strays by €1,400, and tune was already 10–19% above hold for the simple systems of Saturday morning. **Quote €14–15k, never €17.8k.**
2. **What the later ideas gained, they gained off the tune weeks too.** From ideas 1–10 to the frozen system: +€2,858 a week on tune (se 644) and +€2,635 on hold (se 512). The ratio final / early is the same per week on both sets (1.19 against 1.25). Against the House's best on ranking rounds, whose weeks no one tunes on: 0.96 × at 09:00 (ideas 1–7), 1.07 × at 12:00, 1.28 × at 15:00, 1.29 × at 18:00.
3. **The fitted parts mostly hold on weeks they never saw, with three exceptions.** On 64 unseen weeks the dealer side loses predictive power without its place table (64 of 64 weeks), its lane part (63), its event weighting (55) and trust (63); the driver side's large signs (fee, room, lane length, queue, pay, premium, flu) come back with the same sign and within reach of the baked weight. The exceptions: **`known`** has the wrong sign on unseen weeks (baked +0.25, they say −0.17 ± 0.06; the model is better without it); **the two supply signs** are real but baked twice too large (0.75 and 0.71 against 0.31 ± 0.04 and 0.34 ± 0.05: fitted on the rosters of 8 worlds); **the pickup-today and dealer parts** of the level predict nothing (+1.2 and −0.3 per mille of log-likelihood).
4. **The model's level is wrong by a factor of two, and one learned number mends it.** On unseen weeks the on-time model says 10.0% late and 4.8% are. Its log-likelihood as baked is worse than a constant's (−0.1960 against −0.1928); with one intercept free it is −0.1754. That intercept is what `Fleet.learned` finds during the week (+0.88 where it may move by 1): the part of the system that is hand-set with the least evidence (`DOUBT`, the clamp) is the part that carries the calibration. A week whose drivers are *easier* than ours by more than one logit would be left under-sold; a harder week is braked, which is the safe side.
5. **Where the evidence is thin:** every number set by hand in `fleet.py` and `timetable.py` (`DOUBT`, `GRIP`, `CALM`, `KNOWN`, the cap of the late price, `RETRY`, `MIN_SPAN`, the 30 minutes of `rung`) has no measurement behind it at all, or one tune comparison inside noise; the two-car fees (0.70, 0.85) rest on tune weeks; idea 14 (the flu) is +0.38 point of on-time at 1.9 standard errors on the weeks it was designed on and +0.30 (se 0.26) on hold; idea 13's played gain was never resolved (+€392, se 487) and stands on its exact replay (+€202, se 66) and on the answers it foretells. Section 2 measures each of these on untouched weeks.

**What could hurt in a week unlike ours.** (a) The floor: the worst of 96 unseen plays is 92.8%, the mean 96.3%, sd 1.0 point, and the hard week is known (the flu on a Friday in the capital region: 92–94%); a week under 90% would need a world outside everything in 120 worlds, not bad luck. (b) A note in words the grammar has not seen is missed silently: on the 64 unseen weeks the reader left 0.22–0.25 failed visits a week (the kit's reader: 10.6), so the vocabulary held. (c) The events are weighed as the rules state them (one war day, one outage day, never both): a week that breaks the rule costs little by the team's own replay (−€2 to +€118). (d) The 60 numbers of the place table and the supply signs describe *our* Finland: the map and the rosters are the same in every world we played, and the final is the same simulator; on another map both would have to go, and the system would still run (section 2: what it earns without them).

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
| 11 six-hour look, board pairs | tune +€1,900 | no clean pair on hold or wide | **in sample only** |
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

## 4. Ablations on untouched weeks (halal-65..96)

*(running; table follows)*

## 5. The simplest system that is as good

*(follows)*
