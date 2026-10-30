from flask import Blueprint

catalogo_bp = Blueprint('catalogo', __name__, url_prefix='/catalogo')

from app.catalogo import routes
