#!/usr/bin/env bash
#
# E2Eを1分のクールダウンを挟んで繰り返し実行し、実行履歴(.e2e-runs/*.json)を
# 溜める。ベースラインの統計を一晩で確保するための道具(#128、
# asobann_docsのworklog 20260820.e2e-observability-study/05-history-stats.md
# の「一晩の連続周回」案)。
#
# 無人実行を前提にしている。標準出力には「回数と経過時間」の1行だけを出す。
# 何か問題があれば標準エラーへ短く書き、詳細は .e2e-runs/overnight-logs/
# 以下のログファイルに残す。
#
# ビルドは開始時に1回だけ(以降は --no-build で使い回す)。src/やtests/を
# 直しながら回したいときはこのスクリプトを使わないこと(直しても反映されない)。
#
# 使い方:
#   ./scripts/run_e2e_overnight.sh        # 既定8時間
#   ./scripts/run_e2e_overnight.sh 10     # 10時間
#
# 終了条件:
#   - 開始からの経過が指定時間を超えたら、実行中のスイートを打ち切らずに、
#     その完了を待ってから終わる(締切はループの先頭でだけ見る)
#   - 3回連続で実行履歴のJSONが増えなければ中止する。pytest_sessionfinishは
#     テストの合否に関わらず必ずJSONを書くので、「JSONが増えない」は
#     ビルドやmongo接続などテストの中身以前で毎回死んでいる、という
#     強いシグナルになる。続けても無意味なので打ち切る
#   - 1回あたり1時間(通常は10〜15分で終わる)を超えたら、ハングしたと見なして
#     そのスイートを打ち切り、次に進む(3回連続の判定に含める)

set -uo pipefail  # -e は使わない。1回の失敗でループ全体を止めない

HOURS=${1:-8}
case "$HOURS" in
    ''|*[!0-9]*)
        echo "使い方: $0 [時間数(1以上の整数)]。'$HOURS' は数値ではない" >&2
        exit 1
        ;;
esac
if [ "$HOURS" -lt 1 ]; then
    echo "時間数は1以上にすること: '$HOURS'" >&2
    exit 1
fi

if ! command -v timeout >/dev/null 2>&1; then
    echo "timeout コマンドが無い。中止する" >&2
    exit 1
fi

COOLDOWN_SECONDS=60
PER_RUN_TIMEOUT_SECONDS=3600
MAX_CONSECUTIVE_FAILURES=3

cd "$(dirname "$0")/.."

LOG_SESSION_DIR=".e2e-runs/overnight-logs/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$LOG_SESSION_DIR"

fmt_elapsed() {
    local total_seconds="$1"
    printf '%dh%02dm' "$((total_seconds / 3600))" "$(((total_seconds % 3600) / 60))"
}

echo "[$(date '+%H:%M:%S')] 初回ビルド" >&2
if ! ./scripts/build_e2e_image.sh > "$LOG_SESSION_DIR/000_build.log" 2>&1; then
    echo "初回ビルドに失敗した。ログ: $LOG_SESSION_DIR/000_build.log。中止する" >&2
    exit 1
fi

start_epoch=$(date +%s)
deadline_epoch=$((start_epoch + HOURS * 3600))
count=0
consecutive_failures=0

while :; do
    now_epoch=$(date +%s)
    if [ "$now_epoch" -ge "$deadline_epoch" ]; then
        break
    fi

    count=$((count + 1))
    iter_log=$(printf '%s/%03d.log' "$LOG_SESSION_DIR" "$count")

    before=$(ls .e2e-runs/*.json 2>/dev/null | wc -l)
    timeout "$PER_RUN_TIMEOUT_SECONDS" \
        ./scripts/run_e2e.sh --no-build --tolerate-flaky > "$iter_log" 2>&1
    rc=$?
    after=$(ls .e2e-runs/*.json 2>/dev/null | wc -l)

    elapsed=$(( $(date +%s) - start_epoch ))

    if [ "$after" -gt "$before" ]; then
        consecutive_failures=0
        echo "[$count] 経過 $(fmt_elapsed "$elapsed")"
    else
        consecutive_failures=$((consecutive_failures + 1))
        if [ "$rc" -eq 124 ]; then
            echo "[$count回目] タイムアウト(${PER_RUN_TIMEOUT_SECONDS}秒)。履歴なし${consecutive_failures}回連続。ログ: $iter_log" >&2
        else
            echo "[$count回目] 実行履歴が増えなかった(終了コード $rc)。履歴なし${consecutive_failures}回連続。ログ: $iter_log" >&2
        fi
        # stdoutは常に「回数と経過時間」の1行だけにする(スクリプト冒頭のコメント参照)。
        # 補足(連続失敗回数など)はstderrにだけ出す。
        echo "[$count] 経過 $(fmt_elapsed "$elapsed")"

        if [ "$consecutive_failures" -ge "$MAX_CONSECUTIVE_FAILURES" ]; then
            echo "${MAX_CONSECUTIVE_FAILURES}回連続でスイートが完走していない。続けても意味が無いので中止する" >&2
            exit 1
        fi
    fi

    sleep "$COOLDOWN_SECONDS"
done

total_elapsed=$(( $(date +%s) - start_epoch ))
echo "終了: 合計${count}回、経過 $(fmt_elapsed "$total_elapsed")"
