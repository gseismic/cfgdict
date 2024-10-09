import pytest
from cfgdict.schema import Schema, Field

def test_schema_init_and_access():
    schema = Schema(
        name=Field("name", required=True),
        age=Field("age", default=18),
        email={"required": False}
    )
    assert "name" in schema and schema["name"].required
    assert "age" in schema and schema["age"].default == 18
    assert "email" in schema and not schema["email"].required
    assert len(schema) == 3 and set(schema) == {"name", "age", "email"}

def test_schema_modification():
    schema = Schema()
    schema.new_field = Field("new_field", default="test")
    schema["another_field"] = {"required": True}
    schema.another_field = {"required": True}
    assert schema.new_field.default == "test"
    assert schema["another_field"].required

def test_schema_from_methods():
    dict_data = {"name": {"required": True}, "age": {"default": 18}}
    list_data = [{"field": "name", "required": True}, {"field": "age", "default": 18}]
    json_data = '{"name": {"required": true}, "age": {"default": 18}}'
    
    schema_dict = Schema.from_dict(dict_data)
    schema_list = Schema.from_list(list_data)
    schema_json = Schema.from_json(json_data)
    
    for schema in [schema_dict, schema_list, schema_json]:
        assert schema["name"].required and schema["age"].default == 18

def test_schema_iteration():
    schema = Schema(a=Field("a"), b=Field("b"), c=Field("c"))
    assert list(schema) == ["a", "b", "c"]

def test_schema_copy():
    from copy import deepcopy
    schema = Schema(name=Field("name", required=True))
    schema_copy = deepcopy(schema)
    assert schema["name"].required == schema_copy["name"].required
    assert schema is not schema_copy

def test_schema_of_schema():
    schema = Schema(
        Field('status', required=True, type='str', 
             choices=['active', 'inactive', 'pending']),
        Field('optimizer', required=True, schema=Schema(
            Field('type', required=True, type='str', 
                  choices=['sgd', 'adam', 'rmsprop', 
                           'adagrad', 'adadelta', 'adamax',
                           'nadam', 'ftrl']),
            Field('lr', required=True, type='float', min=0, max=1))
    ))
    print(schema)
    print(schema.to_dict())
    
if __name__ == "__main__":
    test_schema_of_schema()