# Runbook: the desk in a final

The final's clock runs by itself: a weekday hour is 18 real seconds, so a price request must be answered within 4.5 s. The desk keeps up alone. A person starts it, watches it, and starts it again if it dies. **One desk per world, ever**: two desks would both quote and both post.

## A test final, step by step (Saturday 14:00 and 20:00)

| When | What | What you see |
|---|---|---|
| 13:30 | Deploy the commit to the cloud machine and measure the round trip (Cloud run, below). | `… ms; then median 10 ms` |
| 13:40 | Start the desk in tmux `spread` on the cloud machine. | `No final is set. Waiting for it.` |
| 13:45 | The organisers set the test final. The desk finds it within 10 s and joins. | `World w…` then `Thu 00:00  joined after N events: 0 orders, 0 of M requests quoted, 0 actions to send` |
| 14:00 | The clock starts on Thursday 00:00. Night hours take 3 s each. | hour lines; the first requests come at Thursday 08:00, 54 s after the start |
| 14:01 to 14:11 | Thursday and Friday: an hour line every 18 s. | `N of M requests quoted` grows by 10 to 40 an hour; `slowest turn` under 100 ms from the cloud machine |
| 14:19 | The week ends on the second Wednesday at 22:00. | `End  margin € …` and `Ranked.` or `Not ranked.` |
| after | Stop the desk (`tmux kill-session -t spread`), or it waits for the next final and plays it. | |

A test final starts on Thursday with nothing of ours in it: no orders, no journal, and M may already count the requests of Monday to Wednesday that nobody answered. The desk treats it as any world it joins late: the market starts from its prior and learns from the first answers, and the on-time line counts only what we win from Thursday on. Rehearse it with `python -m tools.rehearse --tag live-thu --seeds halal-02 --start 4320`.

## Start (any machine)

```sh
cd spread                                   # always the same folder: the journal lives here
set -a; . ./.env; set +a                    # SPREAD_URL, SPREAD_KEY
.venv/bin/python -m dispatch --final 2>&1 | tee -a final.log
```

- Start it at any time. While no final is set it prints `No final is set. Waiting for it.` and asks every 10 s.
- `--policy '{"market": {...}, "fleet": {...}}'` overrides the default policy, as in the harness. The policy is not stored: a restart must name the same one.
- A second start from the same folder refuses (`Another desk already runs from this folder`). Nothing stops a second desk on another machine: see "Never two desks".
- After the world ends the desk prints `End ...` and `Ranked.` or `Not ranked.`, and exits.

## Cloud run

The team's machine in Helsinki, `root@95.133.254.35`: 10 ms to the server (the laptop on a phone hotspot: 40 to 70 ms, and on Saturday morning it lost its route for six hours and then stalled for five minutes under a rehearsal). The final runs there; the laptop is the fallback. On that machine use only `/data/spread` and the tmux session `spread`; touch nothing else, install nothing, never reboot.

```sh
vm() { ssh -i ~/.ssh/verda_junction -o BatchMode=yes root@95.133.254.35 "$@"; }

# deploy: a named commit, never "whatever main is now"
vm 'cd /data/spread/repo && git fetch -q origin && git checkout -q <commit> && git log --oneline -1'
vm 'cd /data/spread/repo && set -a && . ./.env && set +a && PYTHONPATH=kit/python:. python3 -m tools.rtt'

# start: in tmux, so it outlives the laptop's connection; final.sh starts the desk again whenever it stops
vm 'tmux new-session -d -s spread /data/spread/repo/final.sh'            # with a policy: … "/data/spread/repo/final.sh --policy '{…}'"

# watch
vm 'tail -n 30 -f /data/spread/repo/final.log'                           # the desk's own lines
.venv/bin/python -m tools.watch                                          # on the laptop, from the server alone: also when SSH is down

# restart (it hangs, or new code after a deploy): kill the process; final.sh starts it again within a second and it rejoins
vm 'pkill -f "[d]ispatch --final"'

# stop: after a final, or final.sh waits for the next final and plays it
vm 'tmux kill-session -t spread; pgrep -af "[d]ispatch --final" || echo no desk runs'
```

