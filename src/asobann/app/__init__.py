import asyncio
import os
from pathlib import Path
from urllib.parse import urlsplit

import boto3
import socketio
from pymongo import AsyncMongoClient
from quart import Quart, render_template, request, redirect, url_for, jsonify, json, make_response, send_file
from werkzeug.datastructures import FileStorage

import asobann
from asobann.store import tables, components, kits
from . import debug_tools

# prevent 'Too many packets in payload' error
# see https://github.com/miguelgrinberg/python-engineio/issues/142
from engineio.payload import Payload

import logging
from logging.config import dictConfig

Payload.max_decode_packets = 1000

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://sys.stderr',
        'formatter': 'default'
    }},
    'loggers': {
        'asobann.app': {
            'level': 'INFO',
            'handlers': ['wsgi'],
            'propagate': False,
        },
        'socketio': {
            'level': 'WARNING',
            'handlers': ['wsgi'],
            'propagate': False,
        },
        'engineio': {
            'level': 'WARNING',
            'handlers': ['wsgi'],
            'propagate': False,
        },
        'selenium': {
            'level': 'ERROR',
            'handlers': ['wsgi'],
            'propagate': False,
        },
    },
    'root': {
        'level': 'ERROR',
        'handlers': ['wsgi']
    },
})


def resolve_redis_srv(uri: str):
    '''
    Resolve redis+srv:// and return regular redis:// uri.
    Redis itself does not support connecting with SRV record but current AWS ECS
    configuration requires to use SRV record.
    Does not support TXT record.

    :param uri: connection uri starts with redis+srv://
    :return: redis://host:port/ uri resolved with SRV record
    '''
    assert uri.startswith('redis+srv://')
    import re
    from dns import resolver
    auth, host, path_and_rest = re.match(r'redis\+srv://([^@]*@)?([^/?]*)([/?].*)?', uri).groups()
    results = resolver.query('_redis._tcp.' + host, 'SRV')
    node_host = results[0].target.to_text(omit_final_dot=True)
    node_port = results[0].port
    node_uri = f'redis://{auth or ""}{node_host}:{node_port}{path_and_rest or ""}'
    return node_uri


def configure_app(app, testing):
    app.config.from_mapping(
        SECRET_KEY='secret!',
        # Quartのconfigは(Flaskと違い)ENVを自動で持たない。FLASK_ENVは既存の
        # デプロイ/テスト構成(docker-compose、conftest.py等)が使っている名前なので、
        # そのまま踏襲する。
        ENV=os.environ.get('FLASK_ENV', 'production'),
    )

    folder = Path(asobann.__file__).parent.absolute()
    if app.config["ENV"] == "test" or testing:
        app.config.from_pyfile(folder / 'config_test.py', silent=True)
    elif app.config["ENV"] == "production":
        app.config.from_pyfile(folder / 'config_production.py', silent=True)
    else:
        app.config.from_pyfile(folder / 'config_dev.py', silent=True)


class LocalImageUploader:
    async def upload(self, file: FileStorage):
        file_name = file.filename
        from pathlib import Path
        image_base_path = Path('/tmp/asobann/images')
        image_base_path.mkdir(exist_ok=True, parents=True)
        await file.save(image_base_path / file_name)
        return url_for('get_uploaded_image', file_name=file_name, _external=False)


class S3ImageUploader:
    def __init__(self, aws_key, aws_secret, aws_region, bucket_name):
        self.session = boto3.session.Session(
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name=aws_region)
        self.s3 = self.session.resource('s3')
        self.bucket = self.s3.Bucket(bucket_name)
        self.aws_region = aws_region
        self.bucket_name = bucket_name

    def _upload_sync(self, file):
        filename = file.filename
        newname = 'upload/' + filename
        newobj = self.bucket.Object(newname)
        content_type = 'application/octet-stream'
        if filename.lower().endswith('.png'):
            content_type = 'image/png'
        elif filename.lower().endswith('.jpeg') or filename.lower().endswith('.jpg'):
            content_type = 'image/jpeg'
        elif filename.lower().endswith('.gif'):
            content_type = 'image/gif'
        elif filename.lower().endswith('.svg'):
            content_type = 'image/svg'
        newobj.upload_fileobj(file, ExtraArgs={"ContentType": content_type})
        newacl = newobj.Acl()
        newacl.put(ACL='public-read')

        return F'https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{newname}'

    async def upload(self, file):
        # boto3はブロッキングI/O。イベントループを止めないようスレッドに逃がす。
        return await asyncio.to_thread(self._upload_sync, file)


def redact_credentials(uri: str) -> str:
    """接続文字列から認証情報を落とす。

    ログはCloudWatchに残るため、パスワードをそのまま出すとSSMのSecureStringで
    隠している意味がなくなる。接続先の確認に必要なスキーム・ホスト・DB名だけを返す。
    文字列置換ではなくurlsplitで組み立て直すので、構造上パスワードは含まれない。
    """
    parts = urlsplit(uri)
    host = parts.hostname or ''
    if parts.port:
        host = f'{host}:{parts.port}'
    return f'{parts.scheme}://{host}{parts.path}'


