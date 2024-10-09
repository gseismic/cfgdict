from typing import Dict, Any
import os
from .exception import FieldValidationError, FieldKeyError


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """Flatten dict
    
    example:
        d = {'a': 1, 'b': {'c': 3}}
        dd = flatten_dict(d)
        assert dd == {'a': 1, 'b.c': 3}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(d, logger=None):
    """Unflatten dict
    
    example:
        d = {'a.b': 1, 'optim': {'lr': 1}}
        dd = unflatten_dict(d)
        assert dd == {'a': {'b': 1}, 'optim': {'lr': 1}}
    """
    result = {}
    for key, value in d.items():
        parts = key.split('.')
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            elif not isinstance(current[part], dict):
                current[part] = {"": current[part]}
            current = current[part]
            
        if isinstance(value, dict):
            if parts[-1] not in current:
                current[parts[-1]] = {}
            path = key + "."
            nested_update_dict(current[parts[-1]], unflatten_dict(value), logger=logger, path=path)
        else:
            if parts[-1] not in current:
                current[parts[-1]] = value
            else:
                if logger is not None:
                    logger.info(f"Overwriting `{path}{parts[-1]}`: {current[parts[-1]]} -> {value}")
                current[parts[-1]] = value
    return result


def nested_update_dict(d, u, logger=None, path=""):
    """Nested update dict with logging
    
    Note:
        - {'a.x': 1} 'a.x' not allowed
    
    example:
        d = {'a': 1, 'b': 2, 'c': 3}
        u = {'a': 10, 'b': 20, 'd': 40}
        nested_update_dict(d, u, logger=logger)
        assert d == {'a': 10, 'b': 20, 'c': 3, 'd': 40}
    """
    for k, v in u.items():
        if isinstance(v, dict):
            d[k] = nested_update_dict(d.get(k, {}), v,  logger=logger, path=path + k + ".")
        else:
            if logger is not None:
                if k in d and d[k] is not None and d[k] != v:
                    logger.info(f"Overwriting `{path}{k}`: {d[k]} -> {v}")
            d[k] = v
    return d


def resolve_value(value):
    """Resolve value
    
    example1:
        value = "!env{PATH}"
        value = resolve_value(value)
        assert value == os.getenv("PATH")
    example2:
        value = "!env PATH"
        value = resolve_value(value)
        assert value == os.getenv("PATH")
    """
    if isinstance(value, str):
        if value.lower().startswith('!env'):
            env_key = value[4:].strip().lstrip('{').rstrip('}').strip()
            value = os.getenv(env_key)
    return value


def nested_get_from_dict(field:str, config: Dict[str, Any],
                         default: Any = None, unflatten: bool = True,
                         raise_error: bool = False) -> Any:
    """Get nested value
    
    example:
        field = "a.b"
        config = {"a": {"b": 1}}
        value = nested_get_from_dict(field, config)
        assert value == 1
    """
    if unflatten:
        config = unflatten_dict(config)
    keys = field.split('.')
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
            value = resolve_value(value)  # 解析环境变量
        else:
            if raise_error:
                raise KeyError(f"Key `{keys}` not found in config")
            else:
                return default
    return value

def nested_set_dict(config, field: str, value: Any, logger=None):
    keys = field.split('.')
    current = config
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    
    if isinstance(value, dict) and keys[-1] in current and isinstance(current[keys[-1]], dict):
        nested_update_dict(current[keys[-1]], value, logger=logger)
    else:
        current[keys[-1]] = value

def get_default_dict_by_schema(schema):
    """Nested default dict by schema
    """
    full_defauls = {}
    for key, field in schema.items():
        if field.schema:
            assert field.default is None, "field.default must be None"
            defaults = get_default_dict_by_schema(field.schema)
            full_defauls[key] = defaults
        else:
            default = field.default if field else None
            full_defauls[key] = default
    return full_defauls


def make_dict(config_dict, schema, logger=None) -> Dict[str, Any]:
    """
    """
    config_dict = unflatten_dict(config_dict, logger=logger)
    if schema is None:
        return config_dict
    
    keys_dict = set(config_dict.keys())
    keys_schema = set(schema.keys())
    keys = keys_dict.union(keys_schema)
    for key in keys:
        field = schema.get(key)
        value = config_dict.get(key)
        if isinstance(value, dict):
            field_schema = field.schema if field else None
            config_dict[key] = make_dict(value, field_schema, logger=logger)
        else:
            if value is None:
                if field:
                    if field.required:
                        raise FieldKeyError(f"Field `{key}` is required but not found in config")
                    else:
                        field_default = field.default
                        if field_default is not None:
                            config_dict[key] = field_default
                        else:
                            if logger is not None:
                                logger.warning(f"Field `{key}` is None or not found in config and no default value is set in schema")
                            config_dict[key] = None
                else:
                    if logger is not None:
                        logger.warning(f"Field `{key}` is None or not found in config and no default value is set in schema")
                    config_dict[key] = None
            elif isinstance(value, str):
                config_dict[key] = resolve_value(value)
            else:
                config_dict[key] = value
                
    return config_dict
