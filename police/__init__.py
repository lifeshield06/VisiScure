from flask import Blueprint

police_bp = Blueprint("police", __name__)

from police import routes