async def create_app(testing=False):
    app = Quart(__name__)
    configure_app(app, testing=testing)

    from quart.logging import default_handler
    app.logger.removeHandler(default_handler)

    sio_kwargs = {'async_mode': 'asgi'}

    if 'DEBUG_LOG' in app.config and app.config['DEBUG_LOG']:
        sio_kwargs['logger'] = app.logger
        sio_kwargs['engineio_logger'] = app.logger
        app.logger.setLevel('DEBUG')

    try:
        app.logger.info("connecting mongo")
        app.logger.info(redact_credentials(app.config["MONGO_URI"]))
        app.mongo_client = AsyncMongoClient(app.config["MONGO_URI"])
        app.mongo_db = app.mongo_client.get_default_database()
        # make sure mongodb is available and fail fast if not
        await app.mongo_db.list_collection_names()
        app.logger.info("connected to mongo")
    except Exception as e:
        app.logger.error('failed to connect to mongo')
        app.logger.error(f'connection string: {redact_credentials(app.config["MONGO_URI"])}')
        raise

    if app.config['REDIS_URI']:
        uri = app.config["REDIS_URI"]
        app.logger.info(f'use redis at {uri}')
        if uri.startswith('redis+srv://'):
            uri = resolve_redis_srv(uri)
            app.logger.info(f'actual uri {uri}')
        sio_kwargs['client_manager'] = socketio.AsyncRedisManager(uri)
    else:
        app.logger.info('use no message queue')

    if app.config['UPLOADED_IMAGE_STORE'].lower() == 'local':
        app.image_store = LocalImageUploader()
    elif app.config['UPLOADED_IMAGE_STORE'].lower() == 's3':
        app.image_store = S3ImageUploader(
            aws_key=app.config['AWS_KEY'],
            aws_secret=app.config['AWS_SECRET'],
            aws_region=app.config['AWS_REGION'],
            bucket_name=app.config['AWS_S3_IMAGE_BUCKET_NAME'],
        )
    else:
        raise ValueError(f'config UPLOADED_IMAGE_STORE "{app.config["UPLOADED_IMAGE_STORE"].lower()}" is invalid')

    if app.config["ENV"] == "development":
        sio_kwargs['cors_allowed_origins'] = "*"
    else:
        # CORS_ALLOWED_ORIGINS_OVERRIDE lets a local profiling harness run the
        # production config against a plain-http local origin, which never matches
        # BASE_URL's hardcoded https://. Unset in every real deployment, so production
        # behavior is unchanged - but this is an escape hatch in a production code path,
        # and deploy/loadtest/docker-compose.yml sets it. See issue #132.
        sio_kwargs['cors_allowed_origins'] = os.environ.get(
            'CORS_ALLOWED_ORIGINS_OVERRIDE', app.config['BASE_URL'])

    sio = socketio.AsyncServer(**sio_kwargs)
    app.sio = sio

    tables.connect(app.mongo_db)
    components.connect(app.mongo_db)
    kits.connect(app.mongo_db)
    await tables.ensure_indexes()
    debug_tools.configure(
        app.mongo_db,
        performance_recording=app.config.get('DEBUG_PERFORMANCE_RECORDING', False),
    )

    from asobann.app.blueprints import table, kit, component
    table.register_handlers(sio, app)
    app.register_blueprint(table.blueprint)
    app.register_blueprint(component.blueprint)
    app.register_blueprint(kit.blueprint)
    if app.config['ENV'] == 'development' or app.config['ENV'] == 'test':
        from asobann.app.blueprints import debug
        app.register_blueprint(debug.blueprint)

    @app.route('/')
    async def index():
        tablename = tables.generate_new_tablename()
        response = make_response(redirect(url_for('tables.play_table', tablename=tablename)))
        return await response

    @app.route('/export', methods=["GET"])
    async def export_table():
        tablename = request.args.get("tablename")
        app.logger.info(f"exporting table <{tablename}>")
        table = await tables.get(tablename)
        return jsonify(table)

    @app.route('/import', methods=["POST"])
    async def import_table():
        tablename = tables.generate_new_tablename()
        app.logger.info(f"importing table <{tablename}>")
        files = await request.files
        if 'data' not in files:
            return redirect(url_for('/'))
        file = files['data']
        table = json.loads(file.read())
        await tables.store(tablename, table)
        return redirect(url_for('tables.play_table', tablename=tablename))

    @app.route('/customize')
    async def customize():
        return await render_template('customize.html')

    @app.route('/dummy', methods=['POST'])
    async def upload_image():
        files = await request.files
        if 'image' not in files:
            return redirect(url_for('/'))
        file: FileStorage = files['image']
        url = await app.image_store.upload(file)
        return jsonify({
            'imageUrl': url,
        })

    @app.route('/images/uploaded/<file_name>', methods=['GET'])
    async def get_uploaded_image(file_name):
        from pathlib import Path
        image_base_path = Path('/tmp/asobann/images')
        return await send_file(image_base_path / file_name)

    @app.route('/config', methods=['GET'])
    async def get_config():
        client_config = {}
        if 'AWS_COGNITO_USER_POOL_ID' in app.config:
            client_config['AWS_COGNITO'] = {
                'UserPoolId': app.config['AWS_COGNITO_USER_POOL_ID'],
                'ClientId': app.config['AWS_COGNITO_CLIENT_ID'],
            }
        return jsonify(client_config)

    return app
