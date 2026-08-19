import pytest

from tests.performance.framework import parse_extra_workers


class TestParseExtraWorkers:
    def test_empty_spec_means_no_workers(self):
        assert parse_extra_workers('') == []
        assert parse_extra_workers('   ') == []

    def test_single_entry(self):
        assert parse_extra_workers('192.168.0.28:50000') == [('192.168.0.28', 50000)]

    def test_multiple_entries_on_one_host(self):
        assert parse_extra_workers('192.168.0.28:50000,192.168.0.28:50001') == [
            ('192.168.0.28', 50000),
            ('192.168.0.28', 50001),
        ]

    def test_whitespace_around_entries_is_stripped(self):
        assert parse_extra_workers(' 192.168.0.28:50000 , 192.168.0.28:50001 ') == [
            ('192.168.0.28', 50000),
            ('192.168.0.28', 50001),
        ]

    def test_malformed_entry_is_rejected(self):
        with pytest.raises(ValueError):
            parse_extra_workers('not-a-host-port')

    def test_non_numeric_port_is_rejected(self):
        with pytest.raises(ValueError):
            parse_extra_workers('192.168.0.28:notaport')

    def test_ipv6_host_is_rejected(self):
        # ':' inside the host would also break remote_runner.py's plain split(':').
        with pytest.raises(ValueError):
            parse_extra_workers('::1:50000')

    def test_entries_spanning_multiple_hosts_are_rejected(self):
        # same_machine_pairs() only tracks a local/external count, not a per-worker
        # machine id, so it is only correct if every external worker shares one clock.
        with pytest.raises(ValueError):
            parse_extra_workers('192.168.0.28:50000,192.168.0.29:50000')
