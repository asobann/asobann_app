from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app, make_response
)
from asobann.store import tables, components, kits

blueprint = Blueprint('components', __name__, url_prefix='/components')

