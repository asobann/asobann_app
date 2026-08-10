#!/usr/bin/env bash
# Change loadtest-app-1's CPU quota live, without restarting the container (mongo
# connection etc. stays warm) - see plan.local-profiling.20260810.md §2.3.
#
# Usage: ./scripts/set_app_cpu.sh <period_usec> <quota_usec>
# Example: ./scripts/set_app_cpu.sh 80000 6640   # Q=0.083, 80ms period

set -eu
if [ $# -ne 2 ]; then
    echo "usage: $0 <period_usec> <quota_usec>" >&2
    exit 1
fi
PERIOD="$1"
QUOTA="$2"
docker update --cpu-period="$PERIOD" --cpu-quota="$QUOTA" loadtest-app-1 > /dev/null
echo -n "applied: "
docker exec loadtest-app-1 cat /sys/fs/cgroup/cpu.max
