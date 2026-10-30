from flask import Blueprint

comunicacion_bp = Blueprint('comunicacion', __name__, url_prefix='/comunicacion')

from app.comunicacion import routes
