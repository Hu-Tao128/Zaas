import hashlib
from datetime import datetime, timezone
from functools import wraps

from flask import Blueprint, g, jsonify, request
from flask_login import current_user

from app.extensions import db
from app.models.iot import DispositivoIoT, TelemetriaECBD
from app.services.ecbd_service import obtener_kpis_dashboard

iot_bp = Blueprint('iot', __name__, url_prefix='/api/v1')


def require_device_api_key(vista):
    @wraps(vista)
    def decorada(*args, **kwargs):
        api_key = (request.headers.get('X-Device-API-Key') or '').strip()
        if not api_key:
            return jsonify({'error': 'Falta la cabecera X-Device-API-Key.'}), 401

        key_hash = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
        dispositivo = db.session.scalar(
            db.select(DispositivoIoT).where(
                DispositivoIoT.api_key_hash == key_hash,
                DispositivoIoT.activo.is_(True),
            )
        )
        if dispositivo is None:
            return jsonify({'error': 'API Key inválida o dispositivo inactivo.'}), 403

        dispositivo.ultimo_ping = datetime.now(timezone.utc)
        db.session.commit()
        g.dispositivo = dispositivo
        return vista(*args, **kwargs)

    return decorada


def require_admin(vista):
    @wraps(vista)
    def decorada(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Debes iniciar sesión.'}), 401
        if getattr(current_user, 'tipo_usuario', None) != 'admin':
            return jsonify({'error': 'No tienes permiso para acceder a este recurso.'}), 403
        return vista(*args, **kwargs)

    return decorada


def _json_dict():
    datos = request.get_json(silent=True)
    return datos if isinstance(datos, dict) else None


def _modulo(valor, respaldo):
    texto = str(valor or respaldo).strip().lower()
    return texto[:50] or respaldo


def _float_opcional(valor):
    if valor is None or valor == '':
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _int_opcional(valor):
    if valor is None or valor == '':
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _bool_opcional(valor, respaldo=False):
    if valor is None:
        return respaldo
    if isinstance(valor, bool):
        return valor
    if isinstance(valor, str):
        return valor.strip().lower() in {'1', 'true', 'si', 'sí', 'yes', 'on'}
    return bool(valor)


@iot_bp.route('/iot/telemetria', methods=['POST'])
@require_device_api_key
def recibir_telemetria():
    datos = _json_dict()
    if not datos:
        return jsonify({'error': 'JSON inválido.'}), 400

    registro = TelemetriaECBD(
        id_dispositivo=g.dispositivo.id_dispositivo,
        tipo_evento='telemetria',
        modulo_evaluado=_modulo(
            datos.get('modulo') or datos.get('modulo_evaluado'),
            'general',
        ),
        latencia_ms=_float_opcional(datos.get('latencia_ms')),
        memoria_libre_kb=_int_opcional(datos.get('memoria_libre_kb')),
        anomalia_detectada=_bool_opcional(
            datos.get('anomalia', datos.get('anomalia_detectada')),
            False,
        ),
        payload_crudo=datos,
        resumen_agente=datos.get('resumen_agente'),
    )
    db.session.add(registro)
    db.session.commit()

    return jsonify({'status': 'ok', 'id_registro': registro.id_registro}), 201


@iot_bp.route('/dispositivos/evento', methods=['POST'])
@require_device_api_key
def recibir_evento_dispositivo():
    datos = _json_dict()
    if not datos:
        return jsonify({'error': 'JSON inválido.'}), 400

    evento = TelemetriaECBD(
        id_dispositivo=g.dispositivo.id_dispositivo,
        tipo_evento='evento_anomalia',
        modulo_evaluado=_modulo(
            datos.get('modulo') or datos.get('modulo_evaluado'),
            'sistema',
        ),
        latencia_ms=_float_opcional(datos.get('latencia_ms')),
        memoria_libre_kb=_int_opcional(datos.get('memoria_libre_kb')),
        anomalia_detectada=True,
        payload_crudo=datos,
        resumen_agente=(
            datos.get('descripcion')
            or datos.get('resumen_agente')
            or 'Alerta enviada por agente Edge'
        ),
    )
    db.session.add(evento)
    db.session.commit()

    return jsonify({
        'status': 'alerta_registrada',
        'id_registro': evento.id_registro,
    }), 201


@iot_bp.route('/admin/ecbd/kpis', methods=['GET'])
@require_admin
def obtener_kpis_ecbd():
    return jsonify(obtener_kpis_dashboard()), 200
