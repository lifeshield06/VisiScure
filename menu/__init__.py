from flask import Blueprint

menu_bp = Blueprint(
    'menu',
    __name__,
    template_folder='templates'
)

from . import routes
