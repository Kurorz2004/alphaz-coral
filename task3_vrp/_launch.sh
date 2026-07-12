#!/usr/bin/env bash
# Quick launcher for the VRP ablation.
# Usage:
#   ./_launch.sh              # start a tmux session and run
#   ./_launch.sh direct       # run in the current terminal (no tmux)
set -euo pipefail
cd "$(dirname "$0")"

if ! "${1:-}" = "direct" && command -v tmux &>/dev/null; then
  SESSION="task3_vrp_$(date +%m%d_%H%M)"
  tmux new-session -d -s "$SESSION" ./run_ablation.sh
  echo "tmux session: $SESSION"
  echo "attach: tmux attach -t $SESSION"
else
  ./run_ablation.sh
fi
