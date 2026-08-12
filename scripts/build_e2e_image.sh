#!/usr/bin/env bash
# E2Eテスト用イメージを、本番イメージの上に積んでビルドする。
#
# なぜこの手順が要るか:
#   - E2Eは以前 python:3.10-slim-bookworm から独立にビルドしたイメージで動いていて、
#     本番(bullseye / Python 3.10.18 / greenlet 1.1.3)と食い違っていた。テストの意味が
#     薄れるので、本番イメージをベースにする(Dockerfile.e2e)
#   - Dockerfile.aws は requirements.txt を COPY するが、これは uv.lock からの
#     生成物。作業ツリーに残った古い requirements.txt でビルドすると本番と別物になる。
#     実際それで greenlet が 1.1.3 と 3.5.4 に割れていた。**必ず再生成する**
#
# Usage: ./scripts/build_e2e_image.sh
#
# 出力: asobann-app:local (本番相当) と asobann-e2e:local (それ+テスト道具)

set -eu
cd "$(dirname "$0")/.."

APP_IMAGE="asobann-app:local"
E2E_IMAGE="asobann-e2e:local"

echo "==> 依存を uv.lock から書き出す"
uv export --frozen --no-dev --no-emit-project --no-hashes -o requirements.txt --quiet
uv export --frozen --only-group e2e --no-emit-project --no-hashes -o requirements-e2e.txt --quiet
# localdevイメージと負荷試験runnerが使う。ついでに再生成してドリフトを防ぐ
uv export --frozen --group dev --no-emit-project --no-hashes -o requirements-dev.txt --quiet
echo "    requirements.txt: $(grep -cE '^[a-zA-Z0-9]' requirements.txt) パッケージ / requirements-e2e.txt: $(grep -cE '^[a-zA-Z0-9]' requirements-e2e.txt) パッケージ"

echo "==> 本番相当イメージをビルドする ($APP_IMAGE)"
docker build -q -f Dockerfile.aws -t "$APP_IMAGE" . > /dev/null

echo "==> E2Eイメージをビルドする ($E2E_IMAGE)"
docker build -q -f Dockerfile.e2e --build-arg "BASE_IMAGE=$APP_IMAGE" -t "$E2E_IMAGE" . > /dev/null

echo "==> アプリの依存が本番イメージと一致しているか検証する"
# テスト道具(pytest等)の導入が、アプリ側のパッケージを巻き添えで動かしていないことを確認する。
# 動いていたら、そのイメージでのテスト結果は本番の挙動を保証しない。
# --format=freeze で name==version にする。既定の表形式は列幅がパッケージ名の最長に
# 合わせて変わるため、テスト道具を足したE2E側だけ空白が増えて偽の差分になる。
pkgs='^(flask|flask-socketio|python-socketio|python-engineio|eventlet|werkzeug|pymongo|greenlet|flask-pymongo|redis|dnspython|boto3)=='
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
