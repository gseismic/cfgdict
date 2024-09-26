from cfgdict import Config

config_schema = [
    dict(field='n_step', required=True, default=3, rules=dict(type='int', gt=0)),
    dict(field='learning_rate', required=True, default=0.1, rules=dict(type='float', gt=0, max=1)),
    dict(field='nest.gamma', required=True, default=0.99, rule=dict(type='float', min=0, max=1)),
    dict(field='nest.epsilon', required=True, default=0.1, rules=dict(type='float', min=0, max=1)),
    dict(field='nest.verbose_freq', required=False, default=10, rules=dict(type='int', gt=0)),
]
cfg_dict = {'n_step': 3, 'learning_rate': 0.1, 'nest': {'gamma': 0.99, 'epsilon': 0.1}}
config = Config.from_dict(cfg_dict, schema=config_schema, strict=True)

print(config.to_dict())
assert config.to_dict() == {'n_step': 3, 'learning_rate': 0.1, 'nest': {'gamma': 0.99, 'epsilon': 0.1, 'verbose_freq': 10}}