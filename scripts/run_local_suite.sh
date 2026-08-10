#!/usr/bin/env bash
# Local counterpart to run_load_suite.sh: runs sustained_load configurations against the
# deploy/loadtest app (must already be `docker compose up -d`, with the CPU quota already
# set via set_app_cpu.sh - this script records whatever quota is live, it does not change
# it). Records cgroup cpu.stat for the app+mongo containers instead of pulling CloudWatch.
# See plan.local-profiling.20260810.md §4, §7.
#
# Usage: ./scripts/run_local_suite.sh <label> [config_name...]
# Examples:
#   ./scripts/run_local_suite.sh calib-q083          # all configs in CONFIGS below
#   ./scripts/run_local_suite.sh calib-q083 flip_n4  # just one
#
# CONFIGS is intentionally small here (calibration + profiling targets), unlike
# run_load_suite.sh's full baseline sweep - add entries as needed.

set -u
cd "$(dirname "$0")/.."

APP_URL="http://app:5000"
export LOADTEST_DOCKER_RUN_OPTS="--network loadtest_default --cpuset-cpus=8-31"
GAP_SECONDS=10

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

if ! docker inspect loadtest-app-1 > /dev/null 2>&1; then
    echo "ERROR: loadtest-app-1 is not running. Start it: (cd deploy/loadtest && docker compose up -d)" >&2
    exit 1
fi

# name:total_players:worker_count:hz:operation:duration_seconds
# operation empty means mousemove-only (drag_interval_seconds=0); hz=0 means idle
# (no mousemove, no operation - see idle_n6 and the hz>0 guard in sustained_load.py)
CONFIGS=(
    "idle_n6:6:5:0::300"
    "mouseonly_n6:6:5:30::300"
    "flip_n4:4:3:30:flip:300"
    "flip_n2:2:1:30:flip:300"
    "pause_only_n6:6:5:30:pause_only:300"
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

SUITE_JSON="$OUT_DIR/suite.json"
echo "[]" > "$SUITE_JSON"

for entry in "${CONFIGS[@]}"; do
    IFS=':' read -r name total workers hz operation duration <<< "$entry"
    if ! should_run "$name"; then
        continue
    fi

    CPU_MAX=$(docker exec loadtest-app-1 cat /sys/fs/cgroup/cpu.max)
    CPU_QUOTA=$(echo "$CPU_MAX" | awk '{print $1}')
    CPU_PERIOD=$(echo "$CPU_MAX" | awk '{print $2}')

    echo ""
    echo "=== $name (total=$total players, hz=$hz, operation=${operation:-none}, ${duration}s, quota=${CPU_QUOTA}/${CPU_PERIOD}) ==="

    docker ps -a --format '{{.ID}} {{.Image}}' | grep test_run_multiprocess | awk '{print $1}' | xargs -r docker rm -f > /dev/null 2>&1

    PARAM_ARGS=(--param "duration_seconds=$duration" --param "mousemove_hz=$hz")
    if [ -n "$operation" ]; then
        PARAM_ARGS+=(--param "drag_interval_seconds=10" --param "operation=$operation")
    else
        PARAM_ARGS+=(--param "drag_interval_seconds=0")
    fi

    STATS_DIR="$OUT_DIR/${name}.stats"
    pipenv run python scripts/collect_container_stats.py loadtest-app-1 loadtest-mongo-1 \
        --output-dir "$STATS_DIR" --interval 1 &
    STATS_PID=$!
    sleep 1  # let the collector open its files before the run starts

    START_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    RESULT_JSON="$OUT_DIR/${name}.json"
    RUN_LOG="$OUT_DIR/${name}.runlog.txt"

    timeout $((duration + 300)) pipenv run python -m tests.performance.cli run \
        tests.performance.sustained_load "$workers" \
        --run-on docker --url "$APP_URL" \
        "${PARAM_ARGS[@]}" \
        --debug --output "$RESULT_JSON" \
        > "$RUN_LOG" 2>&1
    EXIT_CODE=$?
    END_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

    kill "$STATS_PID" 2>/dev/null
    wait "$STATS_PID" 2>/dev/null

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
    'cpu_quota': $CPU_QUOTA, 'cpu_period': $CPU_PERIOD,
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
