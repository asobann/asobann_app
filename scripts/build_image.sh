#!/usr/bin/env bash
#
# 本番用イメージをビルドする。AWSには一切触らない。
#
# ECRへのpushは asobann_deploy/tools/push_image.py が担当する。分けてあるのは、
# ビルドは asobann_app の資産（Dockerfile.aws、uv.lock、pnpm-lock.yaml、webpack設定）
# だけで完結し、認証情報を必要としないため。CIからも認証情報なしで叩ける。
#
# タグにはgitのコミットSHAを使う。`latest` や `production` のような可変タグは
# デプロイ対象の指定に使わない。同じタグが別の中身を指しうるため、
# 「本番で動いているのはどのイメージか」が曖昧になる（ADR 0002でわざわざ
# digestを記録する羽目になったのはこれが理由）。
#
# ビルドは1回だけ行い、同じdigestを staging → 本番 と昇格させる（ADR 0009）。
# 本番用に作り直したイメージは、stagingで確認したものとは別物になる。
#
# **タグの決め方はここが唯一の正。** 他所で同じ規則を書き直さず、--print-tag を呼ぶこと。
#
# 前提: docker, node + pnpm, uv
#
# 使い方:
#   ./scripts/build_image.sh              # ビルドする
#   ./scripts/build_image.sh --print-tag  # ビルドせず、タグだけ出す
#
# 出力の最後にローカルのイメージ参照（asobann_aws:<tag>）を表示する。

set -euo pipefail

APP_DIR=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
REPO=${REPO:-asobann_aws}

cd "$APP_DIR"

sha=$(git rev-parse --short HEAD)
if [ -n "$(git status --porcelain)" ]; then
    # 未コミットの変更を含むイメージは再現できない。手元での確認には使えるが、
    # 本番に昇格させてはいけないので、タグで見分けられるようにする。
    sha="$sha-dirty"
fi

if [ "${1:-}" = "--print-tag" ]; then
    echo "$sha"
    exit 0
fi

IMAGE="$REPO:$sha"

if [ "$sha" != "${sha%-dirty}" ]; then
    echo "警告: 未コミットの変更がある。このイメージを本番に出さないこと" >&2
fi

echo "==> バージョンを決める"
echo "$IMAGE"

echo "==> 依存を書き出す"

# Dockerfile.aws は requirements.txt を COPY する。uv.lock が正で、
# requirements.txt はその都度生成する中間物（gitignore済み）。
uv export --frozen --no-dev --no-emit-project --no-hashes -o requirements.txt --quiet
echo "$(grep -cE '^[a-zA-Z0-9]' requirements.txt) パッケージ"

echo "==> フロントエンドをビルドする"

# webpackの出力先は src/asobann/app/static/ で、これを Dockerfile.aws が
# src ごと COPY する。つまりビルド順序に依存がある（webpack → docker build）。
#
# node_modules があっても必ず frozen-lockfile で入れ直す。ここを「無ければ入れる」に
# すると、手元に残った別ブランチのnode_modulesでビルドしてしまう。実際に2026-08-09時点で
# 手元にはslowness_issueブランチのもの（webpack 5.93 / socket.io-client 4.7.5）が
# 残っており、masterのlock（5.72.1 / 4.5.1）と食い違っていた。
# pnpm install --frozen-lockfile はlockと不一致なら失敗し、node_modulesをlockどおりに揃える。
pnpm install --frozen-lockfile
pnpm exec webpack

echo "==> イメージをビルドする"

docker build -f Dockerfile.aws -t "$IMAGE" .

echo
echo "==> ビルド完了"
echo "image: $IMAGE"
echo "ECRへ上げるには: asobann_deploy/tools/push_image.py $IMAGE"
