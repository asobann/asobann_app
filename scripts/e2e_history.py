"""
E2Eの実行履歴(tests/e2e/conftest.pyが書く .e2e-runs/<run_id>.json)をSQLiteに
取り込む。「常連フレーキーの中に直せるものがあるか」「フレーキーだと思っている
テストが実は壊れているか」を判定するための生データを溜める(#128)。分析はまだ
無い(活用は後回し。まず漏らさず残す)。

Usage:
    uv run --no-project python scripts/e2e_history.py ingest              # .e2e-runs/*.json を取り込む
    uv run --no-project python scripts/e2e_history.py ingest <path.json>  # 個別ファイルを取り込む
    uv run --no-project python scripts/e2e_history.py fetch-ci            # 日次CIのartifactを取り込む
    uv run --no-project python scripts/e2e_history.py fetch-ci --limit 20

fetch-ci は `gh`(GitHub CLI、要ログイン済み)を使う。日次CIワークフロー
(.github/workflows/e2e-nightly.yml)が e2e-history という名前でartifactに
上げているJSONを、実行ごとに一時ディレクトリへ落として取り込む。

DBは .e2e-runs/history.sqlite3(gitignore済み、JSONと同じ扱い)。
run_id(UUID4)が主キーなので、同じJSONを何度取り込んでも二重に入らない
(CI artifactを再取得しても安全)。
"""
import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
HISTORY_DIR = APP_DIR / '.e2e-runs'
DB_PATH = HISTORY_DIR / 'history.sqlite3'
ARTIFACT_NAME = 'e2e-history'
WORKFLOW_NAME = 'E2E (日次)'

SCHEMA = """
CREATE TABLE IF NOT EXISTS run (
    run_id                TEXT PRIMARY KEY,
    started_at            TEXT NOT NULL,
    finished_at           TEXT,
    origin                TEXT NOT NULL,
    machine               TEXT,
    cpu_count             INTEGER,
    git_sha               TEXT,
    git_dirty             INTEGER,
    e2e_image             TEXT,
    dev_mode              INTEGER,
    randomly_seed         INTEGER,
    pytest_args           TEXT,
    reruns                INTEGER,
    known_flaky_reruns    INTEGER,
    reruns_delay          REAL,
    tolerate_known_flaky  INTEGER,
    known_flaky_list      TEXT,
    headless              INTEGER,
    slowmo                REAL,
    browser               TEXT,
    browser_version       TEXT,
    exit_status            INTEGER,
    source_file           TEXT
);

CREATE TABLE IF NOT EXISTS test_result (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id        TEXT NOT NULL REFERENCES run(run_id),
    nodeid        TEXT NOT NULL,
    order_index   INTEGER NOT NULL,
    final_outcome TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS attempt (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    test_result_id  INTEGER NOT NULL REFERENCES test_result(id),
    attempt_number  INTEGER NOT NULL,
    phase_failed    TEXT,
    outcome         TEXT NOT NULL,
    duration_s      REAL,
    started_at      TEXT,
    failure_summary TEXT
);

CREATE INDEX IF NOT EXISTS idx_test_result_run ON test_result(run_id);
CREATE INDEX IF NOT EXISTS idx_test_result_nodeid ON test_result(nodeid);
CREATE INDEX IF NOT EXISTS idx_attempt_test_result ON attempt(test_result_id);
"""