- `final.sh` is the start command of "Start" in a loop, with the log in `final.log` next to it; it works on the laptop too (`./final.sh`), where it takes the venv's Python.
- The system Python there is 3.12 and needs no venv: the kit is in the repo (`PYTHONPATH=kit/python`), and `dispatch/` uses the standard library only and parses as Python 3.9.
- The desk keeps three files next to itself: `journal-<world id>.jsonl` (what we sent and what the world answered), `journal-hosts.json` (the server's last known address, for a resolver that fails) and `journal-desk.lock`.
- Never start the desk outside tmux over SSH: when the laptop's connection drops, a desk started from the SSH session dies with it. That happened in the first rehearsal from this machine.

### Never two desks

A desk that runs is the only one allowed to act. Before you start a desk anywhere, prove that no other one acts:

1. `vm 'pgrep -af "[d]ispatch --final"'` prints nothing, and `pgrep -af "[d]ispatch --final"` on the laptop prints nothing.
2. If the cloud machine does not answer SSH, you cannot know from SSH whether its desk is dead or only your connection is. Ask the world: `.venv/bin/python -m tools.watch` on the laptop (after `set -a; . ./.env; set +a`) prints one line every 5 s and ends it with `a desk is answering` (an order won or a gig posted in the last two world hours), `NO DESK IS ANSWERING` (15 or more requests closed in those two hours, and neither), or `no way to tell` (night, weekend). Two world hours are 36 real seconds by day.
   - `a desk is answering`: the cloud desk is alive. Do not start another. Fix your SSH.
   - `NO DESK IS ANSWERING`: start the desk on the laptop: `./final.sh` in the main checkout. It joins without the cloud machine's journal, which costs little (see "If it dies").
3. When the cloud machine answers again while the laptop desk runs: first `vm 'tmux kill-session -t spread'`, then check with `pgrep`. Its desk would rejoin the moment its network returned.

If two desks do run for a while, the world limits the damage: the later quote replaces the earlier one, the second post of a car is refused (`already in a live gig`), and both share the 20 actions a second. Kill one; the other needs nothing.

## How to tell it is healthy

```text
World wab12… Ctrl-C stops the desk, not the world: start it again and it rejoins.
Thu 00:00  joined after 0 events: 0 orders, 0 of 0 requests quoted, 0 actions to send
Thu 09:00  margin €      0.00     1 orders    0 without a driver     6 of    6 requests quoted  slowest turn 23 ms
Thu 10:01  margin €     35.37     5 orders    1 without a driver    26 of   26 requests quoted  slowest turn 41 ms
Thursday   margin €    222.48  revenue €     931.00    65 orders  100.0% on time   0.0% not delivered
```

- One line per world hour, from our own books: every 18 s by day, every 3 s at night. No line for a minute: it is dead, or it cannot reach the server.
- `N of M requests quoted`: both must grow together between 08:00 and 18:00 on weekdays. The gap is what we did not answer in time; requests from before we joined stay in the gap.
- `slowest turn`: the longest time in that hour from a burst of events to the world's answer to our actions. From the cloud machine 15 to 60 ms, from the laptop 70 to 600 ms. Above 3,000 ms quotes start to miss their 4.5 s.
- One line per world day with the server's own score. On time must stay at or above 90%.
- `refused …`: an action the world refused, with its reason. `N requests ran out before we saw them`: we were away or slow, and did not send quotes that nobody would read.
- `… No desk for N min; a new one rejoins in N s.`: a request failed, or the server restarted, and the desk rebuilt itself. After five tries in a row it says so once a minute: the server or our network is down, and the desk keeps trying for as long as it takes.
- A Python traceback followed by more hour lines: an event the desk could not answer was passed over. Note it; the desk goes on.

## If it dies

Start it again: the same command in the same folder. On the cloud machine the loop does it. Nothing else.

- The world went on without us: our gigs kept their fees, booked drivers kept driving, and requests that ran out went to the competitor (a little goodwill each, nothing more).
- The new desk reads the world's whole log and its snapshot (0.6 s late in the week), replays them together with the journal, and is the desk that died: `tools/restart_test.py` compares the two object by object. It then quotes every request that is still open and posts every car that has no gig.
- No journal (another machine, a deleted file): it still rejoins with every order and gig, from the log and the snapshot. What is lost: the prices we quoted, so the market starts again from its prior and learns from the answers still to come; the memory of refused posts; and the open gig of each order that the dealer changed is posted once more. To move a running final with its memory: stop the desk, `scp` the `journal-*` files into the other machine's folder, start it there.
- The resolver fails (Saturday morning: the laptop's resolver refused the server's name while the server answered): the desk asks 1.1.1.1 and 8.8.8.8 itself, and when they are silent too it dials the last address anyone gave it, kept in `journal-hosts.json`. Nothing to do.
- If it dies again at once with the same traceback, the bug is in the replay of some event. Deploy the last commit that worked; the journal and the log do not depend on the code.
- Doing nothing is safe: a desk that is down wins no new cars, and the cars it has keep their gigs.

## Check before a final

```sh
python -m tools.rehearse --tag live-check --seeds halal-01 --speed 4 --until 1440 --trouble kill:2,dead:1,cut:1,fail:1   # a Monday at 4x with a killed desk, a dead stream, a lost request
python -m tools.rehearse --tag live-thu --seeds halal-02 --start 4320                                                   # a test final: from Thursday 00:00 at the real clock, 19 minutes
python -m tools.restart_test --seed halal-02 --restarts 12 --baseline <tag of a harness run of the same commit>          # restart = replay
```

The line of a rehearsal ends with what matters: `unquoted` (requests we did not answer; 0 without trouble), the milliseconds from a request to the world's answer to our quote, and how long the desk thought about a turn. While a final or a test final runs, practice worlds get 20 requests a second for every team: do not rehearse between 14:00 and 14:20 or between 20:00 and 20:20.
