"""
Summarize one or two run_load_suite.sh result directories into a Markdown table,
joining each configuration's CloudWatch CPU utilization (looked up by its recorded
UTC start/end time) with the latency/loss numbers already in its result JSON.

Usage:
    uv run --no-project --with boto3 python scripts/summarize_load_suite.py results/baseline
    uv run --no-project --with boto3 python scripts/summarize_load_suite.py results/baseline results/after-fix

Requires AWS credentials for the account staging lives in. Set AWS_PROFILE=asobann
(boto3 does not read --profile; the default profile points at the old prod account
and this script will fail to find the staging cluster if it's used by mistake).
Also requires CloudWatch metrics to have settled - run this a few minutes after the
suite finishes, not immediately.
"""
import json
import sys
from pathlib import Path
from typing import Optional

import boto3


def find_cluster_and_service(ecs_client) -> tuple[str, str]:
    clusters = ecs_client.list_clusters()['clusterArns']
    for cluster_arn in clusters:
        if 'asobann-staging' not in cluster_arn:
            continue
        services = ecs_client.list_services(cluster=cluster_arn)['serviceArns']
        for service_arn in services:
            return cluster_arn.split('/')[-1], service_arn.split('/')[-1]
    raise RuntimeError('could not find an asobann-staging ECS cluster/service')


def cpu_stats(cw_client, cluster: str, service: str, start_utc: str, end_utc: str) -> Optional[dict]:
    from datetime import datetime, timedelta, timezone

    def parse(ts):
        return datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)

    # Skip the first 60s (connections still being established) and the last 20s
    # (workers already winding down) so the window reflects steady-state load.
    start = parse(start_utc) + timedelta(seconds=60)
    end = parse(end_utc) - timedelta(seconds=20)
    if end <= start:
        return None

    resp = cw_client.get_metric_statistics(
        Namespace='AWS/ECS', MetricName='CPUUtilization',
        Dimensions=[
            {'Name': 'ClusterName', 'Value': cluster},
            {'Name': 'ServiceName', 'Value': service},
        ],
        StartTime=start, EndTime=end, Period=30,
        Statistics=['Average', 'Maximum'],
    )
    points = resp['Datapoints']
    if not points:
        return None
    return {
        'avg': sum(p['Average'] for p in points) / len(points),
        'max': max(p['Maximum'] for p in points),
        'n_datapoints': len(points),
    }


def latency_stats(result_path: Path) -> dict:
    if not result_path.exists():
        return {}
    data = json.load(open(result_path))
    result = data.get('result', data)
    timeline = result.get('timeline', [])
    # Drop the final interval. Matching pairs a sent event with the receipt observed by
    # another player, and a message sent near the end of an interval is often observed in
    # the next one (see tests/support/mouse_latency.py). The last interval has no next one
    # to absorb those late receipts, so its loss rate is inflated as a boundary artifact of
    # how the run ends, not a real signal.
    intervals = timeline[:-1] if len(timeline) > 1 else timeline

    p50s, p95s, losses = [], [], []
    min_pairs, max_pairs = None, 0
    for interval in intervals:
        pairs = interval.get('pairs', [])
        if not pairs:
            continue
        n = len(pairs)
        min_pairs = n if min_pairs is None else min(min_pairs, n)
        max_pairs = max(max_pairs, n)
        for p in pairs:
            if p.get('p50') is not None:
                p50s.append(p['p50'])
            if p.get('p95') is not None:
                p95s.append(p['p95'])
            losses.append(p.get('loss_rate', 0))

    flips_not_applied = sum(result.get('flips_not_applied_by_worker', {}).values())

    return {
        'p50': sum(p50s) / len(p50s) if p50s else None,
        'p95': sum(p95s) / len(p95s) if p95s else None,
        'loss': sum(losses) / len(losses) if losses else None,
        'attrition': (max_pairs is not None and min_pairs is not None and min_pairs < max_pairs),
        'flips_not_applied': flips_not_applied,
    }


