# from gevent import monkey
# monkey.patch_all()
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, jsonify, json, make_response, abort
from flask_socketio import SocketIO, emit, join_room
from flask_pymongo import PyMongo
from logging.config import dictConfig

from asobann.store import tables, components, kits

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'DEBUG',
        'handlers': ['wsgi']
    }
})


socketio = SocketIO()


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
    results = resolver.resolve('_redis._tcp.' + host, 'SRV')
    node_host = results[0].target.to_text(omit_final_dot=True)
    node_port = results[0].port
    node_uri = f'redis://{auth or ""}{node_host}:{node_port}{path_and_rest or ""}'
    return node_uri


def create_app(testing=False):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='secret!',
    )

    if app.config["ENV"] == "test" or testing:
        app.config.from_pyfile('config_test.py', silent=True)
    elif app.config["ENV"] == "production":
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_pyfile('config_dev.py', silent=True)

    app.logger.info("connecting mongo")
    app.mongo = PyMongo(app)
    # make sure mongodb is available and fail fast if not
    app.mongo.db.list_collection_names()
    app.logger.info("connected to mongo")
    if app.config['REDIS_URI']:
        uri = app.config["REDIS_URI"]
        app.logger.info(f'use redis at {uri}')
        if uri.startswith('redis+srv://'):
            uri = resolve_redis_srv(uri)
            app.logger.info(f'actual uri {uri}')
        socketio.init_app(app, message_queue=uri)
    else:
        app.logger.info('use no message queue')
        socketio.init_app(app)
    app.socketio = socketio

    tables.connect(app.mongo)
    components.connect(app.mongo)
    kits.connect(app.mongo)

    from . import table
    app.register_blueprint(table.blueprint)

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

    @app.route('/components')
    def get_components_for_kit():
        kit_name = request.args.get("kit_name")
        if not kit_name:
            return abort(500)
        return jsonify(components.get_for_kit(kit_name))

    @app.route('/kits')
    def get_kits():
        return jsonify(kits.get_all())

    return app

