from cfgdict import Config

nested_schema = [
    dict(field='database.host', required=True, rules=dict(type='str')),
    dict(field='database.port', required=True, rules=dict(type='int', min=1, max=65535)),
    dict(field='api.version', required=True, rules=dict(type='str')),
    dict(field='api.endpoints.users', required=True, rules=dict(type='str')),
    dict(field='api.endpoints.products', required=True, rules=dict(type='str')),
]

nested_config = Config.from_dict({
    'database': {
        'host': 'localhost',
        'port': 5432
    },
    'api': {
        'version': 'v1',
        'endpoints': {
            'users': '/api/v1/users',
            'products': '/api/v1/products'
        }
    }
}, schema=nested_schema)

print(nested_config.to_dict())