def connect():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def ingest_file(conn, path: Path) -> bool:
    """1件のrun JSONをDBへ入れる。既に入っていればFalse、新規に入れたらTrue。"""
    data = json.loads(path.read_text(encoding='utf-8'))
    run = data['run']
    run_id = run['run_id']

    if conn.execute('SELECT 1 FROM run WHERE run_id = ?', (run_id,)).fetchone():
        return False

    conn.execute(
        """
        INSERT INTO run (
            run_id, started_at, finished_at, origin, machine, cpu_count,
            git_sha, git_dirty, e2e_image, dev_mode, randomly_seed, pytest_args,
            reruns, known_flaky_reruns, reruns_delay, tolerate_known_flaky,
            known_flaky_list, headless, slowmo, browser, browser_version,
            exit_status, source_file
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id, run.get('started_at'), run.get('finished_at'), run['origin'],
            run.get('machine'), run.get('cpu_count'), run.get('git_sha'),
            int(bool(run.get('git_dirty'))), run.get('e2e_image'),
            int(bool(run.get('dev_mode'))), run.get('randomly_seed'),
            json.dumps(run.get('pytest_args'), ensure_ascii=False),
            run.get('reruns'), run.get('known_flaky_reruns'), run.get('reruns_delay'),
            int(bool(run.get('tolerate_known_flaky'))),
            json.dumps(run.get('known_flaky_list'), ensure_ascii=False),
            int(bool(run.get('headless'))), run.get('slowmo'), run.get('browser'),
            run.get('browser_version'), run.get('exit_status'), str(path),
        ),
    )

    for result in data['results']:
        cur = conn.execute(
            'INSERT INTO test_result (run_id, nodeid, order_index, final_outcome) VALUES (?, ?, ?, ?)',
            (run_id, result['nodeid'], result['order_index'], result['final_outcome']),
        )
        test_result_id = cur.lastrowid
        for attempt in result['attempts']:
            conn.execute(
                """
                INSERT INTO attempt (
                    test_result_id, attempt_number, phase_failed, outcome,
                    duration_s, started_at, failure_summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    test_result_id, attempt['attempt'], attempt.get('phase_failed'),
                    attempt['outcome'], attempt.get('duration_s'),
                    attempt.get('started_at'), attempt.get('failure_summary'),
                ),
            )
    conn.commit()
    return True


def cmd_ingest(args):
    conn = connect()
    if args.path:
        paths = [Path(args.path)]
    else:
        paths = sorted(HISTORY_DIR.glob('*.json'))
    if not paths:
        print(f'取り込むJSONが無い({HISTORY_DIR})')
        return
    new, seen = 0, 0
    for path in paths:
        seen += 1
        if ingest_file(conn, path):
            new += 1
            print(f'取り込んだ: {path.name}')
        else:
            print(f'既に取り込み済み: {path.name}')
    print(f'{seen}件中{new}件を新規に取り込んだ({DB_PATH})')


def cmd_fetch_ci(args):
    conn = connect()
    result = subprocess.run(
        ['gh', 'run', 'list', '--workflow', WORKFLOW_NAME, '--limit', str(args.limit),
         '--json', 'databaseId,status,conclusion'],
        capture_output=True, text=True, cwd=APP_DIR,
    )
    if result.returncode != 0:
        print(f'gh run list に失敗した: {result.stderr}', file=sys.stderr)
        sys.exit(1)
    runs = json.loads(result.stdout)

    new_total, seen_total = 0, 0
    for run in runs:
        if run['status'] != 'completed':
            continue
        run_db_id = run['databaseId']
        with tempfile.TemporaryDirectory() as tmp:
            dl = subprocess.run(
                ['gh', 'run', 'download', str(run_db_id), '-n', ARTIFACT_NAME, '-D', tmp],
                capture_output=True, text=True, cwd=APP_DIR,
            )
            if dl.returncode != 0:
                # artifactが無い(90日超過で失効、またはif-no-files-foundで
                # そもそも上がらなかった)実行はスキップする。
                continue
            for path in sorted(Path(tmp).glob('*.json')):
                seen_total += 1
                if ingest_file(conn, path):
                    new_total += 1
                    print(f'取り込んだ: run {run_db_id} / {path.name}')
    print(f'CI実行{len(runs)}件を確認し、artifact {seen_total}件中{new_total}件を新規に取り込んだ({DB_PATH})')


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)

    p_ingest = sub.add_parser('ingest', help='.e2e-runs/*.json (または指定したファイル) を取り込む')
    p_ingest.add_argument('path', nargs='?', help='個別ファイルを取り込むときのパス。省略時は .e2e-runs/*.json 全部')
    p_ingest.set_defaults(func=cmd_ingest)

    p_fetch = sub.add_parser('fetch-ci', help='日次CIのartifactをghで取得して取り込む')
    p_fetch.add_argument('--limit', type=int, default=30, help='遡る実行回数(既定30)')
    p_fetch.set_defaults(func=cmd_fetch_ci)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
