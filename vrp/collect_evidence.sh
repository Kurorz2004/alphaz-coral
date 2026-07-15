#!/usr/bin/env bash
# Build a publishable evidence tree from vrp/results/ (which is gitignored).
#
# For each real run dir under results/<cond>/<run>/ (symlinks like `latest`
# are skipped), copies only the reviewer-relevant subset of .coral/public/
# (attempts, notes, skills, roles, diagnostics, heartbeat, .publication,
# eval_count) plus config.yaml, start_cmd.txt, and a full git bundle of the
# run's embedded `repo/`. Never copies eval_logs/, logs/, agents/, private/,
# *.pid files, agent_pids.json, agent_state.json, or grader_daemon_heartbeat.
#
# Idempotent: wipes its own dest (evidence/) before rebuilding.
set -euo pipefail

cd "$(dirname "$0")"

DEST="evidence"
rm -rf "$DEST"
mkdir -p "$DEST"
EVID="$(pwd)/$DEST"

# "gate" (one incomplete 7/12 run, not cited in the report) is deliberately excluded.
CONDITIONS="full noknowledge noheartbeat consol"
PUBLIC_DIRS="attempts notes skills roles diagnostics heartbeat .publication"

run_count=0

for cond in $CONDITIONS; do
    cond_dir="results/$cond"
    [ -d "$cond_dir" ] || continue

    for run_path in "$cond_dir"/*/; do
        run_path="${run_path%/}"
        [ -e "$run_path" ] || continue          # unmatched glob
        [ -L "$run_path" ] && continue          # skip `latest` symlinks
        [ -d "$run_path" ] || continue

        run="$(basename "$run_path")"
        run_count=$((run_count + 1))

        dest_run="$DEST/$cond/$run"
        mkdir -p "$dest_run/.coral/public"

        # 2. config.yaml
        cp "$run_path/.coral/config.yaml" "$dest_run/.coral/config.yaml"

        # 3. reviewer-relevant subset of .coral/public/, dereferencing symlinks
        for item in $PUBLIC_DIRS; do
            src="$run_path/.coral/public/$item"
            if [ -e "$src" ]; then
                cp -rL "$src" "$dest_run/.coral/public/$item"
            fi
        done
        if [ -e "$run_path/.coral/public/eval_count" ]; then
            cp -L "$run_path/.coral/public/eval_count" "$dest_run/.coral/public/eval_count"
        fi

        # 4. start_cmd.txt
        if [ -e "$run_path/start_cmd.txt" ]; then
            cp "$run_path/start_cmd.txt" "$dest_run/start_cmd.txt"
        fi

        # 5. full history of the run's evolved program
        if [ -d "$run_path/repo" ]; then
            git -C "$run_path/repo" bundle create "$EVID/$cond/$run/repo.bundle" --all >/dev/null
        fi

        # --- per-run summary ---
        n_attempts=0
        [ -d "$dest_run/.coral/public/attempts" ] && n_attempts=$(find "$dest_run/.coral/public/attempts" -type f -name '*.json' | wc -l | tr -d ' ')
        n_notes=0
        [ -d "$dest_run/.coral/public/notes" ] && n_notes=$(find "$dest_run/.coral/public/notes" -type f | wc -l | tr -d ' ')
        bundle_size="--"
        [ -f "$dest_run/repo.bundle" ] && bundle_size=$(du -h "$dest_run/repo.bundle" | cut -f1)
        echo "  $cond/$run: attempts=$n_attempts notes=$n_notes bundle=$bundle_size"
    done
done

# Python bytecode sneaks in with copied skills/ scripts; it is not evidence.
find "$DEST" -type d -name __pycache__ -prune -exec rm -rf {} +

# Results-root files (< 2MB each; skip + warn otherwise)
for f in ablation.log consol.log manifest.jsonl; do
    src="results/$f"
    if [ -f "$src" ]; then
        size=$(wc -c < "$src" | tr -d ' ')
        if [ "$size" -lt 2097152 ]; then
            cp "$src" "$DEST/$f"
        else
            echo "WARNING: skipping $src (${size} bytes >= 2MB)" >&2
        fi
    fi
done

echo ""
echo "Collected $run_count run dir(s) into $DEST/"
du -sh "$DEST"
