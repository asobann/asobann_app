import pytest

from asobann.app import redact_credentials

pytestmark = [pytest.mark.quick]

PARAMS = [
    {
        'id': 'atlas (mongodb+srv with query string)',
        'uri': 'mongodb+srv://user:secret@cluster.abc.mongodb.net/asobann_dev?appName=x&retryWrites=false',
        'expected': 'mongodb+srv://cluster.abc.mongodb.net/asobann_dev',
    },
    {
        'id': 'with host and port',
        'uri': 'mongodb://admin:secret@mongo:27017/asobann_dev?authSource=admin',
        'expected': 'mongodb://mongo:27017/asobann_dev',
    },
    {
        'id': 'no credentials',
        'uri': 'mongodb://localhost:27017/ex2dev',
        'expected': 'mongodb://localhost:27017/ex2dev',
    },
    {
        'id': 'percent-encoded password',
        'uri': 'mongodb+srv://user:p%40ss%2Fword@cluster.abc.mongodb.net/asobann_dev',
        'expected': 'mongodb+srv://cluster.abc.mongodb.net/asobann_dev',
    },
]


@pytest.mark.parametrize('param', PARAMS, ids=[p['id'] for p in PARAMS])
def test_credentials_are_removed(param):
    redacted = redact_credentials(param['uri'])
    assert redacted == param['expected']
    assert 'secret' not in redacted
    assert 'user' not in redacted
