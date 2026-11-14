# Runbook: the desk in a final

The final's clock runs by itself (a weekday hour is 18 real seconds, so a price request must be answered within 4.5 s). The desk keeps up alone; a person only starts it, watches it, and starts it again if it dies.

## Start

```sh
cd spread                                   # always the same folder: the journal lives here
set -a; . ./.env; set +a                    # SPREAD_URL, SPREAD_KEY
.venv/bin/python -m dispatch --final 2>&1 | tee -a final.log
```

- Start it at any time. While no final is set it prints `No final is set. Waiting for it.` and asks every 10 s. The organisers set a test final at 13:45 and 19:45 on Saturday and the final at 07:30 on Sunday; the clock starts 15 or 30 minutes later.
- `--policy '{"market": {...}, "fleet": {...}}'` overrides the default policy, as in the harness. The policy is not stored: a restart must name the same one.
- **One desk per team key.** Two desks would both quote and both post every car. A second start from the same folder refuses (`Another desk already runs from this folder`); nothing stops a second one on another machine, so stop the old one first.
- After the world ends the desk prints `End ...` and `Ranked.` or `Not ranked.`, and exits.

## How to tell it is healthy

```text
World wab12… Ctrl-C stops the desk, not the world: start it again and it rejoins.
Thu 00:00  joined after 0 events: 0 orders, 0 of 0 requests quoted, 0 actions to send
Thu 09:00  margin €      0.00     1 orders    0 without a driver     6 of    6 requests quoted  slowest turn 73 ms
Thu 10:01  margin €     35.37     5 orders    0 without a driver    26 of   26 requests quoted  slowest turn 83 ms
Thursday   margin €    222.48  revenue €     931.00    65 orders  100.0% on time   0.0% not delivered
```

- One line per world hour, from our own books: every 18 s by day, every 3 s at night. No line for a minute: it is dead or the server is down.
- `N of M requests quoted` must grow together between 08:00 and 18:00 on weekdays; the gap is what we did not answer in time (requests from before we joined count in M). `slowest turn` is the longest time in that hour from a burst of events to the world's answer to our actions: under 500 ms is normal from Helsinki (the round trip is about 55 ms), above 3,000 ms quotes start to miss their 4.5 s.
- One line per world day with the server's own score: margin, orders, on-time share. On time must stay at or above 90%.
- Every action the world refused is one `refused …` line with the world's reason. A few `refused quote … response deadline` lines right after a restart are normal: the request ran out while we were away.
- `… A new desk rejoins in N s.` means a request failed or the server restarted; the desk rebuilt itself. Repeated every few seconds for more than a minute: the server or our network is down.
- A Python traceback followed by more hour lines: an event the desk could not read was passed over. Note the line; the desk goes on.

## If it dies

Start it again, the same command in the same folder. Nothing else.

- The world went on without us: our gigs kept their fees, booked drivers kept driving, and requests that ran out went to the competitor (that costs a little goodwill each, nothing more).
- The new desk reads the world's whole log and its snapshot (0.6 s late in the week), replays them together with `journal-<world id>.jsonl` (every batch we sent and what the world answered), and is the desk that died: `tools/restart_test.py` checks this object by object. It then quotes every request that is still open and posts every car that has no gig.
- No journal (another machine, a deleted file): it still rejoins, with every order and gig, from the log and the snapshot. What is lost: the prices we quoted, so the market starts again from its prior and learns from the answers still to come; the memory of refused posts; and the open gig of each order that the dealer changed is posted once more. Measured on halal-01 with 12 restarts and never a journal: €5,966 and 88.5% on time against €6,089 and 89.5%. Copy the journal when you can.
- If it dies again at once with the same traceback, the bug is in the replay of some event. Run with the last commit that worked; the journal and the log do not depend on the code version.
- Doing nothing is safe: a desk that is down wins no new cars and the cars it has keep their gigs.

Check before a final: `python -m tools.rehearse --tag live-check --seeds halal-01 --speed 4 --until 1440 --trouble kill:2,dead:1,cut:1,fail:1` plays a Monday at four times the final's speed with a killed desk, a dead stream and a lost request; `unquoted` should stay near the requests that arrived while the desk was down.

## A machine near the server

The organisers recommend a machine near the server, in Stockholm. From this laptop in Helsinki the round trip is 55 ms: a quote reaches the world 72 ms after its request (median; 190 ms at the 99th percentile), the desk answers every request at eight times the final's speed, and with 1.5 s added to every request it still answered every request of a Monday. So the cloud machine is insurance against the laptop and its network, not a need. Verda (we have credits):

1. Create the smallest CPU instance in the region nearest Stockholm (Helsinki, FIN), Ubuntu 24.04, with your SSH key. Nothing here needs a GPU.
2. Copy the code: `git clone git@github.com:ink-waffle/junction26-spread.git spread` with a deploy key, or `rsync -a --exclude .venv --exclude runs ./ user@host:spread/`.
3. Copy the key: `scp .env user@host:spread/.env` (`SPREAD_URL`, `SPREAD_KEY`; never commit it).
4. On the machine: `cd spread && python3 -m venv .venv && .venv/bin/pip install kit/spread-0.1.0-py3-none-any.whl`. The desk needs Python 3.9 or later and nothing else.
5. Measure: `.venv/bin/python -c "import time; from spread.client import Client; c = Client(); c.worlds(); t = time.time(); [c.worlds() for _ in range(10)]; print((time.time() - t) * 100, 'ms')"` after `set -a; . ./.env; set +a`.
6. Start it inside `tmux` (or `systemd-run --user`), so a dropped SSH session does not stop it: `tmux new -s desk` then the start command above, wrapped as `while true; do …; sleep 1; done` if it should start again by itself.
7. Moving a running final between machines: stop the desk here, `scp journal-*.jsonl user@host:spread/`, start it there. Never run both.
