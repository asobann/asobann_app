"""
Local-suite counterpart to summarize_load_suite.py: instead of pulling CPU from
CloudWatch, reads the cgroup cpu.stat CSVs written by collect_container_stats.py during
run_local_suite.sh, and joins them with the same latency/loss numbers from the result
JSON. Output table matches summarize_load_suite.py's format so the two can be read
side by side. See plan.local-profiling.20260810.md §4.

Usage:
    pipenv run python scripts/summarize_local_suite.py results/local-20260810
"""
import csv
import json
import sys
from pathlib import Path
from typing import Optional


def cpu_stats(csv_path: Path, quota: int, period: int) -> Optional[dict]:
    """
    Normalize like ECS CPUUtilization: (CPU time actually used) / (CPU time the quota
    allowed) * 100, over the steady-state window (first 60s and last 20s trimmed - same
    convention as summarize_load_suite.py's CloudWatch window, so the two are comparable).
    """
    if not csv_path.exists():
        return None
    rows = list(csv.DictReader(open(csv_path)))
    if len(rows) < 3:
        return None
    rows = [{'t': float(r['t']), 'usage_usec': int(r['usage_usec']),
             'nr_throttled': int(r['nr_throttled']), 'throttled_usec': int(r['throttled_usec'])}
            for r in rows]
    t_end = rows[-1]['t']
    window = [r for r in rows if 60 <= r['t'] <= t_end - 20]
    if len(window) < 2:
        window = rows  # short run (e.g. a calibration probe) - use everything

    quota_fraction = quota / period
    samples = []
    for a, b in zip(window, window[1:]):
        dt_usec = (b['t'] - a['t']) * 1_000_000
        if dt_usec <= 0:
            continue
        d_usage = b['usage_usec'] - a['usage_usec']
        samples.append(d_usage / (dt_usec * quota_fraction) * 100)

    if not samples:
        return None
    return {
        'avg': sum(samples) / len(samples),
        'max': max(samples),
        'n_samples': len(samples),
        'nr_throttled_total': rows[-1]['nr_throttled'] - rows[0]['nr_throttled'],
        'throttled_seconds': (rows[-1]['throttled_usec'] - rows[0]['throttled_usec']) / 1_000_000,
    }


def latency_stats(result_path: Path) -> dict:
    if not result_path.exists():
        return {}
    data = json.load(open(result_path))
    result = data.get('result', data)
    timeline = result.get('timeline', [])
    intervals = timeline[:-1] if len(timeline) > 1 else timeline

    p50s, p95s, losses = [], [], []
    min_pairs, max_pairs = None, 0
    # sent_count is a per-interval delta (the worker drains and clears its send log each
    # cycle - see collect_and_clear_mouse_send_log), not cumulative, so every interval's
    # value for a sender must be kept and averaged, not just the first.
    sent_by_sender = {}
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
            sent_by_sender.setdefault(p['sender'], []).append(p['sent_count'])

    flips_not_applied = sum(result.get('flips_not_applied_by_worker', {}).values())

    # Achieved send rate vs nominal Hz - see plan §3.2. A run below 95% of nominal is
    # client-bound (the test harness itself couldn't keep up), not a valid CPU sample.
    hz = result.get('params', {}).get('mousemove_hz')
    report_interval = result.get('params', {}).get('report_interval_seconds', 60)
    achieved_hz_ratio = None
    if hz and sent_by_sender:
        per_sender_hz = [sum(counts) / len(counts) / report_interval
                        for counts in sent_by_sender.values()]
        achieved_hz_ratio = (sum(per_sender_hz) / len(per_sender_hz)) / hz

    return {
        'p50': sum(p50s) / len(p50s) if p50s else None,
        'p95': sum(p95s) / len(p95s) if p95s else None,
        'loss': sum(losses) / len(losses) if losses else None,
        'attrition': (max_pairs is not None and min_pairs is not None and min_pairs < max_pairs),
        'flips_not_applied': flips_not_applied,
        'achieved_hz_ratio': achieved_hz_ratio,
    }


def fmt(v, suffix='', digits=1):
    if v is None:
        return 'n/a'
    return f'{v:.{digits}f}{suffix}'


def summarize_one(out_dir: Path) -> list[dict]:
    suite_path = out_dir / 'suite.json'
    if not suite_path.exists():
        print(f'warning: {suite_path} not found, skipping', file=sys.stderr)
        return []
    configs = json.load(open(suite_path))
    rows = []
    for cfg in configs:
        cpu = cpu_stats(out_dir / f"{cfg['name']}.stats" / 'loadtest-app-1.csv',
                        cfg['cpu_quota'], cfg['cpu_period'])
        lat = latency_stats(out_dir / f"{cfg['name']}.json")
        rows.append({**cfg, 'cpu': cpu, 'lat': lat})
    return rows


def print_table(label: str, rows: list[dict]):
    print(f'\n## {label}\n')
    print('| 構成 | 人数 | Hz | 操作 | Q(period/quota) | CPU平均 | CPU最大 | スロットル秒 | '
          'p50 | p95 | ロス率 | 実測Hz比 | worker脱落 |')
    print('|---|---|---|---|---|---|---|---|---|---|---|---|---|')
    for r in rows:
        cpu = r['cpu'] or {}
        lat = r['lat'] or {}
        op = r['operation'] or '-'
        attrition = '⚠️あり' if lat.get('attrition') else 'なし'
        exit_flag = '' if r['exit_code'] == 0 else f" (exit={r['exit_code']})"
        hz_ratio = lat.get('achieved_hz_ratio')
        hz_flag = '' if hz_ratio is None else (' ⚠️client律速' if hz_ratio < 0.95 else '')
        print(f"| {r['name']}{exit_flag} | {r['total_players']} | {r['hz']} | {op} | "
              f"{r['cpu_period']}/{r['cpu_quota']} | "
              f"{fmt(cpu.get('avg'), '%')} | {fmt(cpu.get('max'), '%')} | "
              f"{fmt(cpu.get('throttled_seconds'), 's')} | "
              f"{fmt(lat.get('p50'), 'ms', 0)} | {fmt(lat.get('p95'), 'ms', 0)} | "
              f"{fmt((lat.get('loss') or 0) * 100, '%')} | "
              f"{fmt((hz_ratio or 0) * 100, '%')}{hz_flag} | {attrition} |")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    for arg in sys.argv[1:]:
        out_dir = Path(arg)
        rows = summarize_one(out_dir)
        print_table(out_dir.name, rows)


if __name__ == '__main__':
    main()
