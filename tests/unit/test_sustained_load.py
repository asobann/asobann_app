from tests.performance.sustained_load import same_machine_pairs


class TestSameMachinePairs:
    """
    Latency needs both timestamps on one clock. When workers are spread across machines
    (LOADTEST_EXTRA_WORKERS), the last `external_worker_count` of them are elsewhere;
    same_machine_pairs keeps only pairs where neither side crossed a machine boundary.

    Workers are ordered local-then-external (see LocalContainers.start_workers), so with
    3 workers total and external_worker_count=1, P0/P1 are local and P2 is remote.
    """

    def test_no_external_workers_keeps_everything(self):
        pairs = [{'sender': 'P0', 'receiver': 'host'}, {'sender': 'P0', 'receiver': 'P1'}]
        assert same_machine_pairs(pairs, total_workers=2, external_worker_count=0) == pairs

    def test_local_to_local_pair_is_kept(self):
        pairs = [{'sender': 'P0', 'receiver': 'P1'}]
        assert same_machine_pairs(pairs, total_workers=3, external_worker_count=1) == pairs

    def test_host_to_local_pair_is_kept(self):
        pairs = [{'sender': 'host', 'receiver': 'P0'}]
        assert same_machine_pairs(pairs, total_workers=3, external_worker_count=1) == pairs

    def test_local_to_external_pair_is_dropped(self):
        pairs = [{'sender': 'P0', 'receiver': 'P2'}]
        assert same_machine_pairs(pairs, total_workers=3, external_worker_count=1) == []

    def test_external_to_local_pair_is_dropped_regardless_of_direction(self):
        pairs = [{'sender': 'P2', 'receiver': 'P0'}]
        assert same_machine_pairs(pairs, total_workers=3, external_worker_count=1) == []

    def test_host_to_external_pair_is_dropped(self):
        pairs = [{'sender': 'host', 'receiver': 'P2'}]
        assert same_machine_pairs(pairs, total_workers=3, external_worker_count=1) == []

    def test_external_to_external_pair_is_kept(self):
        # Two remote workers on the same other machine still share a clock.
        pairs = [{'sender': 'P2', 'receiver': 'P3'}]
        assert same_machine_pairs(pairs, total_workers=4, external_worker_count=2) == pairs

    def test_mixed_pairs_only_cross_machine_ones_are_dropped(self):
        pairs = [
            {'sender': 'P0', 'receiver': 'host'},   # local <-> local: kept
            {'sender': 'P0', 'receiver': 'P2'},      # local <-> external: dropped
            {'sender': 'host', 'receiver': 'P2'},    # local <-> external: dropped
        ]
        assert same_machine_pairs(pairs, total_workers=3, external_worker_count=1) == [
            {'sender': 'P0', 'receiver': 'host'},
        ]
