import warnings
from .exception import SchemaError

class Field:
    def __init__(self, name=None, required=False, default=None, schema=None, field=None, **rules):
        if schema:
            if rules:
                raise SchemaError(f"Cannot specify both schema and rules, with schema={schema} and rules={rules}")
            # 当schema指定时，default不能指定
            if default is not None:
                raise SchemaError(f"Cannot specify both default and schema, with default={default} and schema={schema}")
        else:
            # schema is None时，required和default不能同时指定
            if required and default is not None:
                raise SchemaError(f"Cannot specify both required and default, with required={required} and default={default}")

        if field is not None:
            warnings.warn("field is deprecated, please use name instead")
        self.name = name or field
        self.required = required
        self.default = default
        if schema is not None:
            from .schema import Schema
            self.schema = Schema.make_schema(schema)
        else:
            self.schema = None
        self.rules = rules
    
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
            if self.default is not None:
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
