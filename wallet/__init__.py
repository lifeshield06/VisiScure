from flask import Blueprint

wallet_bp = Blueprint('wallet', __name__, url_prefix='/wallet')

from . import routes
