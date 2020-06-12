from flask import Flask, render_template, request, redirect, url_for, jsonify, json, make_response, abort
from flask_socketio import SocketIO, emit, join_room
from flask_pymongo import PyMongo
from logging.config import dictConfig
import random
import string

from asobann import tables, components, kits

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
    app.socketio = SocketIO(app)
    app.logger.info("connected to mongo")

    tables.connect(app.mongo)
    components.connect(app.mongo)
    kits.connect(app.mongo)

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

    @app.route('/tables/<tablename>', methods=["GET"])
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
        tablename = tables.generate_new_tablename()
        app.logger.info(f"importing table <{tablename}>")
        if 'data' not in request.files:
            return redirect(url_for('/'))
        file = request.files['data']
        table = json.loads(file.read())
        tables.store(tablename, table)
        return redirect(url_for('.play_table', tablename=tablename))

    @app.socketio.on('come by table')
    def handle_come_by_table(json):
        app.logger.info(f'come by table: {json}')
        table = tables.get(json["tablename"])
        if not table:
            table = tables.create(json["tablename"], None)
        join_room(json["tablename"])
        emit("load table", table)

    @app.socketio.on('set player name')
    def handle_set_player(json):
        app.logger.info(f'set player: {json}')
        table = tables.get(json["tablename"])
        if not table:
            app.logger.error(f"table {json['tablename']} on set player")
            return
        player_name = json['player']['name']
        table["players"][player_name] = {
            "name": player_name,
            "isHost": json['player']['isHost'],
        }
        tables.store(json["tablename"], table)
        emit("confirmed player name", {"player": {"name": player_name}})

    @app.socketio.on("update single component")
    def handle_update_single_component(json):
        app.logger.debug(f'update single component: {json}')
        if "volatile" not in json or not json["volatile"]:
            tables.update_component(json["tablename"], json["componentId"], json["diff"])
        emit("update single component", json, broadcast=True, room=json["tablename"])

    @app.socketio.on("add component")
    def handle_add_component(json):
        app.logger.debug(f'add component: {json}')
        tables.add_component(json["tablename"], json["component"])
        table = tables.get(json["tablename"])
        emit("add component", {"tablename": json["tablename"], "component": json["component"]}, broadcast=True, room=json["tablename"])

    @app.socketio.on("add kit")
    def handle_add_kit(json):
        app.logger.debug(f'add kit: {json}')
        tables.add_kit(json["tablename"], json["data"]["kit"])
        for component_data in json["data"]["components"].values():
            tables.add_component(json["tablename"], component_data)
        table = tables.get(json["tablename"])
        emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])

    @app.socketio.on("remove component")
    def handle_remove_component(json):
        app.logger.debug(f'remove component: {json}')
        tables.remove_component(json['tablename'], json['componentId'])
        table = tables.get(json["tablename"])
        emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])

    @app.socketio.on("remove kit")
    def handle_remove_kit(json):
        app.logger.debug(f'remove kit: {json}')
        tables.remove_kit(json['tablename'], json['kitId'])
        table = tables.get(json["tablename"])
        emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])

    @app.socketio.on("sync with me")
    def handle_sync_with_me(json):
        app.logger.debug(f'sync with me: {json}')
        tables.store(json['tablename'], json['tableData'])
        table = tables.get(json["tablename"])
        emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])

    @app.socketio.on("mouse movement")
    def handle_mouse_movement(json):
        emit("mouse movement", json, broadcast=True, room=json["tablename"])

    @app.route('/customize')
    def customize():
        return render_template('customize.html')

    @app.route('/tables', methods=["POST"])
    def create_table():
        tablename = tables.generate_new_tablename()
        print(request.form)
        tables.create(tablename, request.form.get('prepared_table'))
        response = make_response(redirect(url_for('.play_table', tablename=tablename)))
        return response

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

