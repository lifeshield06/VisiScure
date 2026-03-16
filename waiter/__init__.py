from flask import Blueprint

waiter_bp = Blueprint('waiter', __name__)

from . import routes
