from cfgdict.utils import flatten_dict, unflatten_dict, nested_update_dict
from loguru import logger

def test_utils_basic():
    """
    Test basic functionality of flatten_dict and unflatten_dict functions.
    
    This test case covers:
    1. Flattening and unflattening nested dictionaries
    2. Handling empty dictionaries
    3. Processing single-level dictionaries
    """
    # Test nested dictionary
    nested_dict = {
        'a': 1,
        'b': {
            'c': 2,
            'd': {
                'e': 3
            }
        },
        'f': 4
    }

    # Test flatten_dict
    flattened = flatten_dict(nested_dict)
    assert flattened == {
        'a': 1,
        'b.c': 2,
        'b.d.e': 3,
        'f': 4
    }, "flatten_dict failed to correctly flatten nested dictionary"

    # Test unflatten_dict
    unflattened = unflatten_dict(flattened)
    assert unflattened == nested_dict, "unflatten_dict failed to correctly reconstruct nested dictionary"

    # Test empty dictionary
    assert flatten_dict({}) == {}, "flatten_dict failed to handle empty dictionary"
    assert unflatten_dict({}) == {}, "unflatten_dict failed to handle empty dictionary"

    # Test single-level dictionary
    simple_dict = {'x': 1, 'y': 2, 'z': 3}
    assert flatten_dict(simple_dict) == simple_dict, "flatten_dict failed to handle single-level dictionary"
    assert unflatten_dict(simple_dict) == simple_dict, "unflatten_dict failed to handle single-level dictionary"

def test_utils_advanced():
    """
    Test advanced scenarios for flatten_dict and unflatten_dict functions.
    
    This test case covers:
    1. Dictionaries with list values
    2. Keys containing dots
    3. Non-string keys
    4. Deep nesting
    """
    # Test dictionary with list values
    dict_with_list = {
        'a': [1, 2, 3],
        'b': {
            'c': [4, 5, 6]
        }
    }
    flattened = flatten_dict(dict_with_list)
    assert flattened == {'a': [1, 2, 3], 'b.c': [4, 5, 6]}, "flatten_dict failed to handle list values"
    assert unflatten_dict(flattened) == dict_with_list, "unflatten_dict failed to handle list values"

    # Test keys containing dots
    dict_with_dots = {
        'a.b': 1,
        'c': {
            'd.e': 2
        }
    }
    flattened = flatten_dict(dict_with_dots)
    assert flattened == {'a.b': 1, 'c.d.e': 2}, "flatten_dict failed to handle keys with dots"
    assert unflatten_dict(flattened) == {'a': {'b': 1}, 'c': {'d': {'e': 2}}}, "unflatten_dict failed to handle keys with dots"

    # Test deep nesting
    deep_nested = {'a': {'b': {'c': {'d': {'e': 1}}}}}
    flattened = flatten_dict(deep_nested)
    assert flattened == {'a.b.c.d.e': 1}, "flatten_dict failed to handle deep nesting"
    assert unflatten_dict(flattened) == deep_nested, "unflatten_dict failed to handle deep nesting"

def test_update_dict():
    d = {'a': 1, 'b': 2, 'c': 3}
    u = {'a': 10, 'b': 20, 'd': 40}
    nested_update_dict(d, u, logger=logger)
    assert d == {'a': 10, 'b': 20, 'c': 3, 'd': 40}
    
    d = {'a': None, 'b': 2, 'c': 3}
    u = {'a': 10, 'b': 20, 'd': 40}
    nested_update_dict(d, u, logger=logger)
    assert d == {'a': 10, 'b': 20, 'c': 3, 'd': 40}

def test_unflatten_dict():
    d = {'a': 1, 'b.x': 2, 'b.y': 3, 'c': 4}
    new_d = unflatten_dict(d, logger=logger)
    print(d)
    print(new_d)
    assert new_d == {'a': 1, 'b': {'x': 2, 'y': 3}, 'c': 4}
    
    d = {'a': 1, 'b': {'y': 2}, 'b.y': 3, 'c': 4}
    new_d = unflatten_dict(d, logger=logger)
    print('input:', d)
    print('output:', new_d)
    assert new_d == {'a': 1, 'b': {'y': 3}, 'c': 4}