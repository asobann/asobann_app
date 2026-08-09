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


def pair_latencies(sent: List[dict], received: List[dict]) -> List[float]:
    """
    sent: [{'expected_left': float, 'expected_top': float, 'sent_at': int(ms)}, ...]
    received: [{'left': float, 'top': float, 'received_at': int(ms)}, ...]
    returns: list of latencies in milliseconds, one per matched message.
    """
    sent_by_left = {round(s['expected_left']): s['sent_at'] for s in sent}
    latencies = []
    for r in received:
        sent_at = sent_by_left.get(round(r['left']))
        if sent_at is not None:
            latencies.append(r['received_at'] - sent_at)
    return latencies


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
