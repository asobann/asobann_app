from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, make_response
)
from flask_socketio import SocketIO, emit, join_room
from asobann.store import tables, components, kits
from . import socketio

blueprint = Blueprint('tables', __name__, url_prefix='/tables')


event_handlers = {}


def event_handler(event_name):
    def passthru(fn):
        fn.event_name = event_name
        event_handlers[event_name] = fn
        return fn
    return passthru


@blueprint.route('/<tablename>', methods=["GET"])
def play_table(tablename):
    return render_template('play_session.html')


@event_handler('come by table')
def come_by_table(json, table):
    if not table:
        table = tables.create(json["tablename"], None)
    join_room(json["tablename"])


@socketio.on(come_by_table.event_name)
def handle_come_by_table(json):
    current_app.logger.info(f'come by table: {json}')
    table = tables.get(json["tablename"])
    come_by_table(json, table)
    table = tables.get(json["tablename"])
    emit("load table", table)


@event_handler('set player name')
def set_player(json, table):
    if not table:
        current_app.logger.error(f"table {json['tablename']} on set player")
        raise RuntimeError('table does not exist')
    player_name = json['player']['name']
    table["players"][player_name] = {
        "name": player_name,
        "isHost": json['player']['isHost'],
    }
    tables.store(json["tablename"], table)


@socketio.on(set_player.event_name)
def handle_set_player(json):
    current_app.logger.info(f'set player: {json}')
    table = tables.get(json["tablename"])
    set_player(json, table)
    emit("confirmed player name", {"player": {"name": json['player']['name']}})


@event_handler('update single component')
def upgrade_single_component(json, table):
    if "volatile" not in json or not json["volatile"]:
        tables.update_component(json["tablename"], json["componentId"], json["diff"])


@socketio.on(upgrade_single_component.event_name)
def handle_update_single_component(json):
    current_app.logger.debug(f'update single component: {json}')
    upgrade_single_component(json, None)
    emit("update single component", json, broadcast=True, room=json["tablename"])


@event_handler('add component')
def add_component(json, table):
    tables.add_component(json["tablename"], json["component"])


@socketio.on(add_component.event_name)
def handle_add_component(json):
    current_app.logger.debug(f'add component: {json}')
    add_component(json, None)
    emit("add component", {"tablename": json["tablename"], "component": json["component"]}, broadcast=True, room=json["tablename"])


@event_handler('add kit')
def add_kit(json, table):
    tables.add_kit(json["tablename"], json["kitData"]["kit"])


@socketio.on(add_kit.event_name)
def handle_add_kit(json):
    current_app.logger.debug(f'add kit: {json}')
    add_kit(json, None)
    emit('add kit', {"tablename": json["tablename"], "kit": json["kitData"]["kit"]}, broadcast=True, room=json["tablename"])


@event_handler('remove component')
def remove_component(json, table):
    tables.remove_component(json['tablename'], json['componentId'])


@socketio.on(remove_component.event_name)
def handle_remove_component(json):
    current_app.logger.debug(f'remove component: {json}')
    remove_component(json, None)
    table = tables.get(json["tablename"])
    emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])


@event_handler('remove kit')
def remove_kit(json, table):
    tables.remove_kit(json['tablename'], json['kitId'])


@socketio.on(remove_kit.event_name)
def handle_remove_kit(json):
    current_app.logger.debug(f'remove kit: {json}')
    remove_kit(json, None)
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

