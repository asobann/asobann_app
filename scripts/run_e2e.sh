#!/usr/bin/env bash
#
# E2Eテストをコンテナで実行する。
#
# E2Eはホストでは動かない。config_test.py が mongo:27017 をハードコードしており、
# firefox も geckodriver も要る。本番イメージをベースにしたE2Eイメージを docker 上で
# 動かす。設計上の前提は tests/e2e/README.md を参照。
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
# 既定で -q を渡すので、詳細表示にしたいときは -v を足す（pytestの -q と -v は
# 打ち消し合う）。

set -euo pipefail

# 自分の位置からリポジトリのルートを引く。gitに答えさせるので、どこから
# 実行しても、チェックアウト先がどこにあっても正しい。
APP_DIR=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)

E2E_IMAGE=${E2E_IMAGE:-asobann-e2e:local}
NETWORK=${NETWORK:-loadtest_default}
MONGO_COMPOSE="$APP_DIR/deploy/loadtest/docker-compose.yml"
MONGO_CONTAINER=loadtest-mongo-1

BUILD=yes
DEV=no
TOLERATE_FLAKY=no

while [ $# -gt 0 ]; do
    case "$1" in
        --no-build)       BUILD=no; shift ;;
        --dev)            DEV=yes; BUILD=no; shift ;;
        --tolerate-flaky) TOLERATE_FLAKY=yes; shift ;;
        --)               shift; break ;;
        *)                break ;;
    esac
done

# 対象を指定しなければ tests/e2e 全体。
if [ $# -eq 0 ]; then
    set -- tests/e2e
fi

# E2Eは config_test.py のハードコードにより mongo:27017 を見る。deploy/loadtest の
# composeがサービス名 mongo でそれを提供するので、それを使い回す。
if ! docker ps --format '{{.Names}}' | grep -qx "$MONGO_CONTAINER"; then
    echo "mongo が起動していないので起動する"
    docker compose -f "$MONGO_COMPOSE" up -d mongo
fi

if [ "$BUILD" = yes ]; then
    "$APP_DIR/scripts/build_e2e_image.sh"
elif ! docker image inspect "$E2E_IMAGE" >/dev/null 2>&1; then
    echo "$E2E_IMAGE が無い。--no-build / --dev を外すか、" >&2
    echo "scripts/build_e2e_image.sh を先に実行すること" >&2
    exit 1
fi

envs=(-e MOZ_HEADLESS=1)
[ "$TOLERATE_FLAKY" = yes ] && envs+=(-e E2E_TOLERATE_KNOWN_FLAKY=1)

mounts=()
if [ "$DEV" = yes ]; then
    # 読み取り専用。書き込みを許すとコンテナのrootが __pycache__ を作業ツリーに
    # 作り、ホストから消せなくなる（deploy/loadtest/mongodata で実際にやらかした）。
    mounts=(-v "$APP_DIR/tests:/app/tests:ro")
    envs+=(-e PYTHONDONTWRITEBYTECODE=1)
    echo '--- dev: tests/ はホストからマウント、src/（アプリ）はイメージのもの ---'
    echo '--- アプリ側を直したときは --dev を外してイメージを作り直すこと ---'
fi

# -rR はリトライしたテストを一覧に出す。フレーキーの出入りを見るのに要る。
exec docker run --rm --network "$NETWORK" "${envs[@]}" "${mounts[@]}" \
    "$E2E_IMAGE" python3 -m pytest -q -rR "$@"
