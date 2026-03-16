from flask import Blueprint

guest_verification_bp = Blueprint('guest_verification', __name__)

from . import routes