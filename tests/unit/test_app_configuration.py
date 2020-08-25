from flask import Flask
import os
import asobann
import pytest


PARAMS = [
    {
        'id': 'development',
        'FLASK_ENV': 'development',
        'env': {
        },
        'config': {
            'REDIS_URI': None,
            'MONGO_URI': 'mongodb://localhost:27017/ex2dev',
            'BASE_URL': 'http://localhost:5000',
        },
    },
    {
        'id': 'development with PUBLIC_HOSTNAME (dev on AWS)',
        'FLASK_ENV': 'development',
        'env': {
            'PUBLIC_HOSTNAME': 'asobann.example.com',
        },
        'config': {
            'BASE_URL': 'https://asobann.example.com',
        },
    },
    {
        'id': 'test',
        'FLASK_ENV': 'test',
        'env': {
        },
        'config': {
            'REDIS_URI': None,
            'MONGO_URI': 'mongodb://localhost:27017/ex2test',
            'BASE_URL': 'http://localhost:5000',
        },
        'testing': True,
    },
    {
        'id': 'production',
        'FLASK_ENV': 'production',
        'env': {
            'REDIS_URI': 'redis://example.com',
            'MONGODB_URI': 'mongodb://example.com/',
            'PUBLIC_HOSTNAME': 'asobann.example.com',
        },
        'config': {
            'REDIS_URI': 'redis://example.com',
            'MONGO_URI': 'mongodb://example.com/?retryWrites=false',
            'BASE_URL': 'https://asobann.example.com',
        },
    },
    {
        'id': 'production (preceding period in PUBLIC_HOSTNAME)',
        'FLASK_ENV': 'production',
        'env': {
            'REDIS_URI': 'redis://example.com',
            'MONGODB_URI': 'mongodb://example.com/',
            'PUBLIC_HOSTNAME': '.asobann.example.com',
        },
        'config': {
            'REDIS_URI': 'redis://example.com',
            'MONGO_URI': 'mongodb://example.com/?retryWrites=false',
            'BASE_URL': 'https://asobann.example.com',
        },
    },
]


@pytest.mark.parametrize('param', PARAMS, ids=[p['id'] for p in PARAMS])
def test_config(param):
    os.environ['FLASK_ENV'] = param['FLASK_ENV']
    for key, value in param['env'].items():
        os.environ[key] = value
    app = Flask(__name__)
    asobann.configure_app(app, testing=param.get('testing', False))
    for key, value in param['config'].items():
        assert app.config[key] == value
