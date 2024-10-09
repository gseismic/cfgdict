import re
import json
import yaml
import os
import arrow
from pathlib import Path
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union, Tuple
from loguru import logger as default_logger
from .utils import flatten_dict
from .schema import Field, Schema
from .exception import FieldValidationError, FieldKeyError
# from .utils import nested_update_dict
from .utils import make_dict, nested_get_from_dict, nested_set_dict


class Config:
    
    def __init__(self, 
                config_dict: Optional[Dict[str, Any]] = None, 
                schema: Optional[List[Dict[str, Any]]] = None, 
                strict: bool = False, 
                verbose: bool = False, 
                logger: Optional[Any] = None):
        self._logger = logger or default_logger
        self._schema = Schema.make_schema(schema)
        # 如果schema定义了默认数值，在config_dict中没有指定时，使用默认数值
        self._config = make_dict(config_dict, self._schema, logger=self._logger)
        self._strict = strict or False
        self._verbose = verbose or False
        self._validate_config(self._config, self._schema)
    
    def _validate_config(self, config, schema):
        # config包含了schema中所有字段
        if schema is None:
            return
        
        for key, value in config.items():
            field = schema.get(key)
            if field is None:
                continue
            if field.schema:
                self._validate_config(value, field.schema)
                continue
            
            self._validate_field(key, value, field.rules)

    def _validate_field(self, field: str, value: Any, rules: Dict[str, Any]):        
        if 'type' in rules:
            value = self._convert_type(field, value, rules['type'])

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

    def _convert_type(self, field: str, value: Any, expected_type: str) -> Any:
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
            raise FieldValidationError(f"{field}: Unsupported type: `{expected_type}`")
        try:
            return type_mapping[expected_type](value)
        except ValueError:
            raise FieldValidationError(f"{field}: Cannot convert value to `{expected_type}`: {value}")

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
        
    def _resolve_reference(self, value: Any) -> Any:
        if isinstance(value, str) and value.startswith('$'):
            referenced_field = value[1:].strip()
            # self._config is already `unflatten``
            referenced_value = nested_get_from_dict(referenced_field, self._config, unflatten=False)
            return referenced_value
        return value
    
    def __getitem__(self, key: str) -> Any:
        try:
            value = nested_get_from_dict(key, self._config, unflatten=False, raise_error=True)
            if isinstance(value, dict):
                return Config(value, schema=None, strict=self._strict, verbose=self._verbose, logger=self._logger)
            else:
                return value
        except KeyError:
            raise FieldKeyError(f'Key `{key}` not found in config')
    
    def get(self, key: str, default: Any = None) -> Any:
        return nested_get_from_dict(key, self._config, unflatten=False, default=default, raise_error=False)
    
    def __contains__(self, key: str) -> bool:
        try:
            self[key]
            return True
        except FieldKeyError:
            return False

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            return super().__getattr__(name)
        return self[name]
    
    def __setitem__(self, key: str, value: Any):
        self.update({key: value})
        
    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith('_'):
            super().__setattr__(name, value)    
        else:
            raise AttributeError('Not allowed, use `__setitem__` or `update()`')
        
    def update_key(self, key: str, value: Any, field=None):
        if field is None:
            if self._strict:
                raise FieldKeyError(f"Unknown configuration key: {key}")
            else:
                nested_set_dict(self._config, key, value, logger=self._logger)
                return
        else:
            # 需要先设置值，然后递归检查schema
            nested_set_dict(self._config, key, value, logger=self._logger)
            if field.schema:
                self._validate_config(value, field.schema)
            else:
                self._validate_field(key, value, field.rules)
            
    def update(self, *args, **kwargs):
        if args:
            if len(args) > 1:
                raise TypeError("update expected at most 1 arguments, got %d" % len(args))
            other = dict(args[0])
            kwargs.update(other)
            # nested_update_dict(kwargs, other, logger=self._logger)

        for name, value in kwargs.items():
            field = self._schema.get(name)
            self.update_key(name, value, field)
    
    def __eq__(self, other):
        if not isinstance(other, Config):
            return False
        return self._config == other._config
    
    def __repr__(self):
        return f"Config({self._config})"
    
    def __str__(self):
        return f"Config({self._config})"
    
    def to_dict(self, flatten=False, sep='.') -> Dict[str, Any]:
        if not flatten:
            return self._config
        else:
            return flatten_dict(self._config, sep=sep)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any], schema: List[Dict[str, Any]], strict: bool = None, verbose: bool = None, logger: Optional[Any] = None):
        return cls(config_dict, schema, strict, verbose, logger)

    @classmethod
    def from_json(cls, json_str: str, schema, strict: bool = None, verbose: bool = None, logger: Optional[Any] = None):
        config_dict = json.loads(json_str)
        if isinstance(schema, (str, Path)):
            schema = Schema.from_file(schema)
        elif schema is None:
            pass
        return cls(config_dict, schema, strict, verbose, logger)

    @classmethod
    def parse_schema(cls, schema: List[Dict[str, Any]]):
        if schema is None:
            schema_file = cls._make_schema_path(file_path)
            if os.path.exists(schema_file):
                schema = Schema.from_file(schema_file)
            else:
                schema = None
        else:
            if isinstance(schema, (str, Path)):
                schema = Schema.from_file(schema)
        return schema
    
    @classmethod
    def from_yaml(cls, yaml_str: str, schema: List[Dict[str, Any]], strict: bool = True, verbose: bool = False, logger: Optional[Any] = None):
        schema = cls.parse_schema(schema)
        config_dict = yaml.safe_load(yaml_str)
        return cls(config_dict, schema, strict, verbose, logger)
    
    @classmethod
    def from_file(cls, file_path: str, schema, strict: bool = True, verbose: bool = False, logger: Optional[Any] = None):
        schema = cls.parse_schema(schema)
        _, ext = os.path.splitext(file_path)
        with open(file_path, 'r') as f:
            if ext.lower() == '.json':
                return cls.from_json(f.read(), schema, strict, verbose, logger)
            elif ext.lower() in ['.yaml', '.yml']:
                return cls.from_yaml(f.read(), schema, strict, verbose, logger)
            else:
                raise FieldValidationError(f"Unsupported file format: {ext}")
    
    def to_dict(self):
        return self._config

    def to_json(self, indent=4, ensure_ascii=False):
        return json.dumps(self._config, indent=indent, ensure_ascii=ensure_ascii)

    def to_yaml(self):
        return yaml.dump(self._config)
    
    @classmethod
    def _make_schema_path(cls, file_path):
        paths = file_path.split('.')
        paths.insert(-1, 'schema')
        schema_file = '.'.join(paths)
        return schema_file

    def to_file(self, file_path):
        # ensure dir exists
        schema_file = self._make_schema_path(file_path)
        self._schema.to_file(schema_file)
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        _, ext = os.path.splitext(file_path)
        with open(file_path, 'w') as f:
            if ext.lower() == '.json':
                f.write(self.to_json())
            elif ext.lower() in ['.yaml', '.yml']:
                f.write(self.to_yaml())
            else:
                raise FieldValidationError(f"Unsupported file format: {ext}")   


def make_config(config, schema, strict=False, logger=None, to_dict=False, to_dict_flatten=False, to_dict_sep='.'):
    config = Config(config, schema=schema, strict=strict, logger=logger)
    if to_dict:
        return config.to_dict(flatten=to_dict_flatten, sep=to_dict_sep)
    return config

__all__ = ['Config', 'make_config', 'Field', 'Schema']
