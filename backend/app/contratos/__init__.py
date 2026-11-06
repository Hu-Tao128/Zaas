from flask import Blueprint

contratos_bp = Blueprint('contratos', __name__, url_prefix='/contratos')

from app.contratos import routes
