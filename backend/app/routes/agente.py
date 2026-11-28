"""API del agente conversacional de Zaas (`/api/agente`).

Usa la sesión de Flask-Login creada por `/auth/firebase-login` y exige el token
CSRF en las escrituras, igual que el resto de APIs JSON del proyecto. El motor
de respuestas vive en `app.services.agente_service` y reutiliza las mismas
herramientas que el servidor MCP del ECBD.
"""

from flask import Blueprint, jsonify, request
from flask_login import current_user
from flask_wtf.csrf import generate_csrf, validate_csrf
from wtforms.validators import ValidationError

from app.services.agente_service import responder

agente_api = Blueprint('agente_api', __name__, url_prefix='/api/agente')

MAX_MENSAJE = 500


def _no_autenticado():
    return jsonify({'error': 'Debes iniciar sesión para hablar con el agente.'}), 401


@agente_api.before_request
def proteger_api():
    if request.method == 'OPTIONS':
        return None
    if not current_user.is_authenticated:
        return _no_autenticado()
    if request.method not in ('GET', 'HEAD'):
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except ValidationError:
            return jsonify({
                'error': 'La protección de sesión expiró. Recarga la página.',
            }), 400
    return None


@agente_api.get('/sesion')
def sesion():
    return jsonify(
        usuario={
            'nombre': (current_user.nombres or current_user.email),
            'tipo_usuario': current_user.tipo_usuario,
        },
        csrf_token=generate_csrf(),
    )


@agente_api.post('/chat')
def chat():
    datos = request.get_json(silent=True)
    if not isinstance(datos, dict):
        return jsonify({'error': 'Envía un mensaje válido.'}), 400

    mensaje = (datos.get('mensaje') or '').strip()
    if not mensaje:
        return jsonify({'error': 'El mensaje no puede estar vacío.'}), 400
    if len(mensaje) > MAX_MENSAJE:
        return jsonify({
            'error': f'El mensaje es demasiado largo (máximo {MAX_MENSAJE} caracteres).',
        }), 400

    resultado = responder(mensaje, es_admin=current_user.tipo_usuario == 'admin')
    return jsonify(resultado), 200
