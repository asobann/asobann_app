import os

import asobann
import asobann.app
import pytest
from flask import Flask

pytestmark = [pytest.mark.quick]

PARAMS = [
    {
        'id': 'development',
        'input': {
            'FLASK_ENV': 'development',
            'env': {
            },
        },
        'expected': {
            'config': {
                'REDIS_URI': None,
                'MONGO_URI': 'mongodb://localhost:27017/ex2dev',
                'BASE_URL': 'http://localhost:5000',
                'GOOGLE_ANALYTICS_ID': None,
            },
        },
    },
    {
        'id': 'development with PUBLIC_HOSTNAME (dev on AWS)',
        'input': {
            'FLASK_ENV': 'development',
            'env': {
                'PUBLIC_HOSTNAME': 'asobann.example.com',
            },
        },
        'expected': {
            'config': {
                'BASE_URL': 'https://asobann.example.com',
            },
        },
    },
    {
        'id': 'development (Google Analytics is disabled)',
        'input': {
            'FLASK_ENV': 'development',
            'env': {
                'GOOGLE_ANALYTICS_ID': 'UA-DUMMYID',
            },
        },
        'expected': {
            'config': {
                'GOOGLE_ANALYTICS_ID': None,
            },
        },
    },
    {
        'id': 'test',
        'input': {
            'FLASK_ENV': 'test',
            'env': {
            },
            'testing': True,
        },
        'expected': {
            'config': {
                'REDIS_URI': None,
                'MONGO_URI': 'mongodb://admin:password@mongo:27017/test?authSource=admin',
                'BASE_URL': '*',
                'GOOGLE_ANALYTICS_ID': None,
            },
        },
    },
    {
        'id': 'production',
        'input': {
            'FLASK_ENV': 'production',
            'env': {
                'REDIS_URI': 'redis://example.com',
                'MONGODB_URI': 'mongodb://example.com/',
                'PUBLIC_HOSTNAME': 'asobann.example.com',
                'GOOGLE_ANALYTICS_ID': 'UA-DUMMYID',
            },
        },
        'expected': {
            'config': {
                'REDIS_URI': 'redis://example.com',
                'MONGO_URI': 'mongodb://example.com/?retryWrites=false',
                'BASE_URL': 'https://asobann.example.com',
                'GOOGLE_ANALYTICS_ID': 'UA-DUMMYID',
            },
        },
    },
    {
        'id': 'production (preceding period in PUBLIC_HOSTNAME)',
        'input': {
            'FLASK_ENV': 'production',
            'env': {
                'REDIS_URI': 'redis://example.com',
                'MONGODB_URI': 'mongodb://example.com/',
                'PUBLIC_HOSTNAME': '.asobann.example.com',
                'GOOGLE_ANALYTICS_ID': 'UA-DUMMYID',
            },
        },
        'expected': {
            'config': {
                'BASE_URL': 'https://asobann.example.com',
            },
        },
    },
]


@pytest.mark.parametrize('param', PARAMS, ids=[p['id'] for p in PARAMS])
def test_config(param):
    input_ = param['input']
    expected = param['expected']
    os.environ['FLASK_ENV'] = input_['FLASK_ENV']
    try:
        for key, value in input_['env'].items():
            os.environ[key] = value
        app = Flask(__name__)
        import importlib
        importlib.reload(asobann.config_common)  # must be reloaded with new environment
        asobann.app.configure_app(app, testing=input_.get('testing', False))
        for key, value in expected['config'].items():
            assert app.config[key] == value
    finally:
        for key, value in input_['env'].items():
            del os.environ[key]
