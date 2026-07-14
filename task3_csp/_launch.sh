#!/bin/bash
# Launch the BPP ablation. Run this from task3_csp/ inside tmux/screen.
# Usage:  bash _launch.sh
set -euo pipefail
cd "$(dirname "$0")"

# Verify preflight
command -v tmux >/dev/null || { echo "!! tmux not found"; exit 1; }
[ "$(git -C ../coral-upstream config core.autocrlf)" = "input" ] || {
  echo "!! run: git -C ../coral-upstream config core.autocrlf input"
  exit 1
}
pgrep -f "python.*coral.cli start" >/dev/null && {
  echo "!! CORAL manager already running — run: pkill -f 'coral.cli start'"
  exit 1
}

echo "=== Launching BPP ablation (benchmark instances) ==="
echo "Model: ${MODEL:-sonnet} (actually deepseek-v4-pro via alias)"
echo "Instances: $(ls taskdata/instances/*.txt | wc -l) benchmark instances"
echo "Results: results/"
echo ""

tmux new-session -d -s bpp-ablation -x 200 -y 50 \
  "cd $(pwd) && ./run_ablation.sh 2>&1 | tee ablation.log"
echo "Launched in tmux session 'bpp-ablation'"
echo "  Attach: tmux attach -t bpp-ablation"
echo "  Detach: Ctrl+B D"
echo "  Monitor: tail -f ablation.log"
echo "  Status:  cat results/manifest.jsonl"
