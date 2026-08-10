"""
Record a container's cgroup v2 cpu.stat once a second while a load test runs, so we can
tell whether it actually saturated its CPU quota (nr_throttled/throttled_usec) instead of
relying on a coarse post-hoc average. See plan.local-profiling.20260810.md §3.3, §4.

This machine uses the systemd cgroup driver, so a container's cpu.stat lives at
/sys/fs/cgroup/system.slice/docker-<full id>.scope/cpu.stat - not under /sys/fs/cgroup/docker/
(the cgroupfs-driver layout). If this script is ever run against a cgroupfs-driver host,
it will fail to find the path; that's intentional (see main()) rather than silently
producing empty output.

Usage:
    python scripts/collect_container_stats.py <container_name_or_id> [<container_name_or_id> ...] \
        --output results/local-xxx/stats_app.csv --interval 1.0

Runs until killed (SIGINT/SIGTERM) or the container(s) stop. Intended to be started in the
background (`&`) around a load test run, one CSV per container.
"""
import argparse
import csv
import signal
import subprocess
import sys
import time
from pathlib import Path

CGROUP_ROOT = Path('/sys/fs/cgroup/system.slice')


def resolve_container_id(name_or_id: str) -> str:
    proc = subprocess.run(['docker', 'inspect', '--format', '{{.Id}}', name_or_id],
                           capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f'docker inspect {name_or_id} failed: {proc.stderr.strip()}')
    return proc.stdout.strip()


def cpu_stat_path(container_id: str) -> Path:
    path = CGROUP_ROOT / f'docker-{container_id}.scope' / 'cpu.stat'
    if not path.exists():
        raise RuntimeError(
            f'{path} not found. This script assumes the systemd cgroup driver '
            f'(docker info | grep "Cgroup Driver"); a cgroupfs-driver host needs a '
            f'different path (/sys/fs/cgroup/docker/<id>/cpu.stat) - not handled here.')
    return path


def read_cpu_stat(path: Path) -> dict:
    stat = {}
    with open(path) as f:
        for line in f:
            key, _, value = line.strip().partition(' ')
            stat[key] = int(value)
    return stat


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('containers', nargs='+', help='container name(s) or id(s)')
    parser.add_argument('--output-dir', required=True,
                        help='directory to write <container_name>.csv into')
    parser.add_argument('--interval', type=float, default=1.0)
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = []
    for name in args.containers:
        container_id = resolve_container_id(name)
        path = cpu_stat_path(container_id)
        csv_path = out_dir / f'{name}.csv'
        f = open(csv_path, 'w', newline='')
        writer = csv.writer(f)
        writer.writerow(['t', 'usage_usec', 'nr_periods', 'nr_throttled', 'throttled_usec'])
        targets.append((name, path, f, writer))
        print(f'recording {name} -> {csv_path}', file=sys.stderr)

    stop = False

    def handle_signal(signum, frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # monotonic, not time.time(): this machine (WSL2) has been observed to step the wall
    # clock forward and back by several seconds mid-run, which would make elapsed-time
    # deltas computed from time.time() unusable for correlating with the load test's
    # own timeline.
    start = time.monotonic()
    try:
        while not stop:
            now = time.monotonic() - start
            for name, path, f, writer in targets:
                try:
                    stat = read_cpu_stat(path)
                except FileNotFoundError:
                    # container has stopped; stop writing but keep the file as-is
                    continue
                writer.writerow([f'{now:.2f}', stat['usage_usec'], stat['nr_periods'],
                                 stat['nr_throttled'], stat['throttled_usec']])
                f.flush()
            time.sleep(args.interval)
    finally:
        for _, _, f, _ in targets:
            f.close()


if __name__ == '__main__':
    main()
