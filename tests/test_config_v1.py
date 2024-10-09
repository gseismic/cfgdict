import os
import pytest
from cfgdict.config import Config, Field, Schema,FieldValidationError, FieldKeyError

import json

@pytest.fixture
def sample_schema():
    return [
        dict(field='name', required=True, rules=dict(type='str', min_len=2, max_len=50)),
        dict(field='age', required=True, rules=dict(type='int', min=0, max=120)),
        dict(field='email', required=True, rules=dict(type='str', regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')),
        dict(field='is_active', default=False, required=False, rules=dict(type='bool')),
        dict(field='nested.value', required=True, rules=dict(type='float', min=0, max=1)),
    ]

@pytest.fixture
def sample_config():
    return {
        'name': 'John Doe',
        'age': 30,
        'email': 'john.doe@example.com',
        'nested': {'value': 0.5}
    }

def test_config_initialization(sample_schema, sample_config):
    config = Config(sample_config, sample_schema)
    assert config['name'] == 'John Doe'
    assert config['age'] == 30
    assert config['email'] == 'john.doe@example.com'
    # assert config['nested.value'] == 0.5

def test_config_validation_error(sample_schema):
    invalid_config = {
        'name': 'J',  # Too short
        'age': 150,   # Too high
        'email': 'invalid-email',
        'nested': {'value': 1.5}  # Too high
    }
    with pytest.raises(FieldValidationError):
        Config(invalid_config, sample_schema)

def test_config_missing_required_field(sample_schema):
    incomplete_config = {
        'name': 'John Doe',
        'age': 30
    }
    with pytest.raises(FieldValidationError):
        Config(incomplete_config, sample_schema)

def test_config_update(sample_schema, sample_config):
    config = Config(sample_config, sample_schema)
    config.update(age=31, nested={'value': 0.7})
    assert config['age'] == 31
    assert config['nested.value'] == 0.7
    
    config = Config()
    config.update({'field1': 'value1', 'field2': 'value2'})
    config.update(field1='value1', field2='value2')
    config.update({'field1': 'value1'}, field2='value2')
    print(config.to_dict())

def test_config_to_dict(sample_schema, sample_config):
    config = Config(sample_config, sample_schema)
    config_dict = config.to_dict()
    assert config_dict == {
        'name': 'John Doe',
        'age': 30,
        'email': 'john.doe@example.com',
        'is_active': False,
        'nested': {'value': 0.5}
    }

def test_config_attribute_access(sample_schema, sample_config):
    config = Config(sample_config, sample_schema)
    assert config.name == 'John Doe'
    assert config.age == 30
    assert config.nested.value == 0.5

def test_config_strict_mode():
    schema = [dict(field='allowed_field', required=True, rules=dict(type='str'))]
    config = Config({'allowed_field': 'value'}, schema, strict=True)
    
    with pytest.raises(FieldKeyError):
        config['non_existent_field']
    
    with pytest.raises(FieldKeyError):
        config.update(non_existent_field='value')

def test_config_non_strict_mode():
    schema = [dict(field='allowed_field', required=True, rules=dict(type='str'))]
    config = Config({'allowed_field': 'value'}, schema, strict=False)
    
    config.update(non_existent_field='value')
    assert config['non_existent_field'] == 'value'

def test_config_nested_update(sample_schema, sample_config):
    config = Config(sample_config, sample_schema)
    config.update({'nested': {'value': 0.8}})
    assert config['nested.value'] == 0.8

def test_config_from_json(sample_schema):
    json_str = '{"name": "Jane Doe", "age": 25, "email": "jane.doe@example.com", "nested": {"value": 0.3}}'
    config = Config.from_json(json_str, sample_schema)
    assert config['name'] == 'Jane Doe'
    assert config['age'] == 25
    assert config['nested.value'] == 0.3

def test_config_nested_attribute_access(sample_schema, sample_config):
    config = Config()
    # with pytest.raises(AttributeError):
    #     config.a = 1
    
    config._a = 1
    assert config._a == 1
    assert config.to_dict() == {}
    
    config = Config(strict=False)
    with pytest.raises(AttributeError):
        config.a = 1
    
    config = Config()
    config['a.b.c'] = 3
    config['a.e'] = 5
    assert config.to_dict() == {'a': {'b': {'c': 3}, 'e': 5}}
    print(config.to_dict())
    
def test_getenv():
    config_dict = {
        'database': {
            'host': '!env DATABASE_HOST',
            'port': '!env DATABASE_PORT'
        }
    }

    config_schema = [
        dict(field='database.host', required=True, rules=dict(type='str')),
        dict(field='database.port', required=True, rules=dict(type='int', min=1, max=65535))
    ]

    # # 设置环境变量
    os.environ['DATABASE_HOST'] = 'localhost'
    os.environ['DATABASE_PORT'] = '5555'

    config = Config.from_dict(config_dict, schema=config_schema)

    assert config.database.host == 'localhost'
    assert config.database.port == '5555'
    print(config.database.host)  # 输出: localhost
    print(config.database.port)  # 输出: 5432

def test_allowed_and_disallowed_values():
    schema = [
        dict(field='status', required=True, rules=dict(
            type='str',
            allowed_values=['active', 'inactive', 'pending']
        )),
        dict(field='error_code', required=True, rules=dict(
            type='int',
            disallowed_values=[0, 999]
        ))
    ]

    # 测试有效配置
    valid_config = {
        'status': 'active',
        'error_code': 404
    }
    config = Config(valid_config, schema)
    assert config.status == 'active'
    assert config.error_code == 404

    # 测试 allowed_values 规则
    with pytest.raises(FieldValidationError) as exc_info:
        print('*******1', schema)
        Config({'status': 'deleted', 'error_code': 404}, schema)
    assert "Field `status` with value deleted is not in the allowed values" in str(exc_info.value)

    # 测试 disallowed_values 规则
    with pytest.raises(FieldValidationError) as exc_info:
        print('*******', schema)
        Config({'status': 'active', 'error_code': 0}, schema)
    assert "Field `error_code` with value 0 is in the disallowed values" in str(exc_info.value)

    # 测试更新操作
    config = Config(valid_config, schema)
    with pytest.raises(FieldValidationError):
        config.update(status='expired')
    
    with pytest.raises(FieldValidationError):
        config.update(error_code=999)

    # 测试有效更新
    config.update(status='inactive', error_code=500)
    assert config.status == 'inactive'
    assert config.error_code == 500

def test_additional_validation_rules():
    schema = [
        dict(field='status', required=True, rules=dict(
            type='str',
            choices=['active', 'inactive', 'pending']
        )),
        dict(field='score', required=True, rules=dict(
            type='int',
            range=(0, 100)
        )),
        dict(field='username', required=True, rules=dict(
            type='str',
            pattern=r'^[a-zA-Z0-9_]{3,16}$'
        )),
        dict(field='tags', required=True, rules=dict(
            type='list',
            unique=True
        )),
        dict(field='description', required=True, rules=dict(
            type='str',
            contains='important'
        ))
    ]

    valid_config = {
        'status': 'active',
        'score': 85.5,
        'username': 'user_123',
        'tags': ['tag1', 'tag2', 'tag3'],
        'description': 'This is an important message'
    }

    config = Config(valid_config, schema)
    assert config.status == 'active'
    assert config.score == 85.5
    assert config.username == 'user_123'
    assert config.tags == ['tag1', 'tag2', 'tag3']
    assert config.description == 'This is an important message'

    # Test choices rule
    with pytest.raises(FieldValidationError) as exc_info:
        config = Config({**valid_config, 'status': 'deleted'}, schema)
        print(config.to_dict())
    assert "Field `status` with value deleted is not in the choices" in str(exc_info.value)

    # return
    # Test range rule
    with pytest.raises(FieldValidationError) as exc_info:
        Config({**valid_config, 'score': 101}, schema)
    assert "Field `score` with value 101 is not in the range" in str(exc_info.value)

    # Test pattern rule
    with pytest.raises(FieldValidationError) as exc_info:
        Config({**valid_config, 'username': 'user@123'}, schema)
    assert "Field `username` does not match the required pattern" in str(exc_info.value)

    # Test unique rule
    with pytest.raises(FieldValidationError) as exc_info:
        Config({**valid_config, 'tags': ['tag1', 'tag2', 'tag1']}, schema)
    assert "Field `tags` contains duplicate values" in str(exc_info.value)

    # Test contains rule
    with pytest.raises(FieldValidationError) as exc_info:
        Config({**valid_config, 'description': 'This is a message'}, schema)
    assert "Field `description` does not contain the required substring" in str(exc_info.value)

def test_choices_vs_allowed_values():
    schema = [
        dict(field='color', required=True, rules=dict(
            type='str',
            choices=['red', 'green', 'blue']
        )),
        dict(field='country', required=True, rules=dict(
            type='str',
            allowed_values=['USA', 'Canada', 'UK', 'France', 'Germany', 'Japan', 'Australia', 'Brazil', 'China', 'India']
        ))
    ]

    valid_config = {
        'color': 'red',
        'country': 'USA'
    }

    config = Config(valid_config, schema)
    assert config.color == 'red'
    assert config.country == 'USA'

    # Test choices with too many options
    with pytest.raises(FieldValidationError) as exc_info:
        Config({'color': 'red', 'country': 'USA'}, [
            dict(field='color', required=True, rules=dict(
                type='str',
                choices=['red', 'green', 'blue', 'yellow', 'purple', 'orange', 'pink', 'brown', 'gray', 'black',
                         'white', 'cyan', 'magenta', 'lime', 'olive', 'maroon', 'navy', 'teal', 'silver', 'gold', 'extra']
            ))
        ])
    assert "has too many options. Use `allowed_values` for larger sets" in str(exc_info.value)

    # Test allowed_values with many options (should work fine)
    many_countries = ['USA', 'Canada', 'UK', 'France', 'Germany', 'Japan', 'Australia', 'Brazil', 'China', 'India',
                      'Russia', 'Italy', 'Spain', 'Mexico', 'South Korea', 'Netherlands', 'Sweden', 'Switzerland', 
                      'Norway', 'Denmark', 'Finland', 'Belgium', 'Austria', 'New Zealand', 'Ireland']
    config = Config({'country': 'USA'}, [
        dict(field='country', required=True, rules=dict(
            type='str',
            allowed_values=many_countries
        ))
    ])
    assert config.country == 'USA'

def test_len_rule():
    schema = [
        dict(field='code', required=True, rules=dict(
            type='str',
            len=6
        )),
        dict(field='items', required=True, rules=dict(
            type='list',
            len=3
        )),
        dict(field='data', required=True, rules=dict(
            type='dict',
            len=2
        ))
    ]

    valid_config = {
        'code': '123456',
        'items': ['a', 'b', 'c'],
        'data': {'key1': 'value1', 'key2': 'value2'}
    }

    config = Config(valid_config, schema)
    assert config.code == '123456'
    assert config.items == ['a', 'b', 'c']
    assert config.data.to_dict() == {'key1': 'value1', 'key2': 'value2'}

    # Test string length
    with pytest.raises(FieldValidationError) as exc_info:
        Config({**valid_config, 'code': '12345'}, schema)
    assert "Field `code` length 5 does not match the expected length: 6" in str(exc_info.value)

    # Test list length
    with pytest.raises(FieldValidationError) as exc_info:
        Config({**valid_config, 'items': ['a', 'b', 'c', 'd']}, schema)
    assert "Field `items` length 4 does not match the expected length: 3" in str(exc_info.value)

    # Test dict length
    with pytest.raises(FieldValidationError) as exc_info:
        Config({**valid_config, 'data': {'key1': 'value1'}}, schema)
    assert "Field `data` length 1 does not match the expected length: 2" in str(exc_info.value)
    
def test_mix_field():
    schema = [
        dict(field='status', required=True, type='str', 
             choices=['active', 'inactive', 'pending']),
        Field('status2', required=True, type='str', 
             choices=['active', 'inactive', 'pending'])
    ]
    
    config_dict = {
        'status': 'active',
        'status2': 'active'
    }
    config = Config(config_dict, schema)
    print(config.to_dict())
    
def test_schema_of_schema():
    schema = Schema(
        Field('status', required=True, type='str', 
             choices=['active', 'inactive', 'pending']),
        Field('optimizer', required=True, schema=Schema(
            Field('type', required=True, type='str', 
                  choices=['sgd', 'adam', 'rmsprop', 
                           'adagrad', 'adadelta', 'adamax',
                           'nadam', 'ftrl']),
            Field('lr', required=True, type='float', min=0, max=1),
            Field('momentum', required=False, type='float', min=0, max=1, default=0.9),
            Field('nesterov', required=False, type='bool', default=False)
        )),
    )
    config = Config({'status': 'active', 'optimizer': {
        'type': 'sgd', 'lr': 0.1, 'momentum': 0.9, 'nesterov': False}}, schema)
    print(json.dumps(config.to_dict(), ensure_ascii=False))
    pass
    
    
if __name__ == '__main__':
    if 1:
        test_schema_of_schema()