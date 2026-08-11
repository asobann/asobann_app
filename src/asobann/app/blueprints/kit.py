from quart import Blueprint, request, make_response, jsonify, json
from asobann.store import components, kits

blueprint = Blueprint('kits', __name__, url_prefix='/kits')


@blueprint.route('')
async def get_kits():
    return jsonify(await kits.get_all())


@blueprint.route('<kit_name>')
async def get_single_kit(kit_name):
    return jsonify(await kits.get(kit_name))


@blueprint.route('/create', methods=['POST'])
async def upload_component():
    from json import decoder
    try:
        files = await request.files
        data = json.load(files['data'])
        kit = data['kit']
        await kits.create_or_update({'kit': kit})
        comps = data['components']
        for c in comps:
            await components.create_or_update({'component': c})
    except (decoder.JSONDecodeError, KeyError) as ex:
        response = {
            'result': 'error',
            'error': repr(ex),
        }
        return await make_response(jsonify(response), 400)

    response = {
        'result': 'success',
        'kitName': kit['name'],
    }
    return await make_response(jsonify(response), 200)
