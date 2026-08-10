#!/usr/bin/env bash
# Phase 4 of plan.local-profiling.20260810.md: run the calibrated load configs and take
# a py-spy CPU profile of loadtest-app-1 during each one, alongside the same cpu.stat
# recording run_local_suite.sh does. Assumes:
#   - deploy/loadtest is already `docker compose up -d`
#   - loadtest-app-1's quota is already calibrated (scripts/set_app_cpu.sh) - this
#     script does not change it, only records whatever is live
#   - `docker build -t loadtest-pyspy -f deploy/loadtest/Dockerfile.pyspy deploy/loadtest`
#     has been run
#
# Usage: ./scripts/run_profile_suite.sh <label> [config_name...]

set -u
cd "$(dirname "$0")/.."

APP_URL="http://app:5000"
export LOADTEST_DOCKER_RUN_OPTS="--network loadtest_default --cpuset-cpus=8-31"
GAP_SECONDS=15
PYSPY_STARTUP_DELAY=20   # let the load ramp up before sampling starts
PYSPY_CPUSET="4"         # off app(0)/mongo(2)/workers(8-31) - see plan §3.1

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
    echo "ERROR: loadtest-app-1 is not running." >&2
    exit 1
fi
if ! docker image inspect loadtest-pyspy > /dev/null 2>&1; then
    echo "ERROR: loadtest-pyspy image not built." >&2
    exit 1
fi

# name:total_players:worker_count:hz:operation:duration_seconds
CONFIGS=(
    "idle_n6:6:5:0::300"
    "mouseonly_n6:6:5:30::300"
    "flip_n4:4:3:30:flip:300"
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
    echo "=== $name (total=$total, hz=$hz, operation=${operation:-none}, ${duration}s, quota=${CPU_QUOTA}/${CPU_PERIOD}) ==="

    docker ps -a --format '{{.ID}} {{.Image}}' | grep test_run_multiprocess | awk '{print $1}' | xargs -r docker rm -f > /dev/null 2>&1

    PARAM_ARGS=(--param "duration_seconds=$duration" --param "mousemove_hz=$hz" --param "report_interval_seconds=60")
    if [ -n "$operation" ]; then
        PARAM_ARGS+=(--param "drag_interval_seconds=10" --param "operation=$operation")
    else
        PARAM_ARGS+=(--param "drag_interval_seconds=0")
    fi

    STATS_DIR="$OUT_DIR/${name}.stats"
    pipenv run python scripts/collect_container_stats.py loadtest-app-1 loadtest-mongo-1 \
        --output-dir "$STATS_DIR" --interval 1 &
    STATS_PID=$!
    sleep 1

    RESULT_JSON="$OUT_DIR/${name}.json"
    RUN_LOG="$OUT_DIR/${name}.runlog.txt"

    pipenv run python -m tests.performance.cli run tests.performance.sustained_load "$workers" \
        --run-on docker --url "$APP_URL" \
        "${PARAM_ARGS[@]}" \
        --debug --output "$RESULT_JSON" \
        > "$RUN_LOG" 2>&1 &
    LOAD_PID=$!

    sleep "$PYSPY_STARTUP_DELAY"
    PYSPY_DURATION=$((duration - PYSPY_STARTUP_DELAY - 15))
    echo "recording py-spy for ${PYSPY_DURATION}s..."
    docker run --rm --pid=container:loadtest-app-1 --cap-add=SYS_PTRACE \
        --cpuset-cpus="$PYSPY_CPUSET" -v "$PWD/$OUT_DIR:/out" loadtest-pyspy \
        record --pid 1 --rate 100 --nonblocking --duration "$PYSPY_DURATION" \
        --format speedscope -o "/out/${name}.profile.json" > "$OUT_DIR/${name}.pyspy.log" 2>&1

    wait "$LOAD_PID"
    EXIT_CODE=$?
    kill "$STATS_PID" 2>/dev/null
    wait "$STATS_PID" 2>/dev/null

    python3 -c "
import json
meta = {
    'name': '$name', 'total_players': $total, 'worker_count': $workers,
    'hz': $hz, 'operation': '$operation', 'duration_seconds': $duration,
    'cpu_quota': $CPU_QUOTA, 'cpu_period': $CPU_PERIOD, 'exit_code': $EXIT_CODE,
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
        echo "$name done"
    fi

    docker ps -a --format '{{.ID}} {{.Image}}' | grep test_run_multiprocess | awk '{print $1}' | xargs -r docker rm -f > /dev/null 2>&1

    echo "waiting ${GAP_SECONDS}s before next configuration..."
    sleep "$GAP_SECONDS"
done

echo ""
echo "profile suite '$LABEL' complete. See $OUT_DIR/suite.json"
