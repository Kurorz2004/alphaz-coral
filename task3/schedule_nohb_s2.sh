#!/usr/bin/env bash
# One-shot scheduler for nohb-s2 (Condition B, noheartbeat) on real Sonnet.
# Waits for the 5-hour quota window to reset, disables the deepseek alias only
# for the duration of the run, launches detached, and ALWAYS restores the alias
# on exit (trap) so a killed scheduler can't leave settings.json neutered.
set -uo pipefail
cd "$(dirname "$0")" || exit 1

RESET_EPOCH=${RESET_EPOCH:-1783732200}   # Sat Jul 11 08:10:00 +07 2026
SLACK=${SLACK:-180}
TARGET=$((RESET_EPOCH + SLACK))
SETTINGS="/root/.claude/settings.json"
BAK="/root/.claude/settings.json.nohb-s2-bak"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

restore_settings() {
  if [ -f "$BAK" ]; then
    cp "$BAK" "$SETTINGS" && log "restored settings.json (deepseek alias back)"
    rm -f "$BAK"
  fi
}
trap restore_settings EXIT

now=$(date +%s)
wait_s=$((TARGET - now))
log "scheduler up; launching nohb-s2 at $(date -d "@$TARGET") (in $((wait_s/60))m ${wait_s}s)"
[ "$wait_s" -gt 0 ] && sleep "$wait_s"

if ps -eo args | grep -q "[p]ython -m coral.cli start"; then
  log "!! a CORAL manager is already running — aborting launch"
  exit 1
fi

# Neutralize the sonnet->deepseek alias for the run; trap restores it afterward.
cp "$SETTINGS" "$BAK"
python3 -c "import json; p='$SETTINGS'; d=json.load(open(p)); d['env']={}; json.dump(d, open(p,'w'), indent=2)"
log "disabled deepseek alias (env={}); launching driver for nohb-s2"

env -u ANTHROPIC_DEFAULT_SONNET_MODEL -u ANTHROPIC_DEFAULT_HAIKU_MODEL \
  ./run_ablation.sh nohb-s2
log "driver returned $?"
