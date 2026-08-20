import pytest

from tests.performance.framework import parse_worker_systems


class TestParseWorkerSystems:
    def test_empty_spec_means_no_systems(self):
        assert parse_worker_systems('') == []
        assert parse_worker_systems('   ') == []

    def test_single_entry(self):
        assert parse_worker_systems('local:14') == [('local', 14)]

    def test_multiple_entries(self):
        assert parse_worker_systems('local:14,river:10') == [
            ('local', 14),
            ('river', 10),
        ]

    def test_whitespace_around_entries_is_stripped(self):
        assert parse_worker_systems(' local:14 , river:10 ') == [
            ('local', 14),
            ('river', 10),
        ]

    def test_malformed_entry_is_rejected(self):
        with pytest.raises(ValueError):
            parse_worker_systems('not-a-name-count')

    def test_non_numeric_count_is_rejected(self):
        with pytest.raises(ValueError):
            parse_worker_systems('river:notacount')

    def test_zero_count_is_rejected(self):
        with pytest.raises(ValueError):
            parse_worker_systems('river:0')

    def test_negative_count_is_rejected(self):
        with pytest.raises(ValueError):
            parse_worker_systems('river:-1')

    def test_name_containing_colon_is_rejected(self):
        # A colon in the name would make rpartition(':') misparse the count.
        with pytest.raises(ValueError):
            parse_worker_systems('::1:14')

    def test_duplicate_system_name_is_rejected(self):
        with pytest.raises(ValueError):
            parse_worker_systems('river:10,river:4')

    def test_any_number_of_systems_is_allowed(self):
        # Unlike the old single-external-host design, three or more machines mix freely.
        assert parse_worker_systems('local:14,river:10,pi:4') == [
            ('local', 14),
            ('river', 10),
            ('pi', 4),
        ]
