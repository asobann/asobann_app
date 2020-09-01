from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, make_response, abort,
    jsonify, json
)
from asobann.store import tables, components, kits

blueprint = Blueprint('kits', __name__, url_prefix='/kits')


@blueprint.route('')
def get_kits():
    return jsonify(kits.get_all())


@blueprint.route('/create', methods=['POST'])
def upload_component():
    from json import decoder
    try:
        data = json.load(request.files['data'])
        kit = data['kit']
        components = data['kit']
    except KeyError as ex:
        response = {
            'result': 'error',
            'error': repr(ex),
        }
        return make_response(jsonify(response), 400)
    except decoder.JSONDecodeError as ex:
        response = {
            'result': 'error',
            'error': repr(ex),
        }
        return make_response(jsonify(response), 400)

    response = {
        'result': 'success',
        'id': 'something',
    }
    return make_response(jsonify(response), 200)
