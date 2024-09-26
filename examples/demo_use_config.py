import os
from cfgdict import Config

config_schema = [
    dict(field='API_KEY', required=True, rules=dict(type='str')),
    dict(field='n_step', required=True, default=3, rules=dict(type='int', gt=0)),
    dict(field='learning_rate', required=True, default=0.1, rules=dict(type='float', gt=0, max=1)),
    dict(field='nest.gamma', required=True, default=0.99, rules=dict(type='float', min=0, max=1)),
    dict(field='nest.epsilon', required=True, default=0.1, rules=dict(type='float', min=0, max=1)),
    dict(field='nest.verbose_freq', required=True, default=10, rules=dict(type='int', gt=0)),
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