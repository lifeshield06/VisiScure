from flask import Blueprint

hotel_manager_bp = Blueprint('hotel_manager', __name__)

from . import routes
