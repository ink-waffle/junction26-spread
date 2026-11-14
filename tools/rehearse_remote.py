"""A rehearsal with the desk on another machine, started there as the runbook starts a final: in tmux, by final.sh's
loop, with its log in a file. The practice world is created here, through the slot semaphore that only this machine
has, and the slot is held until the world ends. The pacer runs next to the desk, so this machine's network is no part
of the rehearsal; from here we only watch the world, as `tools.watch` does.

    python -m tools.rehearse_remote --commit 5b45675 --seed halal-01 --speed 4 --kill 2100

The remote folder `--home` is a clone of the repo that only rehearsals use (never the folder a final runs from)."""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shlex
import subprocess
import time

from spread.client import Client, SpreadError

from dispatch.atlas import HOUR
from tools.harness import RUNS, Slot, create
from tools.watch import signs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--ssh", default="ssh -i ~/.ssh/verda_junction -o BatchMode=yes -o ConnectTimeout=10 root@95.133.254.35")
    parser.add_argument("--home", default="/data/spread/rehearsal", help="the rehearsal's clone on the other machine")
    parser.add_argument("--env", default="/data/spread/repo/.env", help="the file with SPREAD_URL and SPREAD_KEY there")
    parser.add_argument("--commit", required=True, help="what to rehearse: the clone fetches and checks it out")
    parser.add_argument("--seed", default="halal-01")
    parser.add_argument("--speed", type=float, default=4)
    parser.add_argument("--start", type=int, default=7 * HOUR, help="4320 for a test final: Thursday 00:00")
    parser.add_argument("--kill", type=int, help="at this world minute, kill -9 the desk there: the loop must start it again")
    parser.add_argument("--baseline", default="live-main-practice")
    parser.add_argument("--tag", default="live-vm")
    args = parser.parse_args()

    def remote(command: str, text: str = "", check: bool = True) -> str:
        done = subprocess.run(shlex.split(os.path.expanduser(args.ssh)) + [command], input=text, capture_output=True, text=True, timeout=120)
        if check and done.returncode:
            raise SystemExit(f"{command[:60]}: {done.stderr.strip()[:300]}")
        return done.stdout

    home, client, ours, ends_at = args.home, Client(), False, 10 ** 9
    if remote("tmux has-session -t spread 2>/dev/null && echo taken; pgrep -f '[d]ispatch --final' >/dev/null && echo taken", check=False).strip():
        raise SystemExit("A desk or the tmux session 'spread' is alive there: it may be playing a final. No rehearsal next to it.")
    with Slot() as slot:
        world = create(client, 8, args.seed)
        slot.hold(world.id)
        try:
            ends_at = world.snapshot()["endsAt"]
            world.advance(to=args.start)
            print(remote(f"cd {home} && git fetch -q origin && git checkout -q {args.commit} && git log --oneline -1 && rm -rf run && mkdir run").strip(), flush=True)
            remote(f"cat > {home}/run/start.sh", f"cd {home}/run\nset -a; . {args.env}; set +a\nexport PYTHONPATH={home}/kit/python:{home}\n"
                   f"python3 -m tools.rehearse --pace {world.id} --speed {args.speed} > pacer.log 2>&1 &\n"
                   f"while true; do python3 -m dispatch --final --world {world.id} 2>&1 | tee -a desk.log; sleep 1; done\n")
            remote(f"tmux new-session -d -s spread 'sh {home}/run/start.sh'")
            ours, events, kill, now = True, [], args.kill, args.start
            while now < ends_at:
                time.sleep(20)
                try:
                    print(signs(world, events), flush=True)
                    now = world.snapshot()["now"]
                except SpreadError as error:  # this machine's network is not the one we rehearse
                    print(f"cannot read the world from here: {str(error)[:100]}", flush=True)
                if kill and now >= kill:
                    remote(f"pkill -9 -f '[d]ispatch --final --world {world.id}'", check=False)
                    print(f"-- kill -9 on the desk at about minute {now}", flush=True)
                    kill = None
            score = world.score()
        finally:
            if ours:
                remote("tmux kill-session -t spread", check=False)
            if world.snapshot()["now"] < ends_at:
                world.delete()
    log, reveal = remote(f"cat {home}/run/desk.log"), world.reveal()
    os.makedirs(os.path.join(RUNS, args.tag), exist_ok=True)
    with open(os.path.join(RUNS, args.tag, f"{args.seed}.desk.log"), "w") as file:
        file.write(log)
    turns = sorted(int(line.split("slowest turn ")[1].split(" ms")[0]) for line in log.splitlines() if "slowest turn" in line and not line.endswith(" 0 ms"))
    unquoted = sum(1 for r in reveal["requests"] if r["outcome"] == "unquoted" and r["request"]["arrivedAt"] >= args.start)
    print(f"== {args.seed} at {args.speed:g}x, desk on the other machine: margin €{score['marginCents'] / 100:,.2f}  on time {score['onTimeShare']:.1%}  won {score['wonOrders']}  "
          f"unquoted {unquoted}  slowest turn of an hour: median {turns[len(turns) // 2] if turns else 0} ms, max {turns[-1] if turns else 0} ms  "
          f"joins {sum('joined after' in line for line in log.splitlines())}")
    path = os.path.join(RUNS, args.baseline, f"{args.seed}.json.gz")
    if os.path.exists(path) and args.start == 7 * HOUR:
        with gzip.open(path, "rt") as file:
            base = json.load(file)["score"]
        print(f"== practice loop, same seed: margin €{base['marginCents'] / 100:,.2f}  on time {base['onTimeShare']:.1%}  won {base['wonOrders']}")
    print(remote("pgrep -af '[d]ispatch --final' || echo 'no desk is left there'", check=False).strip())


if __name__ == "__main__":
    main()
