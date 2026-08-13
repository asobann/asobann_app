#!/usr/bin/env bash
#
# コンテナでテストを走らせる run_*.sh の共通部分。
#
# 単体で実行するものではない。`source` して使う。
#
# なぜ共通化しているか: functional も e2e も「mongoを用意する / テストイメージを
# 用意する / 同じdockerネットワークでpytestを起動する」までが同一で、違うのは
# 対象ディレクトリとブラウザ関連の環境変数だけ。個別に書くと、mongoの起こし方を
# 直したときに片方だけ直すことになる。
#
# 提供するもの:
#   APP_DIR              asobann_app のルート
#   TEST_IMAGE           テスト実行に使うイメージ
#   NETWORK              テストコンテナとmongoを繋ぐdockerネットワーク
#   parse_common_flags   --no-build / --dev を解釈する（残りは呼び出し側へ返す）
#                        スクリプト固有のフラグは EXTRA_FLAG_HANDLER で足す
#   default_targets      対象が指定されていなければ既定のテストパスを補う
#   ensure_mongo         mongoが無ければ起動する
#   ensure_image         イメージをビルドする、または存在を確かめる
#   run_pytest           テストコンテナでpytestを実行する

# 自分の位置からリポジトリのルートを引く。gitに答えさせるので、どこから
# 実行しても、チェックアウト先がどこにあっても正しい。
APP_DIR=$(git -C "$(dirname "${BASH_SOURCE[0]}")" rev-parse --show-toplevel)

# functional も e2e も同じイメージを使う。functional にブラウザは要らないが、
# イメージを増やす方が管理の手間が大きいと判断した。firefoxが乗っている分だけ
# 重いのはローカル実行だけの話で、実害がない。
TEST_IMAGE=${TEST_IMAGE:-${E2E_IMAGE:-asobann-e2e:local}}
NETWORK=${NETWORK:-loadtest_default}
MONGO_COMPOSE="$APP_DIR/deploy/loadtest/docker-compose.yml"
MONGO_CONTAINER=loadtest-mongo-1

# 失敗時のスクリーンショットの置き場。作業ツリーの中だが .gitignore してある。
# tmp/ はコンテナへマウントする作業用で毎回消す。保存用は実行ごとの日時ディレクトリ。
# 普段は捨ててよいもので、必要になったら issue に貼るか worklog へ持っていく。
ARTIFACTS_DIR="$APP_DIR/.e2e-artifacts"
TMP_ARTIFACTS="$ARTIFACTS_DIR/tmp"

BUILD=yes
DEV=no
MOUNT_SRC=no

# 呼び出し側の "$@" をそのまま渡す。解釈しなかった引数を REMAINING_ARGS に残す。
# 配列で返すのは、-k 'Test A' のような空白を含む指定を壊さないため。
#
# スクリプト固有のフラグは EXTRA_FLAG_HANDLER に関数名を入れて渡す。その関数は
# 引数を1つ受け取り、解釈したら0を返す。解釈しなければ非0を返すこと。
#
# 解釈をやめる条件は「`--` が来た」か「フラグでない引数が来た」。どちらの場合も
# 残りは一切触らずpytestへ渡す。ここを緩めると `-- --dev` のように「pytestへの
# 引数として --dev を渡したい」ケースを吸い込んでしまう。
parse_common_flags() {
    REMAINING_ARGS=()
    while [ $# -gt 0 ]; do
        case "$1" in
            --no-build)  BUILD=no; shift ;;
            --dev)       DEV=yes; BUILD=no; shift ;;
            --mount-src) MOUNT_SRC=yes; shift ;;
            --)          shift; REMAINING_ARGS=("$@"); return ;;
            *)
                if [ -n "${EXTRA_FLAG_HANDLER:-}" ] && "$EXTRA_FLAG_HANDLER" "$1"; then
                    shift
                else
                    REMAINING_ARGS=("$@"); return
                fi
                ;;
        esac
    done
}

