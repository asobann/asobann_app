from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, make_response
)
from flask_socketio import SocketIO, emit, join_room
from asobann.store import tables, components, kits
from . import socketio

blueprint = Blueprint('tables', __name__, url_prefix='/tables')


@blueprint.route('/<tablename>', methods=["GET"])
def play_table(tablename):
    return render_template('play_session.html')


@socketio.on('come by table')
def handle_come_by_table(json):
    current_app.logger.info(f'come by table: {json}')
    table = tables.get(json["tablename"])
    if not table:
        table = tables.create(json["tablename"], None)
    join_room(json["tablename"])
    emit("load table", table)


@socketio.on('set player name')
def handle_set_player(json):
    current_app.logger.info(f'set player: {json}')
    table = tables.get(json["tablename"])
    if not table:
        current_app.logger.error(f"table {json['tablename']} on set player")
        return
    player_name = json['player']['name']
    table["players"][player_name] = {
        "name": player_name,
        "isHost": json['player']['isHost'],
    }
    tables.store(json["tablename"], table)
    emit("confirmed player name", {"player": {"name": player_name}})


@socketio.on("update single component")
def handle_update_single_component(json):
    current_app.logger.debug(f'update single component: {json}')
    if "volatile" not in json or not json["volatile"]:
        tables.update_component(json["tablename"], json["componentId"], json["diff"])
    emit("update single component", json, broadcast=True, room=json["tablename"])


@socketio.on("add component")
def handle_add_component(json):
    current_app.logger.debug(f'add component: {json}')
    tables.add_component(json["tablename"], json["component"])
    table = tables.get(json["tablename"])
    emit("add component", {"tablename": json["tablename"], "component": json["component"]}, broadcast=True, room=json["tablename"])


@socketio.on("add kit")
def handle_add_kit(json):
    current_app.logger.debug(f'add kit: {json}')
    tables.add_kit(json["tablename"], json["kitData"]["kit"])
    table = tables.get(json["tablename"])
    emit('add kit', {"tablename": json["tablename"], "kit": json["kitData"]["kit"]}, broadcast=True, room=json["tablename"])


@socketio.on("remove component")
def handle_remove_component(json):
    current_app.logger.debug(f'remove component: {json}')
    tables.remove_component(json['tablename'], json['componentId'])
    table = tables.get(json["tablename"])
    emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])


@socketio.on("remove kit")
def handle_remove_kit(json):
    current_app.logger.debug(f'remove kit: {json}')
    tables.remove_kit(json['tablename'], json['kitId'])
    table = tables.get(json["tablename"])
    emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])


@socketio.on("sync with me")
def handle_sync_with_me(json):
    current_app.logger.debug(f'sync with me: {json}')
    tables.store(json['tablename'], json['tableData'])
    table = tables.get(json["tablename"])
    emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])


@socketio.on("mouse movement")
def handle_mouse_movement(json):
    emit("mouse movement", json, broadcast=True, room=json["tablename"])


@blueprint.route('', methods=["POST"])
def create_table():
    tablename = tables.generate_new_tablename()
    tables.create(tablename, request.form.get('prepared_table'))
    response = make_response(redirect(url_for('tables.play_table', tablename=tablename)))
    return response

