#!/usr/bin/env bash
#
# rerun_nok_s3.sh — re-run nok-s3 after root-cause fix
#
set -uo pipefail
cd "$(dirname "$0")" || exit 1
log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }

log "=== removing old nok-s3 run dir ==="
rm -rf results/noknowledge/nok-s3
log "=== launching nok-s3 ==="
./run_nok_s3.sh
rc=$?
log "nok-s3 exited rc=$rc"
[ $rc -eq 0 ] && log "SUCCESS" || log "FAILED (rc=$rc)"
