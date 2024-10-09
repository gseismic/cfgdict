from cfgdict.utils import nested_update_dict, unflatten_dict, nested_get_from_dict
from cfgdict.schema import Field, Schema
# from cfgdict.config2 import Config
from cfgdict.config2 import Config, Field, Schema,FieldValidationError, FieldKeyError, make_config

from loguru import logger
from cfgdict.exception import FieldKeyError
import pytest

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

def test_get_nested_value():
    d = {'a': 1, 'b.x': 2, 'b.y': 3, 'c': 4, 'yyy': None}
    value = nested_get_from_dict('b.x', d, unflatten=True)
    assert value == 2
    value = nested_get_from_dict('yyy', d, unflatten=True)
    assert value is None

def test_make_dict():
    d = {'a': 1, 'b.x': 2, 'b.y': 3, 'c': 4, 'yyy': None}
    schema = Schema(not_exit=Field(default=9, type='int'),
                    b=Field(schema=Schema(x=Field(type='int'), y=Field(type='int'))), 
                    c=Field(type='int'))
    cfg = Config(d, schema=schema, logger=logger)
    print(cfg)
    
def test_make_dict_error():
    with pytest.raises(FieldKeyError):
        d = {'a': 1, 'b.x': 2, 'b.y': 3, 'c': 4}
        schema = Schema(not_exit=Field(required=True, type='int'),
                        b=Field(schema=Schema(x=Field(type='int'), y=Field(type='int'))), 
                        c=Field(type='int'))
        cfg = Config(d, schema=schema, logger=logger)

def test_make_config():
    d = {'a': 1, 'b.x': 2, 'b.y': 3, 'c': 9}
    schema = Schema(not_exit=Field(required=False, default=9, type='int'),
                    b=Field(schema=Schema(x=Field(type='int'), y=Field(type='int'))), 
                    c=Field(type='int'))
    cfg = Config(d, schema=schema, logger=logger)
    print(cfg)

def test_resolve_reference():
    d = {'a': 1, 'b.x': 2, 'b.y': 3, 'c': 9}
    schema = Schema(not_exit=Field(required=False, default=9, type='int'),
                    b=Field(schema=Schema(x=Field(type='int'), y=Field(type='int'))), 
                    c=Field(type='int', ge='$b.x'))
    cfg = Config(d, schema=schema, logger=logger)
    print(cfg)
    assert cfg['c'] == 9
    assert cfg.get('c') == 9
    assert cfg.c == 9

def test_update():
    d = {'a': 1, 'b.x': 2, 'b.y': 3, 'c': 9}
    schema = Schema(not_exit=Field(required=False, default=9, type='int'),
                    b=Field(schema=Schema(x=Field(type='int', ge=1), y=Field(type='int'))), 
                    c=Field(type='int', ge='$b.x'))
    print(schema)
    cfg = Config(d, schema=schema, logger=logger)
    print(cfg)
    assert cfg['c'] == 9
    assert cfg.get('c') == 9
    assert cfg.c == 9
    cfg.update(b=dict(x=10, y=11))
    print(cfg)
    assert cfg.b.x == 10
    assert cfg.b.y == 11

def test_from_file():
    config_dict = {
        'a': 1,
        'b': {
            'x': 2,
            'y': 3
        },
        'c': 9
    }
    schema = Schema(not_exit=Field(required=False, default=9, type='int'),
                    b=Field(schema=Schema(x=Field(type='int', ge=1), y=Field(type='int'))), 
                    c=Field(type='int', ge='$b.x'))

    cfg = make_config(config_dict, schema=schema, logger=logger)
    
    path = 'config_v2.yaml'
    cfg.to_file(path)
    cfg2 = Config.from_file(path, schema=schema, logger=logger)
    assert cfg == cfg2

    path = 'config_v2.json'
    cfg.to_file(path)
    cfg2 = Config.from_file(path, schema=schema, logger=logger)
    assert cfg == cfg2
    # assert 0
    
if __name__ == "__main__":
    if 0:
        test_update_dict()
    if 0:
        test_unflatten_dict()
    if 1:
        test_make_dict()