# default_targets <既定のパス...> -- <呼び出し側に残った引数...>
#
# 引数にテストパスが含まれていなければ既定のパスを先頭に補い、TARGETS に入れる。
#
# 「引数が1つも無いときだけ既定を使う」ではダメで、`run_functional.sh -s` のように
# pytestのフラグだけ渡すと対象が空になり、pytestが testpaths（tests/ 全部）に
# フォールバックしてe2eまで走ってしまう。実際に踏んだ。
#
# パスの判定は「tests から始まるか」で行う。対象は必ず tests/ 配下にあり、
# -k TestGlued の値のようなフラグの引数とは衝突しない。
default_targets() {
    local defaults=()
    while [ $# -gt 0 ] && [ "$1" != -- ]; do
        defaults+=("$1"); shift
    done
    shift  # --

    for arg in "$@"; do
        case "$arg" in
            tests|tests/*) TARGETS=("$@"); return ;;
        esac
    done
    TARGETS=("${defaults[@]}" "$@")
}

# テストは config_test.py のハードコードにより mongo:27017 を見る。deploy/loadtest の
# composeがサービス名 mongo でそれを提供するので、それを使い回す。
ensure_mongo() {
    if ! docker ps --format '{{.Names}}' | grep -qx "$MONGO_CONTAINER"; then
        echo "mongo が起動していないので起動する"
        docker compose -f "$MONGO_COMPOSE" up -d mongo
    fi
}

ensure_image() {
    if [ "$BUILD" = yes ]; then
        "$APP_DIR/scripts/build_e2e_image.sh"
    elif ! docker image inspect "$TEST_IMAGE" >/dev/null 2>&1; then
        echo "$TEST_IMAGE が無い。--no-build / --dev を外すか、" >&2
        echo "scripts/build_e2e_image.sh を先に実行すること" >&2
        exit 1
    fi
}

# run_pytest [-e KEY=VAL ...] -- <pytestに渡す引数...>
# -- より前は docker run へ、後は pytest へ渡す。
run_pytest() {
    local envs=()
    while [ $# -gt 0 ]; do
        case "$1" in
            -e)  envs+=(-e "$2"); shift 2 ;;
            --)  shift; break ;;
            *)   echo "run_pytest: 解釈できない引数: $1" >&2; exit 1 ;;
        esac
    done

    local mounts=()
    # 読み取り専用。書き込みを許すとコンテナのrootが __pycache__ を作業ツリーに
    # 作り、ホストから消せなくなる（deploy/loadtest/mongodata で実際にやらかした）。
    if [ "$DEV" = yes ]; then
        mounts+=(-v "$APP_DIR/tests:/app/tests:ro")
        envs+=(-e PYTHONDONTWRITEBYTECODE=1)
    fi
    if [ "$MOUNT_SRC" = yes ]; then
        # Dockerfile.aws が `COPY src /app/` しているので、パッケージは /app/asobann。
        mounts+=(-v "$APP_DIR/src/asobann:/app/asobann:ro")
        envs+=(-e PYTHONDONTWRITEBYTECODE=1)
    fi

    if [ "$DEV" = yes ] || [ "$MOUNT_SRC" = yes ]; then
        local mounted='tests/'
        [ "$MOUNT_SRC" = yes ] && mounted='tests/ と src/'
        echo "--- dev: $mounted はホストからマウント（ビルド無し） ---"
        if [ "$MOUNT_SRC" != yes ]; then
            echo '--- src/（アプリ）はイメージのもの。直したらビルドし直すこと ---'
        fi
    fi

    # テストが書き出したものの受け皿。コンテナはrootで動くので、ここに落ちる
    # ファイルはroot所有になる。**ホスト側へは cp で取り出す。** cp は新しい
    # ファイルを作るので、実行した本人が所有者になり、chownもsudoも要らない。
    #
    # この受け皿はディレクトリ自体をホスト側で作る。中のファイルがroot所有でも、
    # 削除に要るのは親ディレクトリへの書き込み権限なので rm -rf は通る。
    #
    # コンテナに渡すコマンドには手を入れない。テストの種類ごとに渡すものが違うので、
    # 後始末をコマンド側に埋め込むと、その都度ついて回ることになる。
    clean_tmp_artifacts
    mkdir -p "$TMP_ARTIFACTS"
    mounts+=(-v "$TMP_ARTIFACTS:/artifacts")
    envs+=(-e ASOBANN_E2E_ARTIFACTS=/artifacts)

    # -rR はリトライしたテストを一覧に出す。フレーキーの出入りを見るのに要る。
    # -v はテスト名を1件ずつ出す。以前は -q を渡しており、進捗のドットしか残らず
    # 「どのテストがどの順で走ったか」が後から追えなかった。順序依存を疑ったときに
    # 手がかりが無いのは困るので、既定を詳細側にする。
    local rc=0
    docker run --rm --network "$NETWORK" "${envs[@]}" "${mounts[@]}" \
        "$TEST_IMAGE" python3 -m pytest -v -rR "$@" || rc=$?

    # || true は set -e への保険。save_artifacts 自身も失敗を握りつぶすが、
    # 二重に守っておく。返すべきは pytest の終了コードだけ。
    save_artifacts || true
    return $rc
}

# 受け皿を空にする。
#
# 中のファイルはコンテナがrootで書いたもの。平坦に置かれているかぎりホスト側で
# 消せる（消すのに要るのは親ディレクトリへの書き込み権限で、それはこちらが持って
# いる）。ただしコンテナが**サブディレクトリ**を作ると、その中身には手が出せない。
# そのときだけコンテナに消させる。ホスト側でsudoを使わずに済ませるため。
clean_tmp_artifacts() {
    [ -e "$TMP_ARTIFACTS" ] || return 0
    rm -rf "$TMP_ARTIFACTS" 2>/dev/null
    [ -e "$TMP_ARTIFACTS" ] || return 0
    docker run --rm -v "$ARTIFACTS_DIR:/a" "$TEST_IMAGE" sh -c 'rm -rf /a/tmp' >/dev/null 2>&1
    rm -rf "$TMP_ARTIFACTS" 2>/dev/null || true
}

# コンテナが書き出したものを、保存用のディレクトリへ実行ごとに分けて取り出す。
# cp が新しいファイルを作るので、ここで所有者がホスト側の自分になる。
# 中身が無ければ何もしない（成功した実行でディレクトリが増えても邪魔なだけ）。
#
# **失敗しても握りつぶす。** これは診断の材料を残すためのおまけであって、テストの
# 結果ではない。ここでコケてスクリプトが落ちると、pytestの終了コードを返す前に
# 死ぬことになり、成果物の都合がテスト結果を上書きしてしまう。
#
# 保存先に秒とPIDを入れる。秒だけだと、同じ秒に2回呼ばれたとき（並行実行や、
# 短いテストを続けて回したとき）に同じディレクトリへ混ざる。
save_artifacts() {
    if [ -z "$(ls -A "$TMP_ARTIFACTS" 2>/dev/null)" ]; then
        return 0
    fi
    local dest="$ARTIFACTS_DIR/$(date +%Y%m%d-%H%M%S)-$$"
    if ! mkdir -p "$dest" 2>/dev/null; then
        echo "成果物の保存先を作れなかった: $dest" >&2
        return 0
    fi
    if ! cp -r "$TMP_ARTIFACTS"/. "$dest"/ 2>/dev/null; then
        echo "成果物のコピーに失敗した（テスト結果には影響しない）: $dest" >&2
        return 0
    fi
    echo "失敗時のスクリーンショット: $dest"
    ls "$dest" 2>/dev/null | sed 's/^/  /' || true
}
