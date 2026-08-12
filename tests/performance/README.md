# 負荷試験ハーネス

**これは恒常的に維持するテストスイートではない。** 特定の問題（[#134](https://github.com/asobann/asobann_app/issues/134)「5人以上で10〜20分遊ぶと途中から重くなる」）を調べるために組んだ道具で、必要に応じて足してきた蓄積。

既定の pytest 実行からは除外してある（`pyproject.toml` の `addopts = --ignore tests/performance`）。CIにも載せていない。

## 維持の方針（ADR 0012）

**壊れたら、直す価値があるかをその都度判断する。** 常時グリーンを保つ対象ではない。

ただし**アプリ側の大きな移行（ランタイム、依存、プロトコル）では追従させる**こと。同じリポジトリにあれば移行作業に巻き込まれるので、追加コストはほぼゼロ。凍結すると、次に使いたくなったときに壊れていることに気づく（2026-08 の asyncio 移行では実際にここが壊れ、同じ PR で直した）。

## 構成

| | |
|---|---|
| `framework.py` | 分散実行の基盤。controller/worker を docker またはローカルプロセスで動かす |
| `sustained_load.py` | 持続的なマウス移動負荷 + 定期的なコンポーネント操作。**主シナリオ** |
| `verify_mouse_load.py` | 合成 mousemove が実際に相手の画面まで届くかの検証 |
| `move_*.py` | 個別のコンポーネント操作シナリオ |
| `remote_runner.py` / `cli.py` | 実行の入口 |

計測結果の突き合わせ（レイテンシ、ロス率）は `tests/support/mouse_latency.py` にある。**あちらは維持する**（ユニットテスト付きで CI で動く）。負荷試験の結論が乗っている解析ロジックなので、ここが狂うと80分回した実験から自信たっぷりに間違った結論が出る。

## 他への依存

- **`tests/e2e/` のヘルパーに乗っている**（`GameHelper`, `browser_func`）。E2E側を変えるとここも影響を受ける。逆向きの依存は無い
- `deploy/loadtest/docker-compose.yml` が対象アプリと mongo を提供する。これは E2E も使っている

## 実行

staging に対してスイートを回す:

```sh
./scripts/run_load_suite.sh <label> [config_name...]
# 1時間以上かかる。nohup ... & disown で流すこと
uv run --no-project --with boto3 python scripts/summarize_load_suite.py results/<label>
```

出力は `results/<label>/` に出る（gitignore 済み）。残したいものは asobann_docs の worklogs へ。

## 経緯と、ここに無いもの

2026-08 の調査の詳細（実測値、実験条件、CPU内訳、ローカル較正の手順と較正済みスクリプト、ベースラインの生データ）は **asobann_docs の `worklogs/20260809.slowness/`**（private）にある。

ローカルCPUプロファイリング用のスクリプト群はそちらに置いた。cgroup v2 / systemd ドライバや実測較正した quota など**特定のマシンに固有の前提**を含むので、再利用するなら較正からやり直すこと（ADR 0014）。
