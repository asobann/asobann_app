#!/usr/bin/env bash
# Run a suite of sustained_load configurations against staging, recording precise UTC
# start/end times and worker logs for each, so summarize_load_suite.py can later pull
# matching CloudWatch CPU windows and so a crashed worker's cause can be diagnosed
# without re-running (docker logs are saved before containers are removed).
#
# Usage: ./scripts/run_load_suite.sh <label> [config_name...]
# Examples:
#   ./scripts/run_load_suite.sh baseline
#   ./scripts/run_load_suite.sh after-throttle-fix flip_n4 flip_n6
#
# Run this detached (nohup ... & disown) - the full suite takes well over an hour.

set -u
cd "$(dirname "$0")/.."

STAGING_URL="https://staging.asobann.yattom.jp"
GAP_SECONDS=90

if [ $# -lt 1 ]; then
    echo "usage: $0 <label> [config_name...]" >&2
    exit 1
fi
LABEL="$1"
shift
REQUESTED_CONFIGS=("$@")

OUT_DIR="results/${LABEL}"
if [ -e "$OUT_DIR" ]; then
    echo "ERROR: $OUT_DIR already exists. Choose a new label to avoid overwriting a previous run." >&2
    exit 1
fi
mkdir -p "$OUT_DIR"

# name:total_players:worker_count:hz:operation:duration_seconds
# operation empty means mousemove-only (drag_interval_seconds=0)
CONFIGS=(
    "flip_n2:2:1:30:flip:300"
    "flip_n3:3:2:30:flip:300"
    "flip_n4:4:3:30:flip:300"
    "flip_n5:5:4:30:flip:300"
    "flip_n6:6:5:30:flip:300"
    "flip_n4_15hz:4:3:15:flip:300"
    "flip_n6_15hz:6:5:15:flip:300"
    "mouseonly_n2:2:1:30::300"
    "mouseonly_n4:4:3:30::300"
    "mouseonly_n6:6:5:30::300"
)

should_run() {
    local name="$1"
    if [ ${#REQUESTED_CONFIGS[@]} -eq 0 ]; then
        return 0
    fi
    for c in "${REQUESTED_CONFIGS[@]}"; do
        [ "$c" = "$name" ] && return 0
    done
    return 1
}

echo "building image..."
uv run --no-project --with typer python -m tests.performance.cli build-image --run-on docker --debug \
    > "$OUT_DIR/build.log" 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: image build failed, see $OUT_DIR/build.log" >&2
    exit 1
fi

SUITE_JSON="$OUT_DIR/suite.json"
echo "[]" > "$SUITE_JSON"

for entry in "${CONFIGS[@]}"; do
    IFS=':' read -r name total workers hz operation duration <<< "$entry"
    if ! should_run "$name"; then
        continue
    fi

    echo ""
    echo "=== $name (total=$total players, hz=$hz, operation=${operation:-none}, ${duration}s) ==="

    docker ps -a --format '{{.ID}} {{.Image}}' | grep test_run_multiprocess | awk '{print $1}' | xargs -r docker rm -f > /dev/null 2>&1

    PARAM_ARGS=(--param "duration_seconds=$duration" --param "mousemove_hz=$hz")
    if [ -n "$operation" ]; then
        PARAM_ARGS+=(--param "drag_interval_seconds=10" --param "operation=$operation")
    else
        PARAM_ARGS+=(--param "drag_interval_seconds=0")
    fi

    START_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    RESULT_JSON="$OUT_DIR/${name}.json"
    RUN_LOG="$OUT_DIR/${name}.runlog.txt"

    timeout $((duration + 300)) uv run --no-project --with typer python -m tests.performance.cli run \
        tests.performance.sustained_load "$workers" \
        --run-on docker --url "$STAGING_URL" \
        "${PARAM_ARGS[@]}" \
        --debug --output "$RESULT_JSON" \
        > "$RUN_LOG" 2>&1
    EXIT_CODE=$?
    END_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    # Save worker logs BEFORE removing containers - the only way to see why a worker died
    # (e.g. the card-position diagnostic in sustained_load.py) once containers are gone.
    WORKER_LOG="$OUT_DIR/${name}.workerlog.txt"
    : > "$WORKER_LOG"
    for c in $(docker ps -a --format '{{.ID}} {{.Image}}' | grep test_run_multiprocess_in_container_worker | awk '{print $1}'); do
        echo "--- container $c ---" >> "$WORKER_LOG"
        docker logs "$c" >> "$WORKER_LOG" 2>&1
    done

    python3 -c "
import json
meta = {
    'name': '$name', 'total_players': $total, 'worker_count': $workers,
    'hz': $hz, 'operation': '$operation', 'duration_seconds': $duration,
    'start_utc': '$START_UTC', 'end_utc': '$END_UTC', 'exit_code': $EXIT_CODE,
}
with open('$OUT_DIR/${name}.meta.json', 'w') as f:
    json.dump(meta, f, indent=2)
suite = json.load(open('$SUITE_JSON'))
suite.append(meta)
with open('$SUITE_JSON', 'w') as f:
    json.dump(suite, f, indent=2)
"

    if [ $EXIT_CODE -ne 0 ]; then
        echo "WARNING: $name exited with code $EXIT_CODE, see $RUN_LOG"
    else
        echo "$name done ($START_UTC .. $END_UTC)"
    fi

    docker ps -a --format '{{.ID}} {{.Image}}' | grep test_run_multiprocess | awk '{print $1}' | xargs -r docker rm -f > /dev/null 2>&1

    echo "waiting ${GAP_SECONDS}s before next configuration..."
    sleep "$GAP_SECONDS"
done

echo ""
echo "suite '$LABEL' complete. See $OUT_DIR/suite.json"
