from collections import OrderedDict
from copy import deepcopy
import json
from .exception import SchemaError
from .field import Field
import yaml
import os
from pathlib import Path
class Schema:
    """
    example #1:
        schema = Schema(
            Field('name', required=True, type='str'),
            Field('age', required=True, type='int', min=0, max=100),
            Field('email', required=True, type='str', format='email'),
            Field('is_student', required=True, type='bool'),
            Field('courses', required=True, schema=Schema(
                Field('name', required=True, type='str'),
                Field('grade', required=True, type='int', min=0, max=100)
            ))
        )
    
    example #2:
        schema = Schema(
            name=Field(required=True, type='str'),
            age=Field(required=True, type='int', min=0, max=100),
            email=Field(required=True, type='str', format='email'),
            is_student=Field(required=True, type='bool'),
            courses=Field(required=True, schema=Schema(
                Field('name', required=True, type='str'),
                Field('grade', required=True, type='int', min=0, max=100)
            ))
        )
    """
    def __init__(self, *args, **kwargs):
        self._fields = OrderedDict()
        self._add_fields_from_list(args)
        self._add_fields_from_dict(kwargs)

    def _add_fields_from_dict(self, d):
        for name, value in d.items():
            self._add_field(value, name=name)

    def _add_fields_from_list(self, l):
        for field in l:
            self._add_field(field)

    def _add_field(self, field, name=None):
        if isinstance(field, dict):
            _field = deepcopy(field)
            if name is None:
                name = _field.pop('name', None) or _field.pop('field', None)
            if name is None:
                raise SchemaError("Field name is required")
            required = _field.pop('required', False)
            default = _field.pop('default', None)
            rules = _field.pop('rules', {})
            schema = _field.pop('schema', None)
            rules.update(_field)
            
            self._fields[name] = Field(name, required, default, schema=schema, **rules)
        elif isinstance(field, Field):
            if name is None:
                name = field.field
            else:
                field.name = name
            self._fields[name] = field
        else:
            raise SchemaError(f"Invalid field type: {field}")

    @classmethod
    def from_dict(cls, d):
        return cls(**d)
    
    @classmethod
    def from_list(cls, l):
        return cls(*l)
    
    @classmethod
    def from_json(cls, json_str):
        return cls(**json.loads(json_str))
    
    @classmethod
    def from_yaml(cls, yaml_str):
        return cls(**yaml.safe_load(yaml_str))
    
    @classmethod
    def from_file(cls, file_path):
        _, ext = os.path.splitext(file_path)
        with open(file_path, 'r') as f:
            if ext.lower() == '.json':
                return cls.from_json(f.read())
            elif ext.lower() in ['.yaml', '.yml']:
                return cls.from_yaml(f.read())
            else:
                raise SchemaError(f"Unsupported file format: {ext}")
    
    def to_dict(self):
        return {field.name: field.to_dict() for field in self._fields.values()}
    
    def to_json(self, indent=4, ensure_ascii=False):
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=ensure_ascii)
    
    def to_yaml(self):
        return yaml.dump(self.to_dict())
    
    def to_file(self, file_path):
        Path(file_path).parent.mkdir(parents=True, exist_ok=True)
        _, ext = os.path.splitext(file_path)
        with open(file_path, 'w') as f:
            if ext.lower() == '.json':
                f.write(self.to_json())
            elif ext.lower() in ['.yaml', '.yml']:
                f.write(self.to_yaml())
            else:
                raise SchemaError(f"Unsupported file format: {ext}")
    
    @classmethod
    def make_schema(cls, schema):
        if isinstance(schema, Schema):
            return schema
        elif isinstance(schema, list):
            return cls(*schema)
        elif isinstance(schema, dict):
            return cls(**schema)
        elif schema is None:
            return cls()
        else:
            raise SchemaError(f"Invalid schema type: {schema}")
    
    @classmethod
    def from_json(cls, json_str):
        return cls(**json.loads(json_str))
    
    def __setitem__(self, key, value):
        self._add_field(value, name=key)
    
    def __setattr__(self, key, value):
        if key in ['_fields', 'from_dict', 'from_list', 'from_json']:
            super().__setattr__(key, value)
        else:
            self._add_field(value, name=key)
    
    def __getitem__(self, key):
        return self._fields[key]
    
    def __getattr__(self, key):
        if key in self._fields:
            return self._fields[key]
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{key}'")
    
    def __iter__(self):
        return iter(self._fields)
    
    def items(self):
        return self._fields.items()
    
    def keys(self):
        return self._fields.keys()
    
    def values(self):
        return self._fields.values()
    
    def get(self, key, default=None):
        return self._fields.get(key, default)
    
    def __len__(self):
        return len(self._fields)
    
    def __contains__(self, key):
        return key in self._fields
    
    def __str__(self):
        return repr(self)
    
    def __repr__(self):
        return f"Schema({dict(self._fields)})"
    
    def to_dict(self):
        return {field.name: field.to_dict() for field in self._fields.values()}
    
    def __deepcopy__(self, memo):
        new_schema = Schema()
        for field in self._fields.values():
            new_schema._fields[field.name] = deepcopy(field, memo)
        return new_schema
