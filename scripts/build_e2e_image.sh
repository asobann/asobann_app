#!/usr/bin/env bash
# E2Eテスト用イメージを、本番イメージの上に積んでビルドする。
#
# なぜこの手順が要るか:
#   - E2Eは以前 python:3.10-slim-bookworm から独立にビルドしたイメージで動いていて、
#     本番(bullseye / Python 3.10.18 / greenlet 1.1.3)と食い違っていた。テストの意味が
#     薄れるので、本番イメージをベースにする(Dockerfile.e2e)
#   - 本番相当イメージのビルドは scripts/build_image.sh に一本化する。以前はここで
#     Dockerfile.aws を直接ビルドしており、build_image.sh が必ずやるwebpackの
#     ビルドを踏まずにイメージができていた。手元では作業ツリーに残った古いJS
#     バンドル(gitignore済み)が偶然拾われて気づかないが、CIの新規チェックアウト
#     ではJSバンドル無しの本番イメージができ、E2Eが全件落ちる。本番イメージの
#     ビルド手順が2箇所にあると、こういう食い違いが構造的に起きる。
#
# Usage: ./scripts/build_e2e_image.sh
#
# 出力: asobann_aws:<sha>(本番相当、scripts/build_image.shが作る) と
#       asobann-e2e:<sha>(それ+テスト道具)。<sha>は同じ値で、未コミットの
#       変更があれば -dirty が付く(scripts/build_image.sh --print-tag が唯一の正)。

set -eu
cd "$(dirname "$0")/.."

TAG=$(./scripts/build_image.sh --print-tag)
APP_IMAGE="asobann_aws:$TAG"
E2E_IMAGE="asobann-e2e:$TAG"

echo "==> 本番相当イメージをビルドする ($APP_IMAGE)"
./scripts/build_image.sh

echo "==> E2Eテスト道具の依存を uv.lock から書き出す"
uv export --frozen --only-group e2e --no-emit-project --no-hashes -o requirements-e2e.txt --quiet
# localdevイメージと負荷試験runnerが使う。ついでに再生成してドリフトを防ぐ
uv export --frozen --group dev --no-emit-project --no-hashes -o requirements-dev.txt --quiet
echo "    requirements-e2e.txt: $(grep -cE '^[a-zA-Z0-9]' requirements-e2e.txt) パッケージ / requirements-dev.txt: $(grep -cE '^[a-zA-Z0-9]' requirements-dev.txt) パッケージ"

echo "==> E2Eイメージをビルドする ($E2E_IMAGE)"
docker build -q -f Dockerfile.e2e --build-arg "BASE_IMAGE=$APP_IMAGE" -t "$E2E_IMAGE" . > /dev/null

echo "==> アプリの依存が本番イメージと一致しているか検証する"
# テスト道具(pytest等)の導入が、アプリ側のパッケージを巻き添えで動かしていないことを確認する。
# 動いていたら、そのイメージでのテスト結果は本番の挙動を保証しない。
# --format=freeze で name==version にする。既定の表形式は列幅がパッケージ名の最長に
# 合わせて変わるため、テスト道具を足したE2E側だけ空白が増えて偽の差分になる。
# asyncio移行後のスタックに合わせた顔ぶれ。flask / flask-socketio / eventlet /
# greenlet / flask-pymongo を並べたままにしていた時期があり、消えたパッケージ名を
# 見ているせいで「一致」と出てしまう状態だった。**依存を入れ替えたらここも直すこと。**
# quart と uvicorn が抜けていると、このスクリプトの存在意義が無くなる。
pkgs='^(quart|uvicorn|hypercorn|wsproto|simple-websocket|python-socketio|python-engineio|werkzeug|pymongo|redis|dnspython|boto3|aiofiles|blinker|itsdangerous|jinja2)=='
app_list=$(docker run --rm --entrypoint sh "$APP_IMAGE" -c "pip3 list --format=freeze 2>/dev/null" | grep -iE "$pkgs" | sort)
e2e_list=$(docker run --rm --entrypoint sh "$E2E_IMAGE" -c "pip3 list --format=freeze 2>/dev/null" | grep -iE "$pkgs" | sort)
if [ "$app_list" = "$e2e_list" ]; then
    echo "    一致"
    echo "$app_list" | sed 's/^/      /'
else
    echo "    ERROR: E2Eイメージでアプリの依存が変わっている" >&2
    diff <(echo "$app_list") <(echo "$e2e_list") >&2 || true
    exit 1
fi

echo ""
echo "完了。実行:"
echo "  docker run --rm --network loadtest_default -e MOZ_HEADLESS=1 \\"
echo "      $E2E_IMAGE python3 -m pytest tests/e2e -q"
