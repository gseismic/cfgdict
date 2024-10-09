import re
import os
import json
import yaml
import arrow
from pathlib import Path
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union, Tuple
from loguru import logger as default_logger
from .utils import flatten_dict, resolve_value, nested_get_from_dict
from .schema import Field, Schema
from .exception import FieldValidationError, FieldKeyError


class Config:
    def __init__(self, 
                 config_dict: Optional[Dict[str, Any]] = None, 
                 schema: Optional[List[Dict[str, Any]]] = None, 
                 strict: bool = False,
                 verbose: bool = False, 
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
        self._schema = Schema.make_schema(schema)
        self._strict = strict or False
        self._verbose = verbose or False
        self._logger = logger or default_logger

        self._validate_and_set(self._config)

    def _validate_and_set(self, config: Dict[str, Any]):
        # First pass: set all values without validation
        for key, field in self._schema.items():
            if field.schema is not None:
                pass
            else:
                value = self._get_nested_value(config, key)
                if value is None:
                    if field.required:
                        raise FieldValidationError(f"Missing required field: `{key}`")
                    value = field.default
                    if self._verbose:
                        self._logger.info(f"Using default value for `{key}`: {value}")
                value = resolve_value(value)
                self._set_nested_value(key, value)

        # Second pass: validate all fields
        for key, field in self._schema.items():
            value = self._get_nested_value(self._config, key)
            if value is not None:
                self._validate_field(key, value, field.rules)

    def _validate_field(self, field: str, value: Any, rules: Dict[str, Any]):        
        if 'type' in rules:
            value = self._convert_type(value, rules['type'])

        for rule, rule_value in rules.items():
            if rule in ['min', 'max', 'gt', 'lt', 'ge', 'le', 'ne']:
                self._apply_comparison_rule(field, value, rule, self._resolve_reference(rule_value))
            elif rule in ['min_len', 'max_len', 'len']:
                self._apply_length_rule(field, value, rule, self._resolve_reference(rule_value))
            elif rule == 'regex':
                self._apply_regex_rule(field, value, rule_value)
            elif rule == 'custom':
                self._apply_custom_rule(field, value, rule_value)
            elif rule == 'allowed_values':
                self._apply_allowed_values_rule(field, value, self._resolve_reference(rule_value))
            elif rule == 'disallowed_values':
                self._apply_disallowed_values_rule(field, value, self._resolve_reference(rule_value))
            elif rule == 'choices':
                self._apply_choices_rule(field, value, self._resolve_reference(rule_value))
            elif rule == 'range':
                self._apply_range_rule(field, value, self._resolve_reference(rule_value))
            elif rule == 'pattern':
                self._apply_pattern_rule(field, value, rule_value)
            elif rule == 'unique':
                self._apply_unique_rule(field, value)
            elif rule == 'contains':
                self._apply_contains_rule(field, value, self._resolve_reference(rule_value))
            else:
                if rule != 'type':
                   raise FieldValidationError(f"Unknown rule: `{rule}`")

        return value

    def _apply_custom_rule(self, field: str, value: Any, custom_func):
        if not callable(custom_func):
            raise FieldValidationError(f"Custom rule for field `{field}` must be a callable")
        try:
            custom_func(value)
        except Exception as e:
            raise FieldValidationError(f"Custom validation failed for field `{field}`: {str(e)}")

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
            raise FieldValidationError(f"Unsupported type: `{expected_type}`")
        try:
            return type_mapping[expected_type](value)
        except ValueError:
            raise FieldValidationError(f"Cannot convert value to `{expected_type}`: {value}")

    def _apply_comparison_rule(self, field: str, value: Any, rule: str, rule_value: Any):
        if not isinstance(value, (int, float, date, datetime)):
            raise FieldValidationError(f"Comparison rule '{rule}' not applicable for field `{field}` of type {type(value)}")
        
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
            raise FieldValidationError(f"Field `{field}` with value {value} does not satisfy the {rule} condition: {rule_value}")

    def _apply_length_rule(self, field: str, value: Any, rule: str, rule_value: int):
        if not hasattr(value, '__len__'):
            raise FieldValidationError(f"Length rule '{rule}' not applicable for field `{field}` of type {type(value)}")
        
        if rule == 'min_len' and len(value) < rule_value:
            raise FieldValidationError(f"Field `{field}` length {len(value)} is less than the minimum length: {rule_value}")
        elif rule == 'max_len' and len(value) > rule_value:
            raise FieldValidationError(f"Field `{field}` length {len(value)} is greater than the maximum length: {rule_value}")
        elif rule == 'len' and len(value) != rule_value:
            raise FieldValidationError(f"Field `{field}` length {len(value)} does not match the expected length: {rule_value}")

    def _apply_regex_rule(self, field: str, value: str, pattern: str):
        if not isinstance(value, str):
            raise FieldValidationError(f"Regex rule not applicable for field `{field}` of type {type(value)}")
        
        if not re.match(pattern, value):
            raise FieldValidationError(f"Field `{field}` does not match the required pattern: {pattern}")

    def _apply_allowed_values_rule(self, field: str, value: Any, allowed_values: List[Any]):
        if not isinstance(allowed_values, list):
            raise FieldValidationError(f"'allowed_values' rule for field `{field}` must be a list")
        if value not in allowed_values:
            raise FieldValidationError(f"Field `{field}` with value {value} is not in the allowed values: {allowed_values}")

    def _apply_disallowed_values_rule(self, field: str, value: Any, disallowed_values: List[Any]):
        if not isinstance(disallowed_values, list):
            raise FieldValidationError(f"'disallowed_values' rule for field `{field}` must be a list")
        if value in disallowed_values:
            raise FieldValidationError(f"Field `{field}` with value {value} is in the disallowed values: {disallowed_values}")

    def _apply_choices_rule(self, field: str, value: Any, choices: List[Any]):
        if not isinstance(choices, list):
            raise FieldValidationError(f"'choices' rule for field `{field}` must be a list")
        if len(choices) > 20:  # 假设我们限制choices最多有20个选项
            raise FieldValidationError(f"'choices' rule for field `{field}` has too many options. Use `allowed_values` for larger sets.")
        if value not in choices:
            raise FieldValidationError(f"Field `{field}` with value {value} is not in the choices: {choices}")

    def _apply_range_rule(self, field: str, value: Union[int, float], range_: Tuple[Union[int, float], Union[int, float]]):
        if not isinstance(value, (int, float)) or not isinstance(range_, (tuple,list)) or len(range_) != 2:
            raise FieldValidationError(f"Invalid range rule for field `{field}`")
        if not (range_[0] <= value <= range_[1]):
            raise FieldValidationError(f"Field `{field}` with value {value} is not in the range {range_}")

    def _apply_pattern_rule(self, field: str, value: str, pattern: str):
        if not isinstance(value, str):
            raise FieldValidationError(f"Pattern rule not applicable for field `{field}` of type {type(value)}")
        if not re.match(pattern, value):
            raise FieldValidationError(f"Field `{field}` does not match the required pattern: {pattern}")

    def _apply_unique_rule(self, field: str, value: List[Any]):
        if not isinstance(value, list):
            raise FieldValidationError(f"Unique rule not applicable for field `{field}` of type {type(value)}")
        if len(value) != len(set(value)):
            raise FieldValidationError(f"Field `{field}` contains duplicate values")

    def _apply_contains_rule(self, field: str, value: Union[str, List[Any]], contained: Any):
        if isinstance(value, str):
            if contained not in value:
                raise FieldValidationError(f"Field `{field}` does not contain the required substring: {contained}")
        elif isinstance(value, list):
            if contained not in value:
                raise FieldValidationError(f"Field `{field}` does not contain the required element: {contained}")
        else:
            raise FieldValidationError(f"Contains rule not applicable for field `{field}` of type {type(value)}")

    def _parse_datetime(self, value: Union[str, int, float, datetime]) -> datetime:
        if isinstance(value, datetime):
            return value
        try:
            return arrow.get(value).datetime
        except arrow.ParserError:
            raise FieldValidationError(f"Invalid datetime format: {value}")

    def _parse_date(self, value: Union[str, int, float, date]) -> date:
        if isinstance(value, date):
            return value
        try:
            return arrow.get(value).date()
        except arrow.ParserError:
            raise FieldValidationError(f"Invalid date format: {value}")

    def _get_nested_value(self, config: Dict[str, Any], field: str) -> Any:
        keys = field.split('.')
        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
                value = resolve_value(value)  # 解析环境变量
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

    def _update_nested_dict(self, current: dict, update: dict):
        for k, v in update.items():
            if isinstance(v, dict) and k in current and isinstance(current[k], dict):
                self._update_nested_dict(current[k], v)
            else:
                current[k] = v

    def __getitem__(self, key: str) -> Any:
        value = self._get_nested_value(self._config, key)
        if value is None and not self._key_exists(self._config, key):
            raise FieldKeyError(key)
        return value

    def __getattr__(self, name: str) -> Any:
        try:
            value = self._get_nested_value(self._config, name)
            if value is None:
                # 如果值为None，我们需要检查这个键是否真的存在
                if not self._key_exists(self._config, name):
                    raise FieldKeyError(name)
            
            if isinstance(value, dict):
                return Config(value, strict=self._strict, verbose=self._verbose, logger=self._logger)
            
            return value
        except FieldKeyError:
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
    
    def __eq__(self, other):
        if not isinstance(other, Config):
            return False
        return self._config == other._config
    
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
                self._validate_field(field, value, self._schema[field].rules)
                self._set_nested_value(field, value)
            elif self._strict:
                raise FieldKeyError(f"Unknown configuration key: {field}")
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
        # Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        _, ext = os.path.splitext(file_path)
        with open(file_path, 'r') as f:
            if ext.lower() == '.json':
                return cls.from_json(f.read(), schema, strict, verbose, logger)
            elif ext.lower() in ['.yaml', '.yml']:
                return cls.from_yaml(f.read(), schema, strict, verbose, logger)
            else:
                raise FieldValidationError(f"Unsupported file format: {ext}")

    def to_yaml(self):
        return yaml.dump(self._config)
    
    def to_json(self, indent=4, ensure_ascii=False):
        return json.dumps(self._config, indent=indent, ensure_ascii=ensure_ascii)
    
    def to_file(self, file_path: str):
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        _, ext = os.path.splitext(file_path)
        with open(file_path, 'w') as f:
            if ext.lower() == '.json':
                f.write(self.to_json())
            elif ext.lower() in ['.yaml', '.yml']:
                f.write(self.to_yaml())
            else:
                raise FieldValidationError(f"Unsupported file format: {ext}")

    def _resolve_reference(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith('$'):
            referenced_field = value[1:].strip()
            # referenced_value = self._get_nested_value(self._config, referenced_field)
            referenced_value = nested_get_from_dict(referenced_field, self._config, unflatten=True)
            return referenced_value
        return value
    
    def __repr__(self):
        return f"Config({self._config})"


def make_config(config, schema, strict=False, logger=None, to_dict=False, to_dict_flatten=False, to_dict_sep='.'):
    config = Config(config, schema=schema, strict=strict, logger=logger)
    if to_dict:
        return config.to_dict(flatten=to_dict_flatten, sep=to_dict_sep)
    return config


__all__ = ['Config', 'make_config', 'Field', 'Schema']
