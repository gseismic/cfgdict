import os
from cfgdict.v2 import Config, Field, Schema

config_schema = [
    dict(name='API_KEY', required=True, type='str'),
    Field('n_step', required=True, type='int', gt=0),
    Field('learning_rate', required=True, 
          rules=dict(type='float', gt=0, max=1), gt=1e-3),
    Field('nest', required=True, 
          schema=Schema(
              Field('gamma', required=True, type='float', min=0, max=1),
              Field('epsilon', required=True, type='float', min=0, max=1),
              Field('verbose_freq', required=True, type='int', gt=0))
          )
]

os.environ['API_KEY'] = 'secret-xxxxxx'

cfg_dict = {
    'API_KEY': '!env API_KEY',
    'n_step': 3,
    'learning_rate': 0.1,
    'nest': {
        'gamma': 0.99,
        'epsilon': 0.1,
        'verbose_freq': 10
    }
}

config = Config.from_dict(cfg_dict, schema=config_schema, strict=True)
print(config.to_dict())
print(config.schema)
