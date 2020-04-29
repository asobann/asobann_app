from flask import Flask, render_template, request, redirect, url_for, jsonify, json, make_response
from flask_socketio import SocketIO, emit, join_room
from flask_pymongo import PyMongo
from logging.config import dictConfig
import random
import string

from asobann import tables


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
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY='secret!',
        MONGO_URI='mongodb://localhost:27017/ex2dev',
    )

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.config.from_mapping(test_config)

    app.logger.info("connecting mongo")
    app.mongo = PyMongo(app)
    app.socketio = SocketIO(app)
    app.logger.info("connected to mongo")

    tables.connect(app.mongo)

    @app.route('/')
    def index():
        tablename = tables.generate_new_tablename()
        response = make_response(redirect(url_for('.play_table', tablename=tablename)))
        return response

    # @app.route('/join_session', methods=["POST"])
    # def join_session():
    #     tablename = request.form.get("tablename")
    #     if not tablename:
    #         tablename = str(random.randint(0, 9999)) + ''.join([random.choice('abddefghijklmnopqrstuvwxyz') for i in range(3)])
    #     player = request.form.get("player")
    #     response = make_response(redirect(url_for('.play_session', tablename=tablename)))
    #     return response

    @app.route('/tables/<tablename>')
    def play_table(tablename):
        return render_template('play_session.html')

    @app.route('/export', methods=["GET"])
    def export_table():
        tablename = request.args.get("tablename")
        app.logger.info(f"exporting table <{tablename}>")
        table = tables.get(tablename)
        return jsonify(table)

    @app.route('/import', methods=["POST"])
    def import_table():
        tablename = request.form.get("tablename")
        app.logger.info(f"importing table <${tablename}>")
        if 'data' not in request.files:
            return redirect(url_for('/'))
        file = request.files['data']
        table = json.loads(file.read())
        tables.store(tablename, table)
        return redirect(url_for('.play_session', tablename=tablename))

    @app.socketio.on('join')
    def handle_join(json):
        app.logger.info(f'join: ${json}')
        table = tables.get(json["tablename"])
        if not table:
            table = tables.create(json["tablename"])
        join_room(json["tablename"])
        emit("initialize table", table)

    @app.socketio.on("update table")
    def handle_update_table(json):
        app.logger.debug(f'update table: ${json}')
        tables.update_component(json["tablename"], json["index"], json["diff"])
        emit("update table", json, broadcast=True, room=json["tablename"])

    @app.socketio.on("add component")
    def handle_add_component(json):
        app.logger.debug(f'add component: ${json}')
        tables.add_component(json["tablename"], json["data"])
        table = tables.get(json["tablename"])
        emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])

    return app





