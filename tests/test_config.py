import os
import pytest
from cfgdict import Config, ConfigValidationError, ConfigKeyError

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
    print('==config', config.to_dict())
    assert config['name'] == 'John Doe'
    assert config['age'] == 30
    assert config['email'] == 'john.doe@example.com'
    assert config['nested.value'] == 0.5

def test_config_validation_error(sample_schema):
    invalid_config = {
        'name': 'J',  # Too short
        'age': 150,   # Too high
        'email': 'invalid-email',
        'nested': {'value': 1.5}  # Too high
    }
    with pytest.raises(ConfigValidationError):
        Config(invalid_config, sample_schema)

def test_config_missing_required_field(sample_schema):
    incomplete_config = {
        'name': 'John Doe',
        'age': 30
    }
    with pytest.raises(ConfigValidationError):
        Config(incomplete_config, sample_schema)

def test_config_update(sample_schema, sample_config):
    config = Config(sample_config, sample_schema)
    config.update(age=31, nested={'value': 0.7})
    assert config['age'] == 31
    assert config['nested.value'] == 0.7
    
    config = Config()
    config.update({'field1': 'value1', 'field2': 'value2'})
    # 或者
    config.update(field1='value1', field2='value2')
    # 或者两者结合
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
    
    with pytest.raises(ConfigKeyError):
        config['non_existent_field']
    
    with pytest.raises(ConfigKeyError):
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