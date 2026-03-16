from flask import Blueprint

orders_bp = Blueprint('orders', __name__)

from . import table_routes