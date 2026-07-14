#!/usr/bin/env bash
#
# rerun_nok.sh — re-run all three nok (Condition A) runs after root-cause fix
#
# The root-cause fix (removing unconditional mkdir from _notes_dir / _skills_dir)
# prevents CORAL from creating knowledge directories when agents.knowledge=false.
# This script deletes the old nok run dirs and re-runs all three sequentially.
#
set -uo pipefail
cd "$(dirname "$0")" || exit 1

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

manager_alive() { ps -eo args | grep -q "[p]ython -m coral.cli start"; }

log "=== cleaning old nok run dirs ==="
for d in results/noknowledge/nok-s1 results/noknowledge/nok-s2 results/noknowledge/nok-s3; do
  if [ -d "$d" ]; then
    log "removing $d"
    rm -rf "$d"
  fi
done

log "=== re-running all three nok runs ==="

for script in run_nok_s1.sh run_nok_s2.sh run_nok_s3.sh; do
  # Check if the script exists; s2 might need special handling (real sonnet)
  if [ ! -f "$script" ]; then
    log "SKIP $script — not found (may need schedule_nohb_s2.sh-style wrapper)"
    continue
  fi

  # Wait for any previous manager to drain
  while manager_alive; do
    log "waiting for manager to drain..."
    sleep 30
  done
  sleep 60

  log "LAUNCH $script"
  ./"$script"
  rc=$?
  log "$script exited rc=$rc"
  [ $rc -ne 0 ] && log "!! $script failed (rc=$rc)"
done

log "=== nok re-run complete ==="
