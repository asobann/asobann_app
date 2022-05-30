from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, make_response
)
from flask_socketio import SocketIO, emit, join_room
from asobann.store import tables, components, kits
from asobann import socketio
from asobann.app import debug_tools

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


@socketio.on('come by table')
def handle_come_by_table(json):
    if 'DEBUG_HANDLER_WAIT' in current_app.config:
        from time import sleep
        sleep(float(current_app.config['DEBUG_HANDLER_WAIT']))
    current_app.logger.info(f'come by table')
    current_app.logger.debug(f'come by table: {json}')
    table = tables.get(json["tablename"])
    if not table:
        table = tables.create(json["tablename"], None)
    join_room(json["tablename"])
    table = tables.get(json["tablename"])
    emit("load table", table)


@socketio.on('set player name')
def handle_set_player(json):
    current_app.logger.info(f'set player')
    current_app.logger.debug(f'set player: {json}')
    table = tables.get(json["tablename"])
    if not table:
        current_app.logger.error(f"table {json['tablename']} on set player")
        raise RuntimeError('table does not exist')
    player_name = json['player']['name']
    table["players"][player_name] = {
        "name": player_name,
        "isHost": json['player']['isHost'],
    }
    tables.store(json["tablename"], table)
    emit("confirmed player name", {"player": {"name": player_name}})


@event_handler('update single component')
def update_single_component(json, table):
    trace = debug_tools.resume_trace(json)
    trace.trace_point('update single component')
    if "volatile" not in json or not json["volatile"]:
        table["components"][json["componentId"]].update(json["diff"])
    debug_tools.add_log_of_updates(json["componentId"], json["diff"]["lastUpdated"]["from"],
                                   json["diff"]["lastUpdated"]["epoch"])
    trace.end()


@socketio.on(update_single_component.event_name)
def handle_update_single_component(json):
    trace = debug_tools.resume_trace(json)
    trace.trace_point('handle update single component')
    current_app.logger.debug(f'update single component: {json}')
    current_app.logger.info(f'update single component')
    table = tables.get(json["tablename"])
    update_single_component(json, table)
    trace.trace_point('before update_table')
    tables.update_table(json["tablename"], table)
    trace.trace_point('after update_table')
    emit("update single component", json, broadcast=True, room=json["tablename"])
    trace.trace_point('emitted response')
    trace.end()
    current_app.logger.info(f'update single component end')


@socketio.on('update many components')
def handle_update_many_components(json):
    trace = debug_tools.resume_trace(json)
    trace.trace_point('handle update many components')
    current_app.logger.debug(f'update many component: {json}')
    current_app.logger.info(f'update many component')
    trace.trace_point('before update_table')
    if json['diffs']:
        tables.update_components(json['tablename'], json['diffs'])
    if json['componentIdsToRemove']:
        tables.remove_components(json['tablename'], json['componentIdsToRemove'])
    trace.trace_point('after update_table')
    emit("update many components", json, broadcast=True, room=json["tablename"])
    trace.end()


@event_handler('add component')
def add_component(json, table):
    table["components"][json["component"]["componentId"]] = json["component"]


@socketio.on(add_component.event_name)
def handle_add_component(json):
    current_app.logger.info(f'add component: {json["component"]["componentId"]} {json["component"]["name"]}')
    current_app.logger.debug(f'add component: {json}')
    table = tables.get(json["tablename"])
    add_component(json, table)
    tables.update_table(json["tablename"], table)
    emit("add component", {"tablename": json["tablename"], "component": json["component"]}, broadcast=True,
         room=json["tablename"])
    current_app.logger.info(f'add component end')


@socketio.on('add kit')
def handle_add_kit(json):
    current_app.logger.info(f'add kit')
    current_app.logger.debug(f'add kit: {json}')
    tables.add_new_kit_and_components(
        tablename=json['tablename'],
        kitData=json['kitData']['kit'],
        components=json['newComponents'])
    emit('add kit',
         {"tablename": json["tablename"],
          "kit": json["kitData"]["kit"],
          "newComponents": json["newComponents"]},
         broadcast=True, room=json["tablename"])
    current_app.logger.info(f'add kit end')


@event_handler('remove component')
def remove_component(json, table):
    del table["components"][json['componentId']]


@socketio.on(remove_component.event_name)
def handle_remove_component(json):
    current_app.logger.info(f'remove component')
    current_app.logger.debug(f'remove component: {json}')
    table = tables.get(json["tablename"])
    remove_component(json, table)
    tables.update_table(json["tablename"], table)
    emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])


@event_handler('remove kit')
def remove_kit(json, table):
    table["kits"] = [e for e in table["kits"] if e["kitId"] != json['kitId']]


@socketio.on(remove_kit.event_name)
def handle_remove_kit(json):
    current_app.logger.info(f'remove kit')
    current_app.logger.debug(f'remove kit: {json}')
    table = tables.get(json["tablename"])
    remove_kit(json, table)
    tables.update_table(json["tablename"], table)
    emit("refresh table", {"tablename": json["tablename"], "table": table}, broadcast=True, room=json["tablename"])


@socketio.on("sync with me")
def handle_sync_with_me(json):
    current_app.logger.info(f'sync with me')
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
