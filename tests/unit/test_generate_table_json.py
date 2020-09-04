from json import dumps
import pytest

from asobann.generate_table_json import ComponentRegistry

pytestmark = [pytest.mark.quick]

def test_single_component_kit():
    registry = ComponentRegistry()
    kit = registry.kit()
    kit.description = {'name': 'kit A', 'key': 'value'}
    kit.add_component({'name': 'component 1', 'text': 'text1'})

    expected = {
        'components': [
            {
                'component':
                    {'name': 'component 1', 'text': 'text1'}
            }
        ],
        'kits': [
            {
                'kit': {
                    'name': 'kit A',
                    'key': 'value',
                    'boxAndComponents': {'component 1': None},
                    'usedComponentNames': ['component 1'],
                }
            }
        ]
    }
    assert dumps(expected, indent=2) == dumps(registry.build_data_for_deploy(), indent=2)


def test_single_kit_with_single_box():
    registry = ComponentRegistry()
    kit = registry.kit()
    kit.description = {'name': 'kit A', 'key': 'value'}

    box = kit.box()
    box.box_component = {'name': 'box 1', 'text': 'text of box'}
    box.add_component({'name': 'component 1', 'text': 'text1'})

    expected = {
        'components': [
            {
                'component':
                    {'name': 'box 1', 'text': 'text of box'},
            },
            {
                'component':
                    {'name': 'component 1', 'text': 'text1'},
            },
        ],
        'kits': [
            {
                'kit': {
                    'name': 'kit A',
                    'key': 'value',
                    'boxAndComponents': {
                        'box 1': ['component 1'],
                    },
                    'usedComponentNames': ['box 1', 'component 1'],
                },
            }
        ]
    }
    assert dumps(expected, indent=2) == dumps(registry.build_data_for_deploy(), indent=2)


def test_kit_with_components_from_another_kit():
    registry = ComponentRegistry()
    kit_a = registry.kit()
    kit_a.description = {'name': 'kit A', 'key': 'value'}

    kit_a.add_component({'name': 'component in A', 'text': 'text1'})

    kit_b = registry.kit()
    kit_b.description = {'name': 'kit B', 'key': 'value'}

    box = kit_b.box()
    box.box_component = {'name': 'box 1', 'text': 'text of box'}
    box.add_component({'name': 'component 1', 'text': 'text2'})
    box.use_components(['component in A'])

    expected = {
        'components': [
            {
                'component':
                    {'name': 'component in A', 'text': 'text1'},
            },
            {
                'component':
                    {'name': 'box 1', 'text': 'text of box'},
            },
            {
                'component':
                    {'name': 'component 1', 'text': 'text2'},
            },
        ],
        'kits': [
            {
                'kit': {
                    'name': 'kit A',
                    'key': 'value',
                    'boxAndComponents': {'component in A': None},
                    'usedComponentNames': ['component in A'],
                },
            },
            {
                'kit': {
                    'name': 'kit B',
                    'key': 'value',
                    'boxAndComponents': {
                        'box 1': ['component 1', 'component in A'],
                    },
                    'usedComponentNames': ['box 1', 'component 1', 'component in A'],
                },
            },
        ]
    }
    assert dumps(expected, indent=2) == dumps(registry.build_data_for_deploy(), indent=2)
