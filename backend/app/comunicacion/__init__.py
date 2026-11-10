from flask import Blueprint

comunicacion_bp = Blueprint('comunicacion', __name__, url_prefix='/comunicacion')

from app.comunicacion import routes  # noqa: E402,F401
from app.comunicacion.api import comunicacion_api_bp  # noqa: E402

# Registrar la API JSON al registrar el blueprint principal.
comunicacion_bp.record_once(
    lambda estado: estado.app.register_blueprint(comunicacion_api_bp)
)
