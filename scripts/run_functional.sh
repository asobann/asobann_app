#!/usr/bin/env bash
#
# functional / api テストをコンテナで実行する。
#
# これらは実MongoDBを要る（アプリを create_app() でインプロセス起動し、store層が
# 実際に読み書きする）。config_test.py が mongo:27017 をハードコードしているため、
# ホストからは動かない。テストイメージをmongoと同じdockerネットワークで走らせる。
#
# e2e と違い、ブラウザは使わない。アプリは別コンテナではなくテストプロセス内で動く
# （Quartの test_client）ので、必要なコンテナはテストとmongoの2つだけ。
#
# 共通の足回り（mongo起動・イメージ用意・docker run）は scripts/lib/container_tests.sh。
#
# 使い方:
#   ./scripts/run_functional.sh [オプション] [pytestに渡す引数...]
#
# オプション（このスクリプトが解釈するもの。以降はすべて pytest に素通しする）:
#   --no-build   イメージのビルドを省く。ビルド済みのものを使う
#   --dev        tests/ と src/ をホストから読み取り専用でマウントし、ビルドを省く。
#                作業ツリーのコードがそのままテスト対象になるので、直しながら
#                回すときはこれを使う（ビルドが要らない分、大幅に速い）
#   --mount-src  src/ だけマウントする（--dev に含まれる）
#
# mongoは deploy/loadtest の compose で起動したまま残る。毎回上げ直さない。
#
# 例:
#   ./scripts/run_functional.sh                                # functional + api 全件
#   ./scripts/run_functional.sh tests/functional/store
#   ./scripts/run_functional.sh --dev -k update_components     # 直しながら速く回す
#   ./scripts/run_functional.sh -p no:randomly -s              # 順序固定＋print表示

set -euo pipefail

source "$(dirname "$0")/lib/container_tests.sh"

parse_common_flags "$@"

# 対象を指定しなければ functional と api の両方。どちらも実MongoDBが要る。
# api は tests/conftest.py の TestServerProvider でサーバをsubprocess起動するので
# functional より重いが、必要な外部リソースは同じ。
default_targets tests/functional tests/api -- ${REMAINING_ARGS+"${REMAINING_ARGS[@]}"}
set -- "${TARGETS[@]}"

# functional はアプリをインプロセスで起動する（別コンテナのサーバを叩かない）ので、
# src/ をマウントすれば作業ツリーのアプリコードがそのままテスト対象になる。
# e2e と違い「本番イメージそのものを検証する」性格ではないため、--dev では
# src/ も一緒にマウントして編集→再実行を速くする。
[ "$DEV" = yes ] && MOUNT_SRC=yes

ensure_mongo
ensure_image

run_pytest -- "$@"
