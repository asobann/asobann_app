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
#
# 例:
#   ./scripts/run_e2e.sh                                  # 全件
#   ./scripts/run_e2e.sh tests/e2e/test_component.py
#   ./scripts/run_e2e.sh --dev -k TestGlued               # テストを直しながら速く回す
#   ./scripts/run_e2e.sh -p no:randomly -s                # 順序固定＋print表示（切り分け用）
#   ./scripts/run_e2e.sh --randomly-seed=12345            # 落ちた順序を再現する
#   ./scripts/run_e2e.sh --tolerate-flaky                 # CIと同じ扱い
#
# 既定で -v を渡すので、テスト名が1件ずつ出る。簡潔にしたいときは -q を足す
# （pytestの -q と -v は打ち消し合う）。
#
# 失敗したテストのスクリーンショットは .e2e-artifacts/<日時>/ に残る（.gitignore済み）。

set -euo pipefail

source "$(dirname "$0")/lib/container_tests.sh"

TOLERATE_FLAKY=no

# --tolerate-flaky はこのスクリプト固有。共通パーサに渡して、他のフラグと同じ
# 扱いにする（先頭のみ解釈し、`--` 以降には手を出さない）。
handle_e2e_flag() {
    case "$1" in
        --tolerate-flaky) TOLERATE_FLAKY=yes; return 0 ;;
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

# 切り分け用のつまみ。ホスト側で設定されていればコンテナへ渡す。
for name in ASOBANN_E2E_SLOWMO; do
    if [ -n "${!name:-}" ]; then
        envs+=(-e "$name=${!name}")
    fi
done

run_pytest "${envs[@]}" -- "$@"
