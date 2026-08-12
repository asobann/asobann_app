from quart import Blueprint, request, abort, jsonify
from asobann.store import components

blueprint = Blueprint('components', __name__, url_prefix='/components')


@blueprint.route('')
async def get_components_for_kit():
    kit_name = request.args.get("kit_name")
    if not kit_name:
        return abort(500)
    return jsonify(await components.get_for_kit(kit_name))
