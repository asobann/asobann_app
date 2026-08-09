from tests.performance.mouse_latency import pair_latencies, summarize_latencies, loss_rate, evaluate_all_pairs


def test_pair_latencies_matches_by_expected_left():
    sent = [
        {'expected_left': 100.0, 'expected_top': 10.0, 'sent_at': 1000},
        {'expected_left': 101.0, 'expected_top': 11.0, 'sent_at': 1010},
        {'expected_left': 102.0, 'expected_top': 12.0, 'sent_at': 1020},
    ]
    received = [
        {'left': 100.0, 'top': 10.0, 'received_at': 1005},
        {'left': 102.0, 'top': 12.0, 'received_at': 1030},  # 101 dropped
    ]
    latencies = pair_latencies(sent, received)
    assert latencies == [5, 10]


def test_pair_latencies_ignores_unmatched_receptions():
    sent = [{'expected_left': 5.0, 'expected_top': 0.0, 'sent_at': 0}]
    received = [{'left': 999.0, 'top': 0.0, 'received_at': 5}]
    assert pair_latencies(sent, received) == []


def test_summarize_latencies_empty():
    assert summarize_latencies([]) == {'count': 0, 'p50': None, 'p95': None, 'max': None}


def test_summarize_latencies_percentiles():
    latencies = list(range(1, 101))  # 1..100
    summary = summarize_latencies(latencies)
    assert summary['count'] == 100
    assert summary['p50'] == 51
    assert summary['p95'] == 96
    assert summary['max'] == 100


def test_loss_rate():
    assert loss_rate(10, 10) == 0.0
    assert loss_rate(10, 5) == 0.5
    assert loss_rate(0, 0) == 0.0


def test_evaluate_all_pairs_skips_self():
    sent_by_player = {
        'P1': [{'expected_left': 1.0, 'expected_top': 0.0, 'sent_at': 0}],
        'P2': [{'expected_left': 2.0, 'expected_top': 0.0, 'sent_at': 0}],
    }
    received_by_receiver = {
        'P1': {'P1': [{'left': 1.0, 'top': 0.0, 'received_at': 1}],  # self, must be skipped
               'P2': [{'left': 2.0, 'top': 0.0, 'received_at': 5}]},
    }
    results = evaluate_all_pairs(sent_by_player, received_by_receiver)
    assert len(results) == 1
    assert results[0]['sender'] == 'P2'
    assert results[0]['receiver'] == 'P1'
    assert results[0]['count'] == 1
