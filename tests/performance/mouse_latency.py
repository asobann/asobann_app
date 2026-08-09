"""
Pairs synthetic mousemove events sent by one player (GameHelper.start_mouse_load)
with the corresponding DOM updates observed by another player
(GameHelper.start_mouse_receive_observer), to measure end-to-end latency of the
mousemove broadcast path (the path suspected of causing slowness under load).

Sent and observed records are matched by the predicted CSS pixel position
(expected_left from the sender) vs. the actually observed left, both integers
after rounding. Since the sender's clientX increases by exactly 1 per event,
expected_left is unique per message, so this is an exact match, not a nearest-
neighbor guess, and needs no assumption about delivery order or drop-free delivery.
"""

from typing import Dict, List


def pair_latencies_with_time(sent: List[dict], received: List[dict]) -> List[dict]:
    """
    Like pair_latencies, but keeps sent_at on each match so callers can attribute a
    match to the interval it was *sent* in (see bucket_by_sent_time / evaluate_all_pairs_timeseries) -
    matching itself should always run over a run's full sent/received data, not data
    already split into report-interval chunks: a message sent near the end of one
    interval can easily be observed in the next one, and matching only within an
    interval's own drained chunk would wrongly count that as a loss in the first
    interval and an unmatched (phantom) reception in the second.
    """
    sent_by_left = {round(s['expected_left']): s['sent_at'] for s in sent}
    matched = []
    for r in received:
        sent_at = sent_by_left.get(round(r['left']))
        if sent_at is not None:
            matched.append({'sent_at': sent_at, 'latency': r['received_at'] - sent_at})
    return matched


def pair_latencies(sent: List[dict], received: List[dict]) -> List[float]:
    """
    sent: [{'expected_left': float, 'expected_top': float, 'sent_at': int(ms)}, ...]
    received: [{'left': float, 'top': float, 'received_at': int(ms)}, ...]
    returns: list of latencies in milliseconds, one per matched message.
    """
    return [m['latency'] for m in pair_latencies_with_time(sent, received)]


def summarize_latencies(latencies: List[float]) -> dict:
    if not latencies:
        return {'count': 0, 'p50': None, 'p95': None, 'max': None}
    ordered = sorted(latencies)
    n = len(ordered)

    def pct(p):
        idx = min(n - 1, int(n * p))
        return ordered[idx]

    return {
        'count': n,
        'p50': pct(0.50),
        'p95': pct(0.95),
        'max': ordered[-1],
    }


def loss_rate(sent_count: int, received_count: int) -> float:
    if sent_count == 0:
        return 0.0
    return max(0.0, 1.0 - received_count / sent_count)


def evaluate_pair(sender_name: str, receiver_name: str, sent: List[dict], received: List[dict]) -> dict:
    latencies = pair_latencies(sent, received)
    return {
        'sender': sender_name,
        'receiver': receiver_name,
        'sent_count': len(sent),
        'received_count': len(received),
        'loss_rate': loss_rate(len(sent), len(received)),
        **summarize_latencies(latencies),
    }


def evaluate_all_pairs(sent_by_player: Dict[str, List[dict]],
                        received_by_receiver: Dict[str, Dict[str, List[dict]]]) -> List[dict]:
    """
    sent_by_player: {player_name: sent_list} - what each player sent in this interval.
    received_by_receiver: {receiver_name: {sender_name: received_list}} - what each
        player observed from each other player in this interval.
    returns a flat list of per-(sender, receiver) evaluations.
    """
    results = []
    for receiver_name, received_by_sender in received_by_receiver.items():
        for sender_name, received in received_by_sender.items():
            if sender_name == receiver_name:
                continue
            sent = sent_by_player.get(sender_name, [])
            results.append(evaluate_pair(sender_name, receiver_name, sent, received))
    return results


def evaluate_all_pairs_timeseries(sent_by_player: Dict[str, List[dict]],
                                   received_by_receiver: Dict[str, Dict[str, List[dict]]],
                                   start_at_ms: int, interval_seconds: int) -> Dict[int, List[dict]]:
    """
    Same inputs as evaluate_all_pairs, but sent_by_player/received_by_receiver are expected
    to hold a whole run's *cumulative* data (concatenated across all periodic drains), not
    a single interval's chunk. Matching runs once over the full data, so a slow message sent
    near the end of one report interval is still correctly matched even if its reception
    lands in the next interval - it does not get double-counted as a loss and a phantom
    reception the way per-interval-only matching would (see pair_latencies_with_time).

    Sent/received counts and matched latencies are then independently grouped by which
    report-interval bucket each event's own timestamp (sent_at for sent/matched, received_at
    for received) falls into.

    returns {bucket_index: [pair_result, ...]}, bucket_index counting up from 0 at start_at_ms.
    """
    interval_ms = interval_seconds * 1000

    def bucket_of(ts):
        return int((ts - start_at_ms) // interval_ms)

    results_by_bucket: Dict[int, List[dict]] = {}
    for receiver_name, received_by_sender in received_by_receiver.items():
        for sender_name, received in received_by_sender.items():
            if sender_name == receiver_name:
                continue
            sent = sent_by_player.get(sender_name, [])
            matched = pair_latencies_with_time(sent, received)

            sent_counts: Dict[int, int] = {}
            for s in sent:
                b = bucket_of(s['sent_at'])
                sent_counts[b] = sent_counts.get(b, 0) + 1

            received_counts: Dict[int, int] = {}
            for r in received:
                b = bucket_of(r['received_at'])
                received_counts[b] = received_counts.get(b, 0) + 1

            latencies_by_bucket: Dict[int, List[float]] = {}
            for m in matched:
                b = bucket_of(m['sent_at'])
                latencies_by_bucket.setdefault(b, []).append(m['latency'])

            all_buckets = set(sent_counts) | set(received_counts) | set(latencies_by_bucket)
            for b in all_buckets:
                sc = sent_counts.get(b, 0)
                rc = received_counts.get(b, 0)
                lats = latencies_by_bucket.get(b, [])
                results_by_bucket.setdefault(b, []).append({
                    'sender': sender_name,
                    'receiver': receiver_name,
                    'sent_count': sc,
                    'received_count': rc,
                    'loss_rate': loss_rate(sc, len(lats)),
                    **summarize_latencies(lats),
                })
    return results_by_bucket
