#!/bin/sh
# The desk for a final, started again whenever it stops. RUNBOOK.md says when and where to run it:
#   tmux new-session -d -s spread /data/spread/repo/final.sh        (arguments go to the desk, for example --policy '{...}')
cd "$(dirname "$0")" || exit 1
set -a; . ./.env; set +a
export PYTHONPATH=kit/python
PY=python3
[ -x .venv/bin/python ] && PY=.venv/bin/python
while true; do
    "$PY" -m dispatch --final "$@" 2>&1 | tee -a final.log
    sleep 1
done
