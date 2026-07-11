#!/usr/bin/env bash
# One-shot scheduler: wait for the 5-hour Sonnet window to reset, then launch
# nok-s2 detached. Launch time is reset epoch + 3 min slack. Even if the window
# slid past that, the driver's own rate_limited/wait_for_reset path retries, so
# launching a touch early is safe. Belt-and-suspenders env -u keeps the deepseek
# alias from creeping back in if ~/.claude/settings.json is ever restored early.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

RESET_EPOCH=${RESET_EPOCH:-1783714200}   # Sat Jul 11 03:10:00 +07 2026
SLACK=${SLACK:-180}
TARGET=$((RESET_EPOCH + SLACK))

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

now=$(date +%s)
wait_s=$((TARGET - now))
log "scheduler up; launching nok-s2 at $(date -d "@$TARGET") (in $((wait_s/60))m ${wait_s}s)"
[ "$wait_s" -gt 0 ] && sleep "$wait_s"

# Refuse to start on top of a live manager.
if ps -eo args | grep -q "[p]ython -m coral.cli start"; then
  log "!! a CORAL manager is already running — aborting launch"
  exit 1
fi

log "launching driver for nok-s2"
env -u ANTHROPIC_DEFAULT_SONNET_MODEL -u ANTHROPIC_DEFAULT_HAIKU_MODEL \
  ./run_ablation.sh nok-s2
log "driver returned $?"
