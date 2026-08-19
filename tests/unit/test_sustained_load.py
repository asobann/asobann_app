from tests.performance.sustained_load import same_machine_pairs


class TestSameMachinePairs:
    """
    Latency needs both timestamps on one clock. When workers are spread across machines
    (LOADTEST_WORKER_SYSTEMS), same_machine_pairs keeps only pairs where neither side
    crossed a machine boundary, grouping by each worker's exact system name rather than
    a binary local/external flag.

    worker_systems is a comma-separated string, one entry per P<idx> in order (e.g.
    'local,local,river,river' means P0/P1 are on 'local' and P2/P3 are on 'river').
    'host' (the controller's own browser) is always on whichever machine this process
    itself runs on, which is 'local' by convention.
    """

    def test_no_worker_systems_keeps_everything(self):
        pairs = [{'sender': 'P0', 'receiver': 'host'}, {'sender': 'P0', 'receiver': 'P1'}]
        assert same_machine_pairs(pairs, '') == pairs

    def test_local_to_local_pair_is_kept(self):
        pairs = [{'sender': 'P0', 'receiver': 'P1'}]
        assert same_machine_pairs(pairs, 'local,local,river') == pairs

    def test_host_to_local_pair_is_kept(self):
        pairs = [{'sender': 'host', 'receiver': 'P0'}]
        assert same_machine_pairs(pairs, 'local,local,river') == pairs

    def test_local_to_remote_pair_is_dropped(self):
        pairs = [{'sender': 'P0', 'receiver': 'P2'}]
        assert same_machine_pairs(pairs, 'local,local,river') == []

    def test_remote_to_local_pair_is_dropped_regardless_of_direction(self):
        pairs = [{'sender': 'P2', 'receiver': 'P0'}]
        assert same_machine_pairs(pairs, 'local,local,river') == []

    def test_host_to_remote_pair_is_dropped(self):
        pairs = [{'sender': 'host', 'receiver': 'P2'}]
        assert same_machine_pairs(pairs, 'local,local,river') == []

    def test_same_remote_system_pair_is_kept(self):
        # Two workers on the same other machine still share a clock.
        pairs = [{'sender': 'P2', 'receiver': 'P3'}]
        assert same_machine_pairs(pairs, 'local,local,river,river') == pairs

    def test_two_different_remote_systems_are_dropped(self):
        # This is the case a single "external" count used to get wrong: two remote
        # hosts don't share a clock just because neither is 'local'.
        pairs = [{'sender': 'P2', 'receiver': 'P3'}]
        assert same_machine_pairs(pairs, 'local,local,river,pi') == []

    def test_mixed_pairs_only_cross_machine_ones_are_dropped(self):
        pairs = [
            {'sender': 'P0', 'receiver': 'host'},   # local <-> local: kept
            {'sender': 'P0', 'receiver': 'P2'},      # local <-> river: dropped
            {'sender': 'host', 'receiver': 'P2'},    # local <-> river: dropped
        ]
        assert same_machine_pairs(pairs, 'local,local,river') == [
            {'sender': 'P0', 'receiver': 'host'},
        ]

    def test_three_systems_each_pair_only_within_its_own_system(self):
        pairs = [
            {'sender': 'P0', 'receiver': 'P1'},  # both local: kept
            {'sender': 'P2', 'receiver': 'P3'},  # both river: kept
            {'sender': 'P4', 'receiver': 'P5'},  # both pi: kept
            {'sender': 'P1', 'receiver': 'P2'},  # local <-> river: dropped
            {'sender': 'P3', 'receiver': 'P4'},  # river <-> pi: dropped
        ]
        assert same_machine_pairs(pairs, 'local,local,river,river,pi,pi') == [
            {'sender': 'P0', 'receiver': 'P1'},
            {'sender': 'P2', 'receiver': 'P3'},
            {'sender': 'P4', 'receiver': 'P5'},
        ]
