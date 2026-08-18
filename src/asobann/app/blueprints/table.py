from quart import Blueprint, render_template, request, redirect, url_for, make_response

from asobann.store import tables, components, kits
from asobann.app import debug_tools

blueprint = Blueprint('tables', __name__, url_prefix='/tables')


@blueprint.route('/<tablename>', methods=["GET"])
async def play_table(tablename):
    return await render_template('play_session.html')


def register_handlers(sio, app):
    logger = app.logger

    @sio.on('come by table')
    async def handle_come_by_table(sid, json):
        if 'DEBUG_HANDLER_WAIT' in app.config:
            import asyncio
            await asyncio.sleep(float(app.config['DEBUG_HANDLER_WAIT']))
        logger.info(f'come by table')
        logger.debug(f'come by table: {json}')
        table = await tables.get(json["tablename"])
        if not table:
            table = await tables.create(json["tablename"], None)
        await sio.enter_room(sid, json["tablename"])
        await sio.emit("load table", table, to=sid)

    @sio.on('set player name')
    async def handle_set_player(sid, json):
        logger.info(f'set player')
        logger.debug(f'set player: {json}')
        table = await tables.get(json["tablename"])
        if not table:
            logger.error(f"table {json['tablename']} on set player")
            raise RuntimeError('table does not exist')
        player_name = json['player']['name']
        table["players"][player_name] = {
            "name": player_name,
            "isHost": json['player']['isHost'],
        }
        await tables.store(json["tablename"], table)
        await sio.emit("confirmed player name", {"player": {"name": player_name}}, to=sid)

    @sio.on('update many components')
    async def handle_update_many_components(sid, json):
        trace = debug_tools.resume_trace(json)
        trace.trace_point('handle update many components')
        logger.debug(f'update many component: {json}')
        logger.info(f'update many component')
        trace.trace_point('before update_table')
        if json['diffs']:
            await tables.update_components(json['tablename'], json['diffs'], json.get('volatileKeys'))
        if json['componentIdsToRemove']:
            await tables.remove_components(json['tablename'], json['componentIdsToRemove'])
        trace.trace_point('after update_table')
        await sio.emit("update many components", json, room=json["tablename"])
        await trace.end()

    @sio.on('add component')
    async def handle_add_component(sid, json):
        logger.info(f'add component: {json["component"]["componentId"]} {json["component"]["name"]}')
        logger.debug(f'add component: {json}')
        await tables.add_component(json["tablename"], json["component"])
        await sio.emit("add component", {"tablename": json["tablename"], "component": json["component"]},
                        room=json["tablename"])
        logger.info(f'add component end')

    @sio.on('add kit')
    async def handle_add_kit(sid, json):
        logger.info(f'add kit')
        logger.debug(f'add kit: {json}')
        await tables.add_new_kit_and_components(
            tablename=json['tablename'],
            kitData=json['kitData']['kit'],
            components=json['newComponents'])
        await sio.emit('add kit',
                        {"tablename": json["tablename"],
                         "kit": json["kitData"]["kit"],
                         "newComponents": json["newComponents"]},
                        room=json["tablename"])
        logger.info(f'add kit end')

    @sio.on("sync with me")
    async def handle_sync_with_me(sid, json):
        logger.info(f'sync with me')
        logger.debug(f'sync with me: {json}')
        await tables.store(json['tablename'], json['tableData'])
        table = await tables.get(json["tablename"])
        await sio.emit("refresh table", {"tablename": json["tablename"], "table": table}, room=json["tablename"])

    @sio.on("mouse movement")
    async def handle_mouse_movement(sid, json):
        await sio.emit("mouse movement", json, room=json["tablename"])


@blueprint.route('', methods=["POST"])
async def create_table():
    tablename = tables.generate_new_tablename()
    form = await request.form
    await tables.create(tablename, form.get('prepared_table'))
    response = make_response(redirect(url_for('tables.play_table', tablename=tablename)))
    return await response
