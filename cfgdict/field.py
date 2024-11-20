import warnings
from enum import IntEnum
from .exception import SchemaError
from .utils import nested_update_dict
from .logger import default_logger
from .utils import HasDefault, default_exists

class Field:
    # XXX: default 无法区分默认值为None和没有默认值
    def __init__(self, name=None, required=False, default=HasDefault.NO_DEFAULT,
                 schema=None, field=None, rules=None, logger=None, **kwargs):
        self.name = name or field
        if field is not None:
            warnings.warn("\033[33mfield is deprecated, please use name instead\033[0m")
        if schema:
            if rules:
                raise SchemaError(f"Cannot specify both schema and rules, with schema={schema} and rules={rules}")
            # 当schema指定时，default不能指定
            if default != HasDefault.NO_DEFAULT:
                raise SchemaError(f"Cannot specify both default and schema, with default={default} and schema={schema}")
        else:
            # schema is None时，required和default不能同时指定
            if required and default == HasDefault.HAS_DEFAULT:
                raise SchemaError(f"`{self.name}`: Cannot specify both required and default, with required={required} and default={default}")
        self.logger = logger or default_logger
        self.required = required
        self.default = default
        if schema is not None:
            from .schema import Schema
            self.schema = Schema.make_schema(schema)
        else:
            self.schema = None
        
        # nested_update_dict
        rules = rules or {}
        rules = nested_update_dict(rules, kwargs, logger=self.logger, path=self.name)
        self.rules = rules
    
    def default_exists(self):
        return not default_exists(self)
    
    def update_rules(self, rules):
        self.rules.update(rules)
    
    @property
    def field(self):
        return self.name
    
    def to_dict(self, simplify=True):
        if simplify:
            out = {}
            if self.name is not None:
                out['name'] = self.name
            if self.required is not None:
                out['required'] = self.required
            if self.default == HasDefault.HAS_DEFAULT:
                out['default'] = self.default
            if self.schema is not None:
                out['schema'] = self.schema.to_dict()
            if self.rules is not None:
                out['rules'] = self.rules
        else:
            out = {
                'name': self.name,
                'required': self.required,
                'default': self.default,
                'schema': self.schema.to_dict() if self.schema else None,
                'rules': self.rules
            }
        return out
    
    def __repr__(self):
        return f"Field(name={self.name}, required={self.required}, default={self.default}, schema={self.schema}, rules={self.rules})"

    def __getstate__(self):
        state = {**self.__dict__}
        del state['logger']
        return state
    
    def __setstate__(self, state):
        self.__dict__.update(state)
