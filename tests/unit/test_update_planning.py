import pytest

from asobann.store.tables import collect_update_candidates, build_modification, InvalidComponentId


class TestCollectUpdateCandidates:
    def test_normal_update_becomes_a_candidate(self):
        candidates = collect_update_candidates(
            [{'component1': {'value1': 100}}],
            volatile_keys={})
        assert candidates == {'component1': {'value1': 100}}

    def test_several_diffs_for_several_components_are_merged(self):
        candidates = collect_update_candidates(
            [
                {'component1': {'value1': 100}},
                {'component2': {'value1': 200}},
            ],
            volatile_keys={})
        assert candidates == {
            'component1': {'value1': 100},
            'component2': {'value1': 200},
        }

    def test_a_volatile_key_is_dropped(self):
        candidates = collect_update_candidates(
            [{'component1': {'value1': 100, 'value2': 200}}],
            volatile_keys={'component1': ['value1']})
        assert candidates == {'component1': {'value2': 200}}

    def test_component_with_all_keys_volatile_is_absent(self):
        candidates = collect_update_candidates(
            [{'component1': {'value1': 100, 'value2': 200}}],
            volatile_keys={'component1': ['value1', 'value2']})
        assert candidates == {}

    def test_volatile_keys_for_another_component_are_ignored(self):
        candidates = collect_update_candidates(
            [{'component1': {'value1': 100}}],
            volatile_keys={'component2': ['value1']})
        assert candidates == {'component1': {'value1': 100}}

    def test_no_diffs_yields_no_candidates(self):
        candidates = collect_update_candidates([], volatile_keys={})
        assert candidates == {}

    def test_component_id_with_dot_is_rejected(self):
        with pytest.raises(InvalidComponentId):
            collect_update_candidates(
                [{'a.b': {'value1': 100}}],
                volatile_keys={})


class TestBuildModification:
    def test_existing_component_produces_dotted_set_paths(self):
        modification = build_modification(
            candidates={'component1': {'value1': 100}},
            existing_component_ids={'component1'})
        assert modification == {'table.components.component1.value1': 100}

    def test_removed_component_is_skipped(self):
        modification = build_modification(
            candidates={
                'component1': {'value1': 100},
                'component2': {'value1': 200},
            },
            existing_component_ids={'component1'})
        assert modification == {'table.components.component1.value1': 100}

    def test_all_candidates_removed_yields_no_modification(self):
        modification = build_modification(
            candidates={'component1': {'value1': 100}},
            existing_component_ids=set())
        assert modification == {}

    def test_no_candidates_yields_no_modification(self):
        modification = build_modification(
            candidates={},
            existing_component_ids={'component1'})
        assert modification == {}