def fmt(v, suffix='', digits=1):
    if v is None:
        return 'n/a'
    return f'{v:.{digits}f}{suffix}'


def summarize_one(out_dir: Path, cw_client, cluster, service) -> list[dict]:
    suite_path = out_dir / 'suite.json'
    if not suite_path.exists():
        print(f'warning: {suite_path} not found, skipping', file=sys.stderr)
        return []
    configs = json.load(open(suite_path))
    rows = []
    for cfg in configs:
        cpu = cpu_stats(cw_client, cluster, service, cfg['start_utc'], cfg['end_utc'])
        lat = latency_stats(out_dir / f"{cfg['name']}.json")
        rows.append({**cfg, 'cpu': cpu, 'lat': lat})
    return rows


def print_table(label: str, rows: list[dict]):
    print(f'\n## {label}\n')
    print('| 構成 | 人数 | Hz | 操作 | CPU平均 | CPU最大 | p50 | p95 | ロス率 | worker脱落 | flip未反映 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|')
    for r in rows:
        cpu = r['cpu'] or {}
        lat = r['lat'] or {}
        op = r['operation'] or '-'
        attrition = '⚠️あり' if lat.get('attrition') else 'なし'
        exit_flag = '' if r['exit_code'] == 0 else f" (exit={r['exit_code']})"
        print(f"| {r['name']}{exit_flag} | {r['total_players']} | {r['hz']} | {op} | "
              f"{fmt(cpu.get('avg'), '%')} | {fmt(cpu.get('max'), '%')} | "
              f"{fmt(lat.get('p50'), 'ms', 0)} | {fmt(lat.get('p95'), 'ms', 0)} | "
              f"{fmt((lat.get('loss') or 0) * 100, '%')} | {attrition} | "
              f"{lat.get('flips_not_applied', 0)} |")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    session = boto3.Session()
    ecs = session.client('ecs', region_name='us-east-1')
    cw = session.client('cloudwatch', region_name='us-east-1')
    cluster, service = find_cluster_and_service(ecs)
    print(f'(cluster={cluster}, service={service})', file=sys.stderr)

    labeled_rows = []
    for arg in sys.argv[1:]:
        out_dir = Path(arg)
        rows = summarize_one(out_dir, cw, cluster, service)
        labeled_rows.append((out_dir.name, rows))
        print_table(out_dir.name, rows)

    if len(labeled_rows) == 2:
        (label_a, rows_a), (label_b, rows_b) = labeled_rows
        by_name_a = {r['name']: r for r in rows_a}
        by_name_b = {r['name']: r for r in rows_b}
        common = sorted(set(by_name_a) & set(by_name_b))
        if common:
            print(f'\n## 比較: {label_a} → {label_b}\n')
            print('| 構成 | CPU平均(前) | CPU平均(後) | 差 | p50(前) | p50(後) | 差 |')
            print('|---|---|---|---|---|---|---|')
            for name in common:
                a, b = by_name_a[name], by_name_b[name]
                cpu_a = (a['cpu'] or {}).get('avg')
                cpu_b = (b['cpu'] or {}).get('avg')
                p50_a = (a['lat'] or {}).get('p50')
                p50_b = (b['lat'] or {}).get('p50')
                cpu_diff = f'{cpu_b - cpu_a:+.1f}%' if cpu_a is not None and cpu_b is not None else 'n/a'
                p50_diff = f'{p50_b - p50_a:+.0f}ms' if p50_a is not None and p50_b is not None else 'n/a'
                print(f'| {name} | {fmt(cpu_a, "%")} | {fmt(cpu_b, "%")} | {cpu_diff} | '
                      f'{fmt(p50_a, "ms", 0)} | {fmt(p50_b, "ms", 0)} | {p50_diff} |')


if __name__ == '__main__':
    main()
