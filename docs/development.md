# 開発ガイド

最終更新: 2026-07-06（masterブランチ基準）

## セットアップ

必要なもの: uv（Pythonと依存はuvが管理）、Node.js + pnpm、Docker。e2eテストにはFirefox + geckodriver。

```shell
pnpm install        # JS依存
uv sync             # Python依存（devグループ含む。.venvを作る）
pnpm exec webpack   # フロントエンドビルド（src/js → src/asobann/app/static/main.js）
```

JSを変更したら `pnpm exec webpack` の再実行が必要（watchモード: `pnpm exec webpack --watch`）。

## ローカル起動

```shell
docker compose -f deploy/localdev/docker-compose.yml up --build
```

- http://localhost:8000/ でアクセス。app_1〜app_3 の3プロセス + mongo + redis が起動する（複数プロセスでの同期挙動を確認できる）
- ソースはボリュームマウントされるが、**Pythonプロセスの自動リロードはない**。サーバコード変更時はコンテナ再起動が必要

## テスト

### 種類と場所

**必要な外部リソースでディレクトリを分けている。** どこに置くかは「何が要るか」で決まる。

| 種類 | 場所 | 前提 | 実行方法 | 内容 |
|---|---|---|---|---|
| unit (JS) | tests/unit/*.test.js | **なし**（jsdom） | ホスト | 更新キュー（Level A/B/C）、送信バッファ |
| unit (Python) | tests/unit/*.py | **なし** | ホスト | 設定、ログの伏字化、レイテンシ解析 |
| functional | tests/functional/ | MongoDB | **コンテナ** | HTTPエンドポイント、store層。アプリは `test_client()` でインプロセス起動 |
| api | tests/api/ | MongoDB + テストサーバ（conftestが起動） | **コンテナ** | キットアップロードAPI |
| e2e | tests/e2e/ | MongoDB + テストサーバ + Firefox | **コンテナ** | Seleniumでの実ブラウザ操作。2ブラウザ同期検証を含む |
| performance | tests/performance/ | 対象サーバ | cli.py | 負荷計測フレームワーク（pytestでは実行しない） |

**実DBが要るテストを `tests/unit/` に置かないこと。** ユニットテストは外部プロセス無しで完走する、が唯一の基準。

### 実行

ワークスペース直下の invoke タスクが統一の窓口。

```shell
inv test-unit                                    # Python + JS。DBもコンテナも不要
inv test-functional                              # functional + api（コンテナ）
inv test-e2e                                     # e2e（コンテナ。重い）

inv test-functional --extra="tests/functional/store"
inv test-unit --extra="-k redact -v"
```

asobann_app 単体で作業しているならスクリプトを直接叩くほうが速い。

```shell
uv run pytest tests/unit                         # ホストでそのまま動く
pnpm test                                        # JS unit
./scripts/run_functional.sh                      # functional + api
./scripts/run_e2e.sh                             # e2e
```

### なぜコンテナなのか

`config_test.py` が接続先に `mongo:27017` を使う。この名前は docker のネットワーク内でしか解決できないので、**functional 以降はホストから直接は動かない**。`scripts/lib/container_tests.sh` が mongo の起動とテストコンテナの実行をまとめて面倒を見る。

- mongo は `deploy/loadtest/docker-compose.yml` から起動し、**上げっぱなしで再利用する**（毎回上げ直さない）
- テストイメージは `asobann-e2e:local`。functional にブラウザは要らないが、イメージを増やす手間のほうが大きいので共用している

### 直しながら回すとき

既定ではイメージをビルドし直すので時間がかかる。`--dev` を使うとビルドを飛ばし、作業ツリーをマウントする。

```shell
./scripts/run_functional.sh --dev tests/functional/store   # 約2秒
inv test-functional --dev --extra="-k update_components"
```

| | functional | e2e |
|---|---|---|
| `--dev` でマウントするもの | `tests/` と `src/` | `tests/` のみ |

e2e で `src/` をマウントしないのは、**本番イメージそのものを検証する**という位置づけを保つため（→ issue #126）。アプリ側を直したら `--dev` を外してビルドし直す。functional はアプリをインプロセスで起動するのでこの制約がなく、`src/` も一緒にマウントして編集→再実行を速くしている。

### 性能計測（tests/performance/）

slowness問題の再現・計測に使う。シナリオ例: `move_single_card_each.py`（複数プレイヤーが各自カードを動かす）、`move_stack_of_cards.py` など。`cli.py` がエントリポイントで、`remote_runner.py` によりリモートホストでの分散実行もできる。

## ディレクトリ早見

```
src/asobann/       # Pythonバックエンド（→ docs/architecture.md）
src/js/            # フロントエンド（webpackでバンドル）
src/asobann/app/static/main.js   # webpackの出力（コミットしない・直接編集しない）
deploy/localdev/   # ローカル用docker compose
scripts/           # 補助スクリプト
tests/             # 上記テスト群
```

## コーディング規約

- Python: PEP 8、型アノテーション推奨、snake_case / PascalCase
- JavaScript: ES6+、camelCase / PascalCase
- テストは種類ごとのディレクトリに置く（→ 上記「種類と場所」）。マーカーではなく置き場所で区別する

## 落とし穴メモ

- feats配列の先頭は必ず `basic`（feat.js）。feat間に暗黙の依存があるため、featの追加・変更時は architecture.md の「featシステム」を先に読むこと
- `table.data` がサーバ状態、`component.*` はビュー状態のキャッシュ。receiveDataで受信した `data` を書き換えないこと
- socket.ioまわりのバージョンはサーバ（python-socketio）とクライアント（socket.io-client）の互換表を確認してから上げること
