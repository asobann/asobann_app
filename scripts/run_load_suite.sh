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
# Set a config's `remote_systems` field (7th field, e.g. "river:8" or "river:8,pi:4")
# to spread its workers across this machine and one or more others - see framework.py's
# LOADTEST_WORKER_SYSTEMS docstring for why latency is then only meaningful within one
# machine (same_machine_pairs). framework.py itself starts and stops the remote worker
# containers over SSH, once per config (a controller's 'shutdown' command reaches every
# worker including remote ones - see remote_runner.py's worker_server - so a remote
# worker never survives past the config that used it, same as the local ones). The
# remote worker image must already be present on each remote host named in a config
# actually run (docker save | ssh ... | docker load) - this script does not sync it.
#
# Run this detached (nohup ... & disown) - the full suite takes well over an hour.

set -u
cd "$(dirname "$0")/.."

STAGING_URL="https://staging.asobann.yattom.jp"
GAP_SECONDS=90
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

# name:total_players:worker_count:hz:operation:duration_seconds:remote_systems
# operation empty means mousemove-only (drag_interval_seconds=0)
# remote_systems: "name:count[,name:count...]" - workers to run on other machines
# instead of here (see the LOADTEST_WORKER_SYSTEMS comment above), empty means every
# worker runs on this machine. 1 worker can't usefully be split (the only pair left
# would be host<->remote, which same_machine_pairs always drops - zero latency
# samples), so n2 stays local-only.
CONFIGS=(
    "flip_n2:2:1:30:flip:300:"
    "flip_n3:3:2:30:flip:300:"
    "flip_n4:4:3:30:flip:300:"
    "flip_n5:5:4:30:flip:300:"
    "flip_n6:6:5:30:flip:300:"
    "flip_n4_15hz:4:3:15:flip:300:"
    "flip_n6_15hz:6:5:15:flip:300:"
    "mouseonly_n2:2:1:30::300:"
    "mouseonly_n4:4:3:30::300:"
    "mouseonly_n6:6:5:30::300:"
    "flip_n2_dist:2:1:30:flip:300:"
    "flip_n6_dist:6:5:30:flip:300:river:2"
    "flip_n10_dist:10:9:30:flip:300:river:4"
    "flip_n14_dist:14:13:30:flip:300:river:6"
    # R3 (CPU512): CPU256 saturated between n10 (92% avg/99% max) and n14 (worker
    # attrition, p95 202ms->294ms). n10_dist is reused as-is against CPU512 for a direct
    # before/after point; n18/n24/n30 step coarsely past it to find where 512 saturates.
    "flip_n18_dist:18:17:30:flip:300:river:8"
    "flip_n24_dist:24:23:30:flip:300:river:11"
    "flip_n30_dist:30:29:30:flip:300:river:14"
    # river turned out to fall over past ~10 workers of its own (8 cores) - n24/n30_dist
    # above are invalid past that point. These probe how far this machine alone (32
    # cores) scales before finding another machine is unavoidable.
    "flip_n14_local:14:13:30:flip:300:"
    "flip_n18_local:18:17:30:flip:300:"
    "flip_n20_local:20:19:30:flip:300:"
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

# Distinct remote host names (i.e. every name but 'local') referenced by a config's
# remote_systems field, e.g. "river:8,pi:4" -> "river" "pi".
remote_hosts_of() {
    local remote_systems="$1"
    [ -n "$remote_systems" ] || return 0
    local parts
    IFS=',' read -ra parts <<< "$remote_systems"
    for part in "${parts[@]}"; do
        echo "${part%%:*}"
    done
}

# Every distinct remote host across every config actually being run - used only for the
# up-front fail-fast checks below (image present) and for the exit-time safety net.
# Each config still starts its own fresh remote containers, once per config, via
# framework.py's LocalContainers (a controller's 'shutdown' command makes every remote
# worker exit too, so none of them can persist across configs - see the header comment).
all_remote_hosts() {
    local hosts=()
    for entry in "${CONFIGS[@]}"; do
        IFS=':' read -r name total workers hz operation duration remote_systems <<< "$entry"
        should_run "$name" || continue
        while IFS= read -r host; do
            [ -n "$host" ] && hosts+=("$host")
        done < <(remote_hosts_of "$remote_systems")
    done
    printf '%s\n' "${hosts[@]}" | sort -u
}

# framework.py's LocalContainers never removes worker containers itself (see
# start_workers/shutdown there) - it only makes the worker process inside exit, leaving
# an Exited container that would collide with the next config's port binding. This
# script removes them, both locally (below, by ancestor image) and here for one remote
# host at a time.
remove_remote_worker_containers() {
    local host="$1"
    ssh "$host" "docker ps -a --format '{{.ID}} {{.Image}}' | grep $WORKER_IMAGE | awk '{print \$1}' | xargs -r docker rm -f" \
        > /dev/null 2>&1
}

cleanup_all_remote_hosts() {
    while IFS= read -r host; do
        [ -n "$host" ] && remove_remote_worker_containers "$host"
    done < <(all_remote_hosts)
}

echo "building image..."
uv run --no-project --with typer python -m tests.performance.cli build-image --run-on docker --debug \
    > "$OUT_DIR/build.log" 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: image build failed, see $OUT_DIR/build.log" >&2
    exit 1
fi

ANY_REMOTE_HOST=0
while IFS= read -r host; do
    [ -n "$host" ] || continue
    ANY_REMOTE_HOST=1
    if ! ssh "$host" "docker image inspect $WORKER_IMAGE > /dev/null 2>&1"; then
        echo "ERROR: $WORKER_IMAGE not found on $host - transfer it first (docker save | ssh $host docker load)" >&2
        exit 1
    fi
done < <(all_remote_hosts)
if [ "$ANY_REMOTE_HOST" -eq 1 ]; then
    trap cleanup_all_remote_hosts EXIT
fi

SUITE_JSON="$OUT_DIR/suite.json"
echo "[]" > "$SUITE_JSON"

for entry in "${CONFIGS[@]}"; do
    IFS=':' read -r name total workers hz operation duration remote_systems <<< "$entry"
    if ! should_run "$name"; then
        continue
    fi

    echo ""
    echo "=== $name (total=$total players, hz=$hz, operation=${operation:-none}, ${duration}s, remote_systems=${remote_systems:-none}) ==="

    docker ps -a --format '{{.ID}} {{.Image}}' | grep test_run_multiprocess | awk '{print $1}' | xargs -r docker rm -f > /dev/null 2>&1
    while IFS= read -r host; do
        [ -n "$host" ] && remove_remote_worker_containers "$host"
    done < <(remote_hosts_of "$remote_systems")

    REMOTE_TOTAL=0
    if [ -n "$remote_systems" ]; then
        IFS=',' read -ra REMOTE_PARTS <<< "$remote_systems"
        for part in "${REMOTE_PARTS[@]}"; do
            REMOTE_TOTAL=$((REMOTE_TOTAL + ${part#*:}))
        done
    fi
    LOCAL_COUNT=$((workers - REMOTE_TOTAL))
    if [ -n "$remote_systems" ]; then
        WORKER_SYSTEMS_ENV="local:${LOCAL_COUNT},${remote_systems}"
    else
        WORKER_SYSTEMS_ENV=""
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

    LOADTEST_WORKER_SYSTEMS="$WORKER_SYSTEMS_ENV" \
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
    if [ -n "$remote_systems" ]; then
        for part in "${REMOTE_PARTS[@]}"; do
            host="${part%%:*}"
            count="${part#*:}"
            for ((i = 0; i < count; i++)); do
                port=$((50000 + i))
                echo "--- remote $host container port $port ---" >> "$WORKER_LOG"
                ssh "$host" "docker ps -a --filter publish=${port} --format '{{.ID}}' | xargs -r docker logs" \
                    >> "$WORKER_LOG" 2>&1
            done
        done
    fi

    python3 -c "
import json
meta = {
    'name': '$name', 'total_players': $total, 'worker_count': $workers,
    'hz': $hz, 'operation': '$operation', 'duration_seconds': $duration,
    'remote_systems': '$remote_systems',
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
    while IFS= read -r host; do
        [ -n "$host" ] && remove_remote_worker_containers "$host"
    done < <(remote_hosts_of "$remote_systems")

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
