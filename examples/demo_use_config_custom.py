
from cfgdict.v1 import Config, FieldValidationError

def validate_even(value):
    if value % 2 != 0:
        raise FieldValidationError(f"Value {value} is not even")

config_schema = [
    dict(field='even_number', required=True, rules=dict(type='int', custom=validate_even))
]

config = Config.from_dict({'even_number': 4}, schema=config_schema) 

print(config.to_dict())
