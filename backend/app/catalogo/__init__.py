from flask import Blueprint

catalogo_bp = Blueprint('catalogo', __name__, url_prefix='/catalogo')

from app.catalogo import routes  # noqa: E402,F401
from app.catalogo.api import catalogo_api_bp  # noqa: E402

# La API JSON (/api/catalogo/...) se registra sola al registrar catalogo_bp en la app,
# así no hay que tocar create_app().
catalogo_bp.record_once(lambda estado: estado.app.register_blueprint(catalogo_api_bp))
