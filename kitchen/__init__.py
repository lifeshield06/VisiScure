from flask import Blueprint

kitchen_bp = Blueprint('kitchen', __name__)

from . import routes
