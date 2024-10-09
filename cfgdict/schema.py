from collections import OrderedDict
from copy import deepcopy
import json
from .exception import SchemaError

class Field:
    def __init__(self, field, required=False, default=None, schema=None, **rules):
        if schema is not None and rules:
            raise SchemaError(f"Cannot specify both schema and rules, with schema={schema} and rules={rules}")
        self.field = field
        self.required = required
        self.default = default
        if schema is not None:
            self.schema = Schema.make_schema(schema)
        else:
            self.schema = None
        self.rules = rules
    
    def to_dict(self):
        return {
            'field': self.field,
            'required': self.required,
            'default': self.default,
            'schema': self.schema.to_dict() if self.schema else None,
            'rules': self.rules
        }

    def __repr__(self):
        return f"Field(field={self.field}, required={self.required}, default={self.default}, schema={self.schema}, rules={self.rules})"

class Schema:
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
                name = _field.pop('field', None)
            if name is None:
                raise SchemaError("Field name is required")
            required = _field.pop('required', False)
            default = _field.pop('default', None)
            rules = _field.pop('rules', {})
            schema = _field.pop('schema', None)
            rules.update(_field)
            self._fields[name] = Field(name, required, default, schema=schema, **rules)
        elif isinstance(field, Field):
            self._fields[field.field] = field
        else:
            raise SchemaError(f"Invalid field type: {field}")

    @classmethod
    def from_dict(cls, d):
        return cls(**d)
    
    @classmethod
    def from_list(cls, l):
        return cls(*l)
    
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
    
    def __len__(self):
        return len(self._fields)
    
    def __contains__(self, key):
        return key in self._fields
    
    def __str__(self):
        return repr(self)
    
    def __repr__(self):
        return f"Schema({dict(self._fields)})"
    
    def to_dict(self):
        return {field.field: field.to_dict() for field in self._fields.values()}
    
    def __deepcopy__(self, memo):
        new_schema = Schema()
        for field in self._fields.values():
            new_schema._fields[field.field] = deepcopy(field, memo)
        return new_schema
    
    def __getstate__(self):
        return self._fields
    
    def __setstate__(self, state):
        self._fields = OrderedDict()
        for name, field in state.items():
            self._fields[name] = field
