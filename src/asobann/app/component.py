from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, make_response, abort,
    jsonify, json
)
from asobann.store import tables, components, kits

blueprint = Blueprint('components', __name__, url_prefix='/components')


@blueprint.route('/')
def get_components_for_kit():
    kit_name = request.args.get("kit_name")
    if not kit_name:
        return abort(500)
    return jsonify(components.get_for_kit(kit_name))
