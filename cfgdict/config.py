import re
import json
import yaml
import os
import arrow
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union, Set
from copy import deepcopy
from loguru import logger as default_logger
from .utils import flatten_dict

class ConfigValidationError(Exception):
    pass

class ConfigKeyError(Exception):
    pass

class Config:
    def __init__(self, 
                 config_dict: Optional[Dict[str, Any]] = None, 
                 schema: Optional[List[Dict[str, Any]]] = None, 
                 strict: bool = None, 
                 verbose: bool = None, 
                 logger: Optional[Any] = None):
        """
        Initialize a Config object.

        Args:
            config_dict: Initial configuration dictionary.
            schema: List of schema definitions for the configuration.
            strict: If True, raise errors for undefined fields.
            verbose: If True, log detailed information.
            logger: Custom logger object.
        """
        self._config = config_dict or {}
        self._schema = {item['field']: item for item in (schema or [])}
        self._strict = strict or False
        self._verbose = verbose or False
        self._logger = logger or default_logger

        self._validate_schema()
        self._validate_and_set(self._config)

    def _validate_schema(self) -> None:
        """Validate the configuration schema."""
        for field, field_schema in self._schema.items():
            if 'field' not in field_schema:
                raise ConfigValidationError("Each schema item must have a 'field' key")
            if 'rules' in field_schema and not isinstance(field_schema['rules'], dict):
                raise ConfigValidationError(f"Rules for field '{field}' must be a dictionary")
            if not field_schema.get('required', False) and 'default' not in field_schema:
                raise ConfigValidationError(f"Field '{field}' is not required but has no default value")

    def _validate_and_set(self, config: Dict[str, Any]):
        # First pass: set all values without validation
        for field, schema in self._schema.items():
            value = self._get_nested_value(config, field)
            if value is None:
                if schema.get('required', False):
                    raise ConfigValidationError(f"Missing required field: {field}")
                value = schema['default']
                if self._verbose:
                    self._logger.info(f"Using default value for '{field}': {value}")
            value = self._resolve_value(value)  # 解析环境变量
            self._set_nested_value(field, value)

        # Second pass: validate all fields
        for field, schema in self._schema.items():
            value = self._get_nested_value(self._config, field)
            if value is not None:
                self._validate_field(field, value, schema.get('rules', {}))

    def _validate_field(self, field: str, value: Any, rules: Dict[str, Any]):
        if 'type' in rules:
            value = self._convert_type(value, rules['type'])

        for rule, rule_value in rules.items():
            if rule in ['min', 'max', 'gt', 'lt', 'ge', 'le', 'ne']:
                self._apply_comparison_rule(field, value, rule, self._resolve_reference(rule_value))
            elif rule in ['min_len', 'max_len']:
                self._apply_length_rule(field, value, rule, self._resolve_reference(rule_value))
            elif rule == 'regex':
                self._apply_regex_rule(field, value, rule_value)
            elif rule == 'custom':
                self._apply_custom_rule(field, value, rule_value)

        return value

    def _apply_custom_rule(self, field: str, value: Any, custom_func):
        if not callable(custom_func):
            raise ConfigValidationError(f"Custom rule for field '{field}' must be a callable")
        try:
            custom_func(value)
        except Exception as e:
            raise ConfigValidationError(f"Custom validation failed for field '{field}': {str(e)}")

    def _convert_type(self, value: Any, expected_type: str) -> Any:
        type_mapping = {
            'str': str,
            'int': int,
            'float': float,
            'bool': bool,
            'list': list,
            'dict': dict,
            'date': self._parse_date,
            'datetime': self._parse_datetime
        }
        if expected_type not in type_mapping:
            raise ConfigValidationError(f"Unsupported type: {expected_type}")
        try:
            return type_mapping[expected_type](value)
        except ValueError:
            raise ConfigValidationError(f"Cannot convert value to {expected_type}: {value}")

    def _apply_comparison_rule(self, field: str, value: Any, rule: str, rule_value: Any):
        if not isinstance(value, (int, float, date, datetime)):
            raise ConfigValidationError(f"Comparison rule '{rule}' not applicable for field '{field}' of type {type(value)}")
        
        comparison_ops = {
            'min': lambda x, y: x >= y,
            'max': lambda x, y: x <= y,
            'gt': lambda x, y: x > y,
            'lt': lambda x, y: x < y,
            'ge': lambda x, y: x >= y,
            'le': lambda x, y: x <= y,
            'ne': lambda x, y: x != y
        }
        
        if not comparison_ops[rule](value, rule_value):
            raise ConfigValidationError(f"Field '{field}' with value {value} does not satisfy the {rule} condition: {rule_value}")

    def _apply_length_rule(self, field: str, value: Any, rule: str, rule_value: int):
        if not hasattr(value, '__len__'):
            raise ConfigValidationError(f"Length rule '{rule}' not applicable for field '{field}' of type {type(value)}")
        
        if rule == 'min_len' and len(value) < rule_value:
            raise ConfigValidationError(f"Field '{field}' length {len(value)} is less than the minimum length: {rule_value}")
        elif rule == 'max_len' and len(value) > rule_value:
            raise ConfigValidationError(f"Field '{field}' length {len(value)} is greater than the maximum length: {rule_value}")

    def _apply_regex_rule(self, field: str, value: str, pattern: str):
        if not isinstance(value, str):
            raise ConfigValidationError(f"Regex rule not applicable for field '{field}' of type {type(value)}")
        
        if not re.match(pattern, value):
            raise ConfigValidationError(f"Field '{field}' does not match the required pattern: {pattern}")

    def _parse_datetime(self, value: Union[str, int, float, datetime]) -> datetime:
        if isinstance(value, datetime):
            return value
        try:
            return arrow.get(value).datetime
        except arrow.ParserError:
            raise ConfigValidationError(f"Invalid datetime format: {value}")

    def _parse_date(self, value: Union[str, int, float, date]) -> date:
        if isinstance(value, date):
            return value
        try:
            return arrow.get(value).date()
        except arrow.ParserError:
            raise ConfigValidationError(f"Invalid date format: {value}")

    def _get_nested_value(self, config: Dict[str, Any], field: str) -> Any:
        keys = field.split('.')
        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
                value = self._resolve_value(value)  # 解析环境变量
            else:
                return None
        return value

    def _set_nested_value(self, field: str, value: Any):
        keys = field.split('.')
        current = self._config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            elif not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        
        if isinstance(value, dict) and keys[-1] in current and isinstance(current[keys[-1]], dict):
            # 如果新值是字典，且当前值也是字典，我们需要递归地更新
            self._update_nested_dict(current[keys[-1]], value)
        else:
            current[keys[-1]] = value
    
    def _resolve_value(self, value):
        if isinstance(value, str):
            if value.lower().startswith('!env'):
                env_key = value[4:].strip().lstrip('{').rstrip('}').strip()
                value = os.getenv(env_key)
        return value

    def _update_nested_dict(self, current: dict, update: dict):
        for k, v in update.items():
            if isinstance(v, dict) and k in current and isinstance(current[k], dict):
                self._update_nested_dict(current[k], v)
            else:
                current[k] = v

    def __getitem__(self, key: str) -> Any:
        value = self._get_nested_value(self._config, key)
        if value is None and not self._key_exists(self._config, key):
            raise ConfigKeyError(key)
        return value

    def __getattr__(self, name: str) -> Any:
        try:
            value = self._get_nested_value(self._config, name)
            if value is None:
                # 如果值为None，我们需要检查这个键是否真的存在
                if not self._key_exists(self._config, name):
                    raise ConfigKeyError(name)
            
            if isinstance(value, dict):
                return Config(value, strict=self._strict, verbose=self._verbose, logger=self._logger)
            
            return value
        except ConfigKeyError:
            raise AttributeError(f"'Config' object has no attribute '{name}'")

    def _key_exists(self, config: Dict[str, Any], field: str) -> bool:
        keys = field.split('.')
        current = config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return False
        return True

    def __setitem__(self, key: str, value: Any):
        self.update({key: value})
        
    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            raise AttributeError('Not allowed, use `__setitem__` or `update()`')

    def update(self, *args, **kwargs):
        """
        Update the configuration with new values.

        This method behaves similarly to dict.update().
        It can be called with either another dictionary as an argument,
        or with keyword arguments.

        Args:
            *args: A dictionary of configuration values.
            **kwargs: Keyword arguments of configuration values.
        """
        if args:
            if len(args) > 1:
                raise TypeError("update expected at most 1 arguments, got %d" % len(args))
            other = dict(args[0])
            kwargs.update(other)

        for field, value in kwargs.items():
            if field in self._schema:
                self._validate_field(field, value, self._schema[field].get('rules', {}))
                self._set_nested_value(field, value)
            elif self._strict:
                raise ConfigKeyError(f"Unknown configuration key: {field}")
            else:
                self._set_nested_value(field, value)

        self._validate_and_set(self._config)

    def diff(self, other: 'Config') -> Dict[str, Dict[str, Any]]:
        """
        Compare this configuration with another and return the differences.

        Args:
            other: Another Config object to compare with.

        Returns:
            A dictionary containing the differences. Each key is a field name,
            and the value is a dictionary with 'self' and 'other' keys showing
            the different values.
        """
        differences = {}
        all_keys = set(self._config.keys()) | set(other._config.keys())

        for key in all_keys:
            self_value = self._get_nested_value(self._config, key)
            other_value = other._get_nested_value(other._config, key)

            if self_value != other_value:
                differences[key] = {
                    'self': self_value,
                    'other': other_value
                }

        return differences

    def to_dict(self, flatten=False, sep='.') -> Dict[str, Any]:
        if not flatten:
            return self._config
        else:
            return flatten_dict(self._config, sep=sep)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any], schema: List[Dict[str, Any]], strict: bool = None, verbose: bool = None, logger: Optional[Any] = None):
        return cls(config_dict, schema, strict, verbose, logger)

    @classmethod
    def from_json(cls, json_str: str, schema: List[Dict[str, Any]], strict: bool = None, verbose: bool = None, logger: Optional[Any] = None):
        config_dict = json.loads(json_str)
        return cls(config_dict, schema, strict, verbose, logger)

    @classmethod
    def from_yaml(cls, yaml_str: str, schema: List[Dict[str, Any]], strict: bool = True, verbose: bool = False, logger: Optional[Any] = None):
        config_dict = yaml.safe_load(yaml_str)
        return cls(config_dict, schema, strict, verbose, logger)

    @classmethod
    def from_file(cls, file_path: str, schema: List[Dict[str, Any]], strict: bool = True, verbose: bool = False, logger: Optional[Any] = None):
        _, ext = os.path.splitext(file_path)
        with open(file_path, 'r') as f:
            if ext.lower() == '.json':
                return cls.from_json(f.read(), schema, strict, verbose, logger)
            elif ext.lower() in ['.yaml', '.yml']:
                return cls.from_yaml(f.read(), schema, strict, verbose, logger)
            else:
                raise ConfigValidationError(f"Unsupported file format: {ext}")

    def _resolve_reference(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith('$'):
            referenced_field = value[1:]
            referenced_value = self._get_nested_value(self._config, referenced_field)
            return referenced_value
        return value
