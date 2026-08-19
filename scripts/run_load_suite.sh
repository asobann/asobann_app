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
# Set LOADTEST_REMOTE_HOST (an SSH-reachable host/alias, e.g. "river") to spread the
# workers of any config whose `external_workers` field is > 0 across this machine and
# that one - see framework.py's LOADTEST_EXTRA_WORKERS docstring for why latency is
# then only meaningful within one machine (same_machine_pairs). This script starts and
# stops the remote worker containers itself, once per config (a controller's 'shutdown'
# command reaches every worker including remote ones - see remote_runner.py's
# worker_server - so a remote worker never survives past the config that used it, same
# as the local ones). The remote worker image must already be present there
# (docker save | ssh ... | docker load) - this script does not sync it.
#
# Run this detached (nohup ... & disown) - the full suite takes well over an hour.

set -u
cd "$(dirname "$0")/.."

STAGING_URL="https://staging.asobann.yattom.jp"
GAP_SECONDS=90
REMOTE_HOST="${LOADTEST_REMOTE_HOST:-}"
REMOTE_PORT_BASE=50000
# Matches tests/performance/framework.py's WORKER_NAME - keep in sync.
WORKER_IMAGE="test_run_multiprocess_in_container_worker"

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

# name:total_players:worker_count:hz:operation:duration_seconds:external_workers
# operation empty means mousemove-only (drag_interval_seconds=0)
# external_workers: how many of worker_count run on LOADTEST_REMOTE_HOST rather than
# here. 1 worker can't usefully be split (the only pair left would be host<->remote,
# which same_machine_pairs always drops - zero latency samples), so n2 stays local-only.
CONFIGS=(
    "flip_n2:2:1:30:flip:300:0"
    "flip_n3:3:2:30:flip:300:0"
    "flip_n4:4:3:30:flip:300:0"
    "flip_n5:5:4:30:flip:300:0"
    "flip_n6:6:5:30:flip:300:0"
    "flip_n4_15hz:4:3:15:flip:300:0"
    "flip_n6_15hz:6:5:15:flip:300:0"
    "mouseonly_n2:2:1:30::300:0"
    "mouseonly_n4:4:3:30::300:0"
    "mouseonly_n6:6:5:30::300:0"
    "flip_n2_dist:2:1:30:flip:300:0"
    "flip_n6_dist:6:5:30:flip:300:2"
    "flip_n10_dist:10:9:30:flip:300:4"
    "flip_n14_dist:14:13:30:flip:300:6"
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

# Largest external_workers among the configs actually being run - used only for the
# up-front fail-fast checks below (host set, image present). Each config still starts
# its own fresh remote containers; see the header comment for why they can't persist.
max_external_workers() {
    local max=0
    for entry in "${CONFIGS[@]}"; do
        IFS=':' read -r name total workers hz operation duration external <<< "$entry"
        should_run "$name" || continue
        [ "$external" -gt "$max" ] && max=$external
    done
    echo "$max"
}

start_remote_workers() {
    local n="$1"
    echo "starting $n remote worker(s) on $REMOTE_HOST (ports $REMOTE_PORT_BASE..$((REMOTE_PORT_BASE + n - 1)))..."
    for ((i = 0; i < n; i++)); do
        local port=$((REMOTE_PORT_BASE + i))
        ssh "$REMOTE_HOST" "docker run -d -p ${port}:${port} -e PORT=${port} ${WORKER_IMAGE}" > /dev/null
    done
    for ((i = 0; i < n; i++)); do
        local port=$((REMOTE_PORT_BASE + i))
        for attempt in $(seq 1 30); do
            (exec 3<>"/dev/tcp/${REMOTE_HOST}/${port}") 2>/dev/null && { exec 3>&-; break; }
            sleep 1
        done
    done
}

stop_remote_workers() {
    [ -n "$REMOTE_HOST" ] || return 0
    ssh "$REMOTE_HOST" "docker ps -a --format '{{.ID}} {{.Image}}' | grep $WORKER_IMAGE | awk '{print \$1}' | xargs -r docker rm -f" \
        > /dev/null 2>&1
}

echo "building image..."
uv run --no-project --with typer python -m tests.performance.cli build-image --run-on docker --debug \
    > "$OUT_DIR/build.log" 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: image build failed, see $OUT_DIR/build.log" >&2
    exit 1
fi

MAX_EXTERNAL=$(max_external_workers)
if [ "$MAX_EXTERNAL" -gt 0 ]; then
    if [ -z "$REMOTE_HOST" ]; then
        echo "ERROR: a requested config needs $MAX_EXTERNAL remote worker(s) but LOADTEST_REMOTE_HOST is not set" >&2
        exit 1
    fi
    if ! ssh "$REMOTE_HOST" "docker image inspect $WORKER_IMAGE > /dev/null 2>&1"; then
        echo "ERROR: $WORKER_IMAGE not found on $REMOTE_HOST - transfer it first (docker save | ssh $REMOTE_HOST docker load)" >&2
        exit 1
    fi
    trap stop_remote_workers EXIT
fi

SUITE_JSON="$OUT_DIR/suite.json"
echo "[]" > "$SUITE_JSON"

for entry in "${CONFIGS[@]}"; do
    IFS=':' read -r name total workers hz operation duration external <<< "$entry"
    if ! should_run "$name"; then
        continue
    fi

    echo ""
    echo "=== $name (total=$total players, hz=$hz, operation=${operation:-none}, ${duration}s, external=$external) ==="

    docker ps -a --format '{{.ID}} {{.Image}}' | grep test_run_multiprocess | awk '{print $1}' | xargs -r docker rm -f > /dev/null 2>&1
    stop_remote_workers

    EXTRA_WORKERS_ENV=""
    if [ "$external" -gt 0 ]; then
        start_remote_workers "$external"
        entries=()
        for ((i = 0; i < external; i++)); do
            entries+=("${REMOTE_HOST}:$((REMOTE_PORT_BASE + i))")
        done
        EXTRA_WORKERS_ENV=$(IFS=,; echo "${entries[*]}")
    fi

    PARAM_ARGS=(--param "duration_seconds=$duration" --param "mousemove_hz=$hz")
    if [ -n "$operation" ]; then
        PARAM_ARGS+=(--param "drag_interval_seconds=10" --param "operation=$operation")
    else
        PARAM_ARGS+=(--param "drag_interval_seconds=0")
    fi

    START_UTC=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    RESULT_JSON="$OUT_DIR/${name}.json"
    RUN_LOG="$OUT_DIR/${name}.runlog.txt"

    LOADTEST_EXTRA_WORKERS="$EXTRA_WORKERS_ENV" \
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
    if [ "$external" -gt 0 ]; then
        for ((i = 0; i < external; i++)); do
            port=$((REMOTE_PORT_BASE + i))
            echo "--- remote container port $port ---" >> "$WORKER_LOG"
            ssh "$REMOTE_HOST" "docker ps -a --filter publish=${port} --format '{{.ID}}' | xargs -r docker logs" \
                >> "$WORKER_LOG" 2>&1
        done
    fi

    python3 -c "
import json
meta = {
    'name': '$name', 'total_players': $total, 'worker_count': $workers,
    'hz': $hz, 'operation': '$operation', 'duration_seconds': $duration,
    'external_workers': $external,
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
    stop_remote_workers

    echo "waiting ${GAP_SECONDS}s before next configuration..."
    sleep "$GAP_SECONDS"
done

echo ""
echo "suite '$LABEL' complete. See $OUT_DIR/suite.json"

# CloudWatch's ECS CPUUtilization metric lags a few minutes behind real time - the last
# config's window may not have datapoints yet if queried immediately. summarize_load_suite.py
# itself only queries the recorded windows (never "now"), so waiting here is what makes the
# most recent config's numbers actually show up instead of "n/a".
echo "waiting for CloudWatch metrics to settle..."
sleep 120
AWS_PROFILE=asobann uv run --no-project --with boto3 python scripts/summarize_load_suite.py "$OUT_DIR" \
    | tee "$OUT_DIR/summary.md"
