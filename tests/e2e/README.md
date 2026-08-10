# E2Eテストの実行方法

## 前提: コンテナ内で動かす設計になっている

このE2Eテストは以下の前提で書かれており、**ホストのシェルからそのままでは動かない**。

- `tests/conftest.py` が `subprocess.Popen` で**サーバ自身を起動する**(`http://localhost:10011`)。
  起動対象は `FLASK_ENV=test`、`config_test.py` の `PORT = 10011`
- `config_test.py` の `MONGO_URI` が **`mongodb://admin:password@mongo:27017/test`** をハードコード。
  ホスト名 `mongo` はdocker-composeのサービス名なので、**そのネットワーク内でしか解決しない**
- `tests/conftest.py` がサーバ起動に `/usr/local/bin/pipenv` を決め打ちしている
- firefox と geckodriver が要る

分散負荷テスト用のワーカーイメージがこれらをすべて満たす(firefox-esr・geckodriver・
`/usr/local/bin/pipenv`)ので、それを流用するのが手っ取り早い。

なお `helper.py` の `STAGING_TOP` は死んだHeroku URLで、**このテストはstagingには向けられない**。

## 手順

```sh
# 1. mongo を立てる(deploy/loadtest の compose を流用する。app は使わないが起動していても害はない)
(cd deploy/loadtest && docker compose up -d mongo)

# 2. ワーカーイメージをビルド(tests/ と src/ が焼き込まれるので、コード変更のたびに必要)
pipenv run python -m tests.performance.cli build-image --run-on docker

# 3. 実行
docker run --rm --network loadtest_default \
    -e PYTHONPATH=/runner:/runner/src \
    -e MOZ_HEADLESS=1 \
    --entrypoint sh test_run_multiprocess_in_container_worker \
    -c "cd /runner && pipenv run pytest tests/e2e -q"
```

- `PYTHONPATH` に `/runner/src` を足すのは、`in_mem_app` フィクスチャなどが `asobann` を
  import するため(イメージの既定は `/runner` だけ)
- `MOZ_HEADLESS=1` を使うのは、`another_browser_window` と `browser_factory` が
  `webdriver.Firefox()` をオプション無しで呼んでいて、`--headless` オプションが渡らないため。
  環境変数ならどの経路でも効く

一部だけ流すときは末尾を `pytest tests/e2e/test_session.py -q` などに変える。

## フレーキーさについて

複数の実ブラウザを実サーバに対して動かし、非同期に届く状態をassertするので、本質的に
フレーキー。`tests/e2e/conftest.py` の `pytest_collection_modifyitems` で
**E2Eテストにのみ** `pytest.mark.flaky`(pytest-rerunfailures)を自動付与している。

ユニットテストには意図的に適用していない。そちらで再試行すると本物の不具合を隠すため。

## 過去にはまった点

- **サーバ起動待ち**: `start_server` が `time.sleep(1)` の固定待ちだった。Mongo接続だけで
  数秒かかるので、listen前にブラウザが接続して
  `Reached error page: about:neterror?e=connectionFailure` になっていた。
  現在はポートが受け付けるまで待つ(`wait_for_server`)
- **ウィンドウサイズ**: ヘッドレスFirefoxの既定ビューポートは **1366x634** だが、テストは
  y=650〜750 あたりにドラッグする。`MoveTargetOutOfBoundsException` と、その後の
  連鎖的なタイムアウトが大量に出る。`new_e2e_browser` で明示的に 1600x1200 にしている。
  負荷テストと共有している `firefox_options` は変更していない(変えるとベースラインがずれる)
