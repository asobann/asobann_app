import time
from quart import Blueprint, request, current_app, render_template, make_response, jsonify, json

from .. import debug_tools

blueprint = Blueprint('debug', __name__, url_prefix='/debug')


@blueprint.route('setting')
async def get_debug_setting():
    setting = {
        'performanceRecording': current_app.config.get('DEBUG_PERFORMANCE_RECORDING', False),
    }
    return jsonify(setting)


@blueprint.route('add_traces', methods=['POST'])
async def add_traces():
    data = json.loads(await request.get_data())
    s = str(data)
    current_app.logger.debug(f"add trace: {s[:30]}...")
    await current_app.mongo_db.traces.insert_one({'traces': data, 'created_at': time.time() * 1000})
    return await make_response()


@blueprint.route('traces')
async def view_traces():
    return await render_template('debug/traces.html')


@blueprint.route('delete_traces')
async def delete_traces():
    await current_app.mongo_db.traces.delete_many({})
    return "{}"


@blueprint.route('get_traces', methods=['GET'])
async def get_traces():
    since = request.args.get('since')
    traces = current_app.mongo_db.traces.find({'created_at': {'$gt': float(since)}})
    return jsonify({
        'data': [{'traces': t['traces'],
                  'created_at': t['created_at']
                  } async for t in traces]
    })


@blueprint.route('delete_all_traces')
async def delete_all_traces():
    await current_app.mongo_db.traces.delete_many({})
