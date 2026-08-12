from tests.support.mouse_latency import (
    pair_latencies, summarize_latencies, loss_rate, evaluate_all_pairs, evaluate_all_pairs_timeseries,
)


def test_pair_latencies_matches_by_position():
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


def test_pair_latencies_distinguishes_positions_sharing_an_x():
    # The cursor walks a lattice, so many sends share an x coordinate and differ only in y.
    # Keying on x alone would pair a reception with whichever same-x send came last.
    sent = [
        {'expected_left': 50.0, 'expected_top': 10.0, 'sent_at': 1000},
        {'expected_left': 50.0, 'expected_top': 11.0, 'sent_at': 1100},
    ]
    received = [{'left': 50.0, 'top': 10.0, 'received_at': 1200}]
    assert pair_latencies(sent, received) == [200]  # not 100


def test_pair_latencies_picks_most_recent_send_when_position_repeats():
    # A 100x100 grid at 30Hz revisits a position every ~5.5 minutes; the reception belongs
    # to the latest lap, and a naive first/last-wins map would yield a nonsensical latency.
    sent = [
        {'expected_left': 7.0, 'expected_top': 3.0, 'sent_at': 1_000},
        {'expected_left': 7.0, 'expected_top': 3.0, 'sent_at': 331_000},  # next lap
    ]
    received = [{'left': 7.0, 'top': 3.0, 'received_at': 331_200}]
    assert pair_latencies(sent, received) == [200]


def test_pair_latencies_never_reports_negative_latency():
    # Reception precedes every recorded send at that position: unmatched, not negative.
    sent = [{'expected_left': 1.0, 'expected_top': 1.0, 'sent_at': 5_000}]
    received = [{'left': 1.0, 'top': 1.0, 'received_at': 1_000}]
    assert pair_latencies(sent, received) == []


def test_pair_latencies_drops_matches_beyond_max_latency():
    sent = [{'expected_left': 1.0, 'expected_top': 1.0, 'sent_at': 0}]
    received = [{'left': 1.0, 'top': 1.0, 'received_at': 120_000}]
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


def test_evaluate_all_pairs_timeseries_buckets_by_send_time_not_drain_boundary():
    # A message sent at the very end of interval 0 (sent_at=59900) but received just
    # after interval 0's nominal boundary (60000) must NOT count as a loss in interval 0
    # nor as a phantom (unmatched) reception in interval 1: it belongs to interval 0's
    # sent bucket (by sent_at) and interval 1's received bucket (by received_at), and the
    # latency itself is still attributed to interval 0 (bucket the match by sent_at).
    start = 0
    sent_by_player = {
        'A': [
            {'expected_left': 1.0, 'expected_top': 0.0, 'sent_at': 100},      # bucket 0
            {'expected_left': 2.0, 'expected_top': 0.0, 'sent_at': 59900},    # bucket 0, received late
        ],
    }
    received_by_receiver = {
        'B': {
            'A': [
                {'left': 1.0, 'top': 0.0, 'received_at': 300},      # bucket 0
                {'left': 2.0, 'top': 0.0, 'received_at': 60100},    # bucket 1 (crossed boundary)
            ],
        },
    }
    buckets = evaluate_all_pairs_timeseries(sent_by_player, received_by_receiver,
                                            start_at_ms=start, interval_seconds=60)
    assert set(buckets.keys()) == {0, 1}

    bucket0 = buckets[0][0]
    assert bucket0['sender'] == 'A' and bucket0['receiver'] == 'B'
    assert bucket0['sent_count'] == 2  # both sends happened in bucket 0
    assert bucket0['count'] == 2  # both matched, attributed to their sent_at bucket
    assert bucket0['loss_rate'] == 0.0
    assert bucket0['max'] == 60100 - 59900  # the late-arriving message's latency

    bucket1 = buckets[1][0]
    assert bucket1['sent_count'] == 0  # nothing was newly sent in bucket 1
    assert bucket1['received_count'] == 1  # the late arrival landed here
    assert bucket1['count'] == 0  # but it was already matched into bucket 0, not counted again


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
