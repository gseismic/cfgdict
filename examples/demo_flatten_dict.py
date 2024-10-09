from cfgdict.v1 import flatten_dict, unflatten_dict

# test nested dict
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

print(f'nested_dict: {nested_dict}')

# test flatten_dict
flattened = flatten_dict(nested_dict)
print(f'flattened: {flattened}')

assert flattened == {
    'a': 1,
    'b.c': 2,
    'b.d.e': 3,
    'f': 4
}

unflattened = unflatten_dict(flattened)
assert unflattened == nested_dict

# 测试空字典 | test empty dict
assert flatten_dict({}) == {}
assert unflatten_dict({}) == {}

# 测试只有一层的字典 | test simple dict
simple_dict = {'x': 1, 'y': 2, 'z': 3}
assert flatten_dict(simple_dict) == simple_dict
assert unflatten_dict(simple_dict) == simple_dict
