from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, jsonify, json, make_response, send_file
from flask_pymongo import PyMongo
import logging
from logging.config import dictConfig
import boto3

from werkzeug.datastructures import FileStorage

import asobann
from asobann.store import tables, components, kits

from .. import socketio

# prevent 'Too many packets in paylod' error
# see https://github.com/miguelgrinberg/python-engineio/issues/142
from engineio.payload import Payload

Payload.max_decode_packets = 1000

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        # 'format': '[%(asctime)s] %(levelname)s in %(name)s at %(pathname)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
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
    )

    folder = Path(asobann.__file__).parent.absolute()
    if app.config["ENV"] == "test" or testing:
        app.config.from_pyfile(folder / 'config_test.py', silent=True)
    elif app.config["ENV"] == "production":
        app.config.from_pyfile(folder / 'config_production.py', silent=True)
    else:
        app.config.from_pyfile(folder / 'config_dev.py', silent=True)


class LocalImageUploader:
    def upload(self, file):
        file_name = file.filename
        from pathlib import Path
        image_base_path = Path('/tmp/asobann/images')
        image_base_path.mkdir(exist_ok=True, parents=True)
        file.save(image_base_path / file_name)
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

    def upload(self, file):
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


def create_app(testing=False):
    app = Flask(__name__)
    configure_app(app, testing=testing)

    from flask.logging import default_handler
    app.logger.removeHandler(default_handler)

    socketio_args = {}

    if 'DEBUG_LOG' in app.config and app.config['DEBUG_LOG']:
        socketio_args['logger'] = app.logger
        socketio_args['engineio_logger'] = app.logger
        app.logger.setLevel('DEBUG')

    try:
        app.logger.info("connecting mongo")
        app.mongo = PyMongo(app)
        # make sure mongodb is available and fail fast if not
        app.mongo.db.list_collection_names()
        app.logger.info("connected to mongo")
    except Exception as e:
        app.logger.error('failed to connect to mongo')
        app.logger.error(f'connection string: {app.config["MONGO_URI"]}')
        raise

    if app.config['REDIS_URI']:
        uri = app.config["REDIS_URI"]
        app.logger.info(f'use redis at {uri}')
        if uri.startswith('redis+srv://'):
            uri = resolve_redis_srv(uri)
            app.logger.info(f'actual uri {uri}')
        socketio_args['message_queue'] = uri
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
        socketio_args['cors_allowed_origins'] = "*"
    else:
        socketio_args['cors_allowed_origins'] = app.config['BASE_URL']
    socketio.init_app(app, **socketio_args)
    app.socketio = socketio

    tables.connect(app.mongo)
    components.connect(app.mongo)
    kits.connect(app.mongo)

    from asobann.app.blueprints import table, kit, component
    app.register_blueprint(table.blueprint)
    app.register_blueprint(component.blueprint)
    app.register_blueprint(kit.blueprint)
    if app.config['ENV'] == 'development' or app.config['ENV'] == 'test':
        from asobann.app.blueprints import debug
        app.register_blueprint(debug.blueprint)

    @app.route('/')
    def index():
        tablename = tables.generate_new_tablename()
        response = make_response(redirect(url_for('tables.play_table', tablename=tablename)))
        return response

    # @app.route('/join_session', methods=["POST"])
    # def join_session():
    #     tablename = request.form.get("tablename")
    #     if not tablename:
    #         tablename = str(random.randint(0, 9999)) + ''.join([random.choice('abddefghijklmnopqrstuvwxyz') for i in range(3)])
    #     player = request.form.get("player")
    #     response = make_response(redirect(url_for('.play_session', tablename=tablename)))
    #     return response

    @app.route('/export', methods=["GET"])
    def export_table():
        tablename = request.args.get("tablename")
        app.logger.info(f"exporting table <{tablename}>")
        table = tables.get(tablename)
        return jsonify(table)

    @app.route('/import', methods=["POST"])
    def import_table():
        tablename = tables.generate_new_tablename()
        app.logger.info(f"importing table <{tablename}>")
        if 'data' not in request.files:
            return redirect(url_for('/'))
        file = request.files['data']
        table = json.loads(file.read())
        tables.store(tablename, table)
        return redirect(url_for('tables.play_table', tablename=tablename))

    @app.route('/customize')
    def customize():
        return render_template('customize.html')

    @app.route('/dummy', methods=['POST'])
    def upload_image():
        if 'image' not in request.files:
            return redirect(url_for('/'))
        file: FileStorage = request.files['image']
        url = app.image_store.upload(file)
        return jsonify({
            'imageUrl': url,
        })

    @app.route('/images/uploaded/<file_name>', methods=['GET'])
    def get_uploaded_image(file_name):
        from pathlib import Path
        image_base_path = Path('/tmp/asobann/images')
        return send_file(image_base_path / file_name)

    @app.route('/config', methods=['GET'])
    def get_config():
        client_config = {}
        if 'AWS_COGNITO_USER_POOL_ID' in app.config:
            client_config['AWS_COGNITO'] = {
                'UserPoolId': app.config['AWS_COGNITO_USER_POOL_ID'],
                'ClientId': app.config['AWS_COGNITO_CLIENT_ID'],
            }
        return jsonify(client_config)

    return app
