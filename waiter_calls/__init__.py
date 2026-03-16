
from flask import Blueprint

waiter_calls_bp = Blueprint('waiter_calls', __name__, url_prefix='/api/waiter-calls')

from . import routes

__all__ = ['waiter_calls_bp']
