
default_version = 'v2'

def make_config_v1(config, schema, strict=False, logger=None, to_dict=False, to_dict_flatten=False, to_dict_sep='.'):
    from .v1 import Config as Config_v1
    config = Config_v1(config, schema=schema, strict=strict, logger=logger)
    if to_dict:
        return config.to_dict(flatten=to_dict_flatten, sep=to_dict_sep)
    return config

def make_config_v2(config, schema, strict=False, logger=None, to_dict=False, to_dict_flatten=False, to_dict_sep='.'):
    from .v2 import Config as Config_v2
    config = Config_v2(config, schema=schema, strict=strict, logger=logger)
    if to_dict:
        return config.to_dict(flatten=to_dict_flatten, sep=to_dict_sep)
    return config

def make_config(config, schema, strict=False, logger=None, to_dict=False, 
                to_dict_flatten=False, to_dict_sep='.', version=None):
    if version is None:
        version = default_version
    if version == 'v1':
        return make_config_v1(config, schema, strict, logger, to_dict, to_dict_flatten, to_dict_sep)
    elif version == 'v2':
        return make_config_v2(config, schema, strict, logger, to_dict, to_dict_flatten, to_dict_sep)
    else:
        raise ValueError(f"Unsupported version: {version}")

if default_version == 'v1':
    from .v1 import Config
    __all__ = ['make_config', 'Config']
else:
    from .v2 import Config
    __all__ = ['make_config', 'Config']
