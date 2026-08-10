(cluster=asobann-staging, service=asobann-staging-Service-8SGkckzQoSDd)

## baseline

| 構成 | 人数 | Hz | 操作 | CPU平均 | CPU最大 | p50 | p95 | ロス率 | worker脱落 | flip未反映 |
|---|---|---|---|---|---|---|---|---|---|---|
| flip_n2 | 2 | 30 | flip | n/a | n/a | 205ms | 226ms | 2.4% | なし | 0 |
| flip_n3 | 3 | 30 | flip | 52.3% | 54.3% | 217ms | 234ms | 2.1% | なし | 0 |
| flip_n4 | 4 | 30 | flip | 66.4% | 72.5% | 215ms | 1082ms | 1.8% | なし | 0 |
| flip_n5 | 5 | 30 | flip | 83.0% | 92.4% | 213ms | 239ms | 1.8% | なし | 0 |
| flip_n6 | 6 | 30 | flip | 90.5% | 99.2% | 217ms | 279ms | 1.5% | なし | 0 |
| flip_n4_15hz | 4 | 15 | flip | 40.3% | 46.4% | 210ms | 240ms | 2.1% | なし | 0 |
| flip_n6_15hz | 6 | 15 | flip | 63.7% | 66.4% | 211ms | 240ms | 1.5% | なし | 0 |
| mouseonly_n2 | 2 | 30 | - | 31.3% | 37.7% | 226ms | 243ms | 2.1% | なし | 0 |
| mouseonly_n4 | 4 | 30 | - | 68.0% | 77.4% | 211ms | 234ms | 1.8% | なし | 0 |
| mouseonly_n6 | 6 | 30 | - | 99.7% | 100.0% | 217ms | 399ms | 4.0% | なし | 0 |
| pause_only_n6 | 6 | 30 | pause_only | 87.1% | 97.2% | 214ms | 372ms | 4.1% | なし | 0 |
