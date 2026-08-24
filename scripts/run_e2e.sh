#!/usr/bin/env bash
#
# E2Eテストをコンテナで実行する。
#
# E2Eはホストでは動かない。config_test.py が mongo:27017 をハードコードしており、
# firefox も geckodriver も要る。本番イメージをベースにしたE2Eイメージを docker 上で
# 動かす。設計上の前提は tests/e2e/README.md を参照。
#
# 共通の足回り（mongo起動・イメージ用意・docker run）は scripts/lib/container_tests.sh。
#
# 使い方:
#   ./scripts/run_e2e.sh [オプション] [pytestに渡す引数...]
#
# オプション（このスクリプトが解釈するもの。以降はすべて pytest に素通しする）:
#   --no-build        イメージのビルドを省く。ビルド済みのものを使う
#   --dev             tests/ をホストから読み取り専用でマウントし、ビルドを省く。
#                     テストコードを直しながら回すとき用。
#                     **src/（アプリ側）はイメージのままなので注意**
#   --tolerate-flaky  既知フレーキーの失敗を終了コードに含めない（CI用）。
#                     一覧に無い失敗が1件でもあれば従来どおり失敗する
#   --watch           人間が観戦参加するモード。卓ができた時点でURLを表示して止まる。
#                     ブラウザで開くと観戦者として卓が見える。Enterで先へ進む。
#                     **1テストを単独で実行するときに使うもの**（テストごとに止まる）。
#                     詳細は tests/e2e/README.md の「実行中の卓を人間が見る」
#
# 環境変数:
#   ASOBANN_E2E_SLOWMO=秒数  操作の合間に待つ。結果が不安定化する可能性がある
#   ASOBANN_E2E_BROWSER=chrome  Firefoxのかわりに Chromium で走らせる（試し。既定 firefox）
#
# 例:
#   ./scripts/run_e2e.sh                                  # 全件
#   ./scripts/run_e2e.sh tests/e2e/test_component.py
#   ./scripts/run_e2e.sh --dev -k TestGlued               # テストを直しながら速く回す
#   ./scripts/run_e2e.sh -p no:randomly -s                # 順序固定＋print表示（切り分け用）
#   ./scripts/run_e2e.sh --randomly-seed=12345            # 落ちた順序を再現する
#   ./scripts/run_e2e.sh --tolerate-flaky                 # CIと同じ扱い
#   ./scripts/run_e2e.sh --watch --dev -p no:randomly \
#       tests/e2e/test_component.py::TestGlued::test_flipped_and_text_hides
#   ASOBANN_E2E_BROWSER=chrome ./scripts/run_e2e.sh       # Chromiumで全件
#
# 既定で -v を渡すので、テスト名が1件ずつ出る。簡潔にしたいときは -q を足す
# （pytestの -q と -v は打ち消し合う）。
#
# 失敗したテストのスクリーンショットは .e2e-artifacts/<日時>/ に残る（.gitignore済み）。

set -euo pipefail

source "$(dirname "$0")/lib/container_tests.sh"

TOLERATE_FLAKY=no
WATCH=no

# --tolerate-flaky と --watch はこのスクリプト固有。共通パーサに渡して、他のフラグと
# 同じ扱いにする（先頭のみ解釈し、`--` 以降には手を出さない）。
handle_e2e_flag() {
    case "$1" in
        --tolerate-flaky) TOLERATE_FLAKY=yes; return 0 ;;
        --watch)          WATCH=yes; return 0 ;;
        *)                return 1 ;;
    esac
}
EXTRA_FLAG_HANDLER=handle_e2e_flag

parse_common_flags "$@"
default_targets tests/e2e -- ${REMAINING_ARGS+"${REMAINING_ARGS[@]}"}
set -- "${TARGETS[@]}"

ensure_mongo
ensure_image

envs=(-e MOZ_HEADLESS=1)
[ "$TOLERATE_FLAKY" = yes ] && envs+=(-e E2E_TOLERATE_KNOWN_FLAKY=1)

# 観戦モード。3つ全部が揃わないと成立しない。
#   -p 10011:10011  ホストのブラウザからテストサーバへ届くようにする。
#                   **ホスト側のポートをずらしてはいけない**。テストが持っている
#                   URLは http://localhost:10011/tables/<名前> で、それをそのまま
#                   人間に貼ってもらう
#   -i              コンテナの標準入力を繋ぐ。無いと input() が即EOFになる
#   -s              pytestの出力キャプチャを止める。無いとURLの表示も input() も
#                   実行中には効かない
if [ "$WATCH" = yes ]; then
    DOCKER_EXTRA+=(-p 10011:10011 -i)
    envs+=(-e ASOBANN_E2E_WATCH=1)
    set -- -s "$@"
fi

# 切り分け用のつまみ。ホスト側で設定されていればコンテナへ渡す。
for name in ASOBANN_E2E_SLOWMO ASOBANN_E2E_BROWSER; do
    if [ -n "${!name:-}" ]; then
        envs+=(-e "$name=${!name}")
    fi
done

run_pytest "${envs[@]}" -- "$@"
