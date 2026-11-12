"""API JSON del módulo de Pagos para el frontend React.

Sigue las convenciones de `contratos/api.py` y `comunicacion/api.py`:
sesión de Flask-Login, respuestas `{"ok": ..., "mensaje": ..., ...}`.
"""

from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import or_

from app.auth.models import Usuario
from app.contratos.models import Contrato, Entregable
from app.extensions import db
from app.pagos.models import Arbitraje, Disputa, Liberacion, Pago, Recibo
from app.pagos import services

pagos_api_bp = Blueprint('pagos_api', __name__, url_prefix='/pagos/api')


# ---------------------------------------------------------------- utilidades

def _ok(mensaje=None, status=200, **datos):
    return jsonify({'ok': True, 'mensaje': mensaje, **datos}), status


def _error(mensaje, status=400, errores=None):
    return jsonify({'ok': False, 'mensaje': mensaje, 'errores': errores or {}}), status


def _requiere(*roles):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if not current_user.is_authenticated:
                return _error('Debes iniciar sesión.', 401)
            if roles and current_user.tipo_usuario not in roles:
                return _error('No tienes permiso para realizar esta acción.', 403)
            return vista(*args, **kwargs)
        return envoltura
    return decorador


def _iso(valor, utc=False):
    if not valor:
        return None
    texto = valor.isoformat()
    return texto + 'Z' if utc else texto


def _datos_json():
    datos = request.get_json(silent=True)
    return datos if isinstance(datos, dict) else {}


def _int_o_none(valor):
    if valor is None or valor == '':
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _float_o_none(valor):
    if valor is None or valor == '':
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _usuario_publico(usuario):
    if usuario is None:
        return None
    return {
        'id': usuario.id,
        'nombres': usuario.nombres,
        'apellido_paterno': usuario.apellido_paterno,
        'nombre_completo': usuario.nombre_completo,
    }


def _liberacion(item):
    return {
        'id': item.id,
        'id_pago': item.id_pago,
        'id_entregable': item.id_entregable,
        'monto_liberado': item.monto_liberado,
        'motivo': item.motivo,
        'fecha_hora': _iso(item.fecha_hora, utc=True),
        'usuario': _usuario_publico(item.usuario),
    }


def _recibo(item):
    if item is None:
        return None
    return {
        'id': item.id,
        'id_pago': item.id_pago,
        'folio': item.folio,
        'fecha_emision': _iso(item.fecha_emision, utc=True),
        'total': item.total,
        'contenido_html': item.contenido_html,
    }


def _disputa(item):
    return {
        'id': item.id,
        'id_contrato': item.id_contrato,
        'id_admin': item.id_admin,
        'id_reportante': item.id_reportante,
        'id_pago': item.id_pago,
        'id_entregable': item.id_entregable,
        'id_incidencia': item.id_incidencia,
        'tipo': item.tipo,
        'descripcion': item.descripcion,
        'estado': item.estado,
        'fecha_hora_publicacion': _iso(item.fecha_hora_publicacion, utc=True),
        'fecha_hora_resolucion': _iso(item.fecha_hora_resolucion, utc=True),
        'resolucion': item.resolucion,
        'reportante': _usuario_publico(item.reportante),
        'arbitraje': (
            {
                'id': item.arbitrajes[0].id,
                'decision': item.arbitrajes[0].decision,
                'porcentaje_desarrollador': item.arbitrajes[0].porcentaje_desarrollador,
                'notas': item.arbitrajes[0].notas,
                'fecha_hora': _iso(item.arbitrajes[0].fecha_hora, utc=True),
            }
            if item.arbitrajes else None
        ),
    }


def _pago(item):
    recibo = item.recibos[0] if getattr(item, 'recibos', None) else None
    return {
        'id': item.id,
        'id_contrato': item.id_contrato,
        'monto': item.monto,
        'estado_escrow': item.estado_escrow,
        'metodo_pago': item.metodo_pago,
        'transaccion_id': item.transaccion_id,
        'fecha_pago': _iso(item.fecha_pago, utc=True),
        'fecha_liberacion': _iso(item.fecha_liberacion, utc=True),
        'recibo': _recibo(recibo),
        'liberaciones': [_liberacion(x) for x in (item.liberaciones or [])],
    }


def _arbitraje(item):
    if item is None:
        return None
    return {
        'id': item.id,
        'id_disputa': item.id_disputa,
        'id_arbitro': item.id_arbitro,
        'decision': item.decision,
        'porcentaje_desarrollador': item.porcentaje_desarrollador,
        'notas': item.notas,
        'fecha_hora': _iso(item.fecha_hora, utc=True),
    }


@pagos_api_bp.get('/csrf')
def csrf():
    from flask_wtf.csrf import generate_csrf
    return jsonify({'csrf_token': generate_csrf()})


# ---------------------------------------------------------------- pagos

@pagos_api_bp.post('/crear')
@pagos_api_bp.post('/')
@_requiere()
def crear_pago():
    datos = _datos_json()
    id_contrato = _int_o_none(datos.get('id_contrato'))
    if id_contrato is None:
        return _error('El contrato es obligatorio.', 422, {'id_contrato': 'El contrato es obligatorio.'})

    from app.pagos.services import contrato_de_usuario

    contrato = contrato_de_usuario(id_contrato, current_user)
    if contrato is None:
        return _error('Contrato no encontrado o sin permiso.', 404)

    try:
        pago = services.registrar_pago(
            contrato,
            current_user,
            monto=datos.get('monto'),
            metodo_pago=datos.get('metodo_pago'),
            transaccion_id=datos.get('transaccion_id'),
        )
        db.session.commit()
    except PermissionError as exc:
        db.session.rollback()
        return _error(str(exc), 403)
    except ValueError as exc:
        db.session.rollback()
        return _error(str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return _error(f'No se pudo registrar el pago: {exc}', 500)

    return _ok('Pago registrado. Los fondos quedan retenidos en escrow.', 201, pago=_pago(pago))


@pagos_api_bp.get('/<int:id>')
@pagos_api_bp.get('/pago/<int:id>')
@_requiere()
def obtener_pago(id):
    pago = services.obtener_pago(id, current_user)
    if pago is None:
        return _error('Pago no encontrado o sin permiso.', 404)
    return jsonify({'ok': True, 'pago': _pago(pago)})


@pagos_api_bp.get('/contrato/<int:id>')
@pagos_api_bp.get('/contrato/<int:id>/pagos')
@_requiere()
def listar_pagos_contrato(id):
    pagos = services.listar_pagos_contrato(id, current_user)
    if pagos is None:
        return _error('Contrato no encontrado o sin permiso.', 404)
    return jsonify({'ok': True, 'items': [_pago(p) for p in pagos], 'total': len(pagos)})


@pagos_api_bp.get('/pagos')
@pagos_api_bp.get('/')
@_requiere()
def listar_pagos():
    id_contrato = _int_o_none(request.args.get('id_contrato') or request.args.get('contrato'))
    if id_contrato is not None:
        pagos = services.listar_pagos_contrato(id_contrato, current_user)
        if pagos is None:
            return _error('Contrato no encontrado o sin permiso.', 404)
        return jsonify({'ok': True, 'items': [_pago(p) for p in pagos], 'total': len(pagos)})

    # Sin contrato: pagos de los contratos del usuario.
    if current_user.tipo_usuario == 'admin':
        query = db.select(Pago).order_by(Pago.fecha_pago.desc())
    else:
        query = (
            db.select(Pago)
            .join(Contrato)
            .filter(or_(Contrato.id_cliente == current_user.id, Contrato.id_desarrollador == current_user.id))
            .order_by(Pago.fecha_pago.desc())
        )
    pagos = db.session.execute(query).scalars().all()
    return jsonify({'ok': True, 'items': [_pago(p) for p in pagos], 'total': len(pagos)})


# ---------------------------------------------------------------- liberaciones

@pagos_api_bp.post('/liberaciones/crear')
@pagos_api_bp.post('/liberaciones')
@pagos_api_bp.post('/pagos/<int:id_pago>/liberar')
@pagos_api_bp.post('/pagos/<int:id_pago>/liberaciones')
@_requiere()
def crear_liberacion(id_pago=None):
    datos = _datos_json()
    if id_pago is None:
        id_pago = _int_o_none(datos.get('id_pago'))
    if id_pago is None:
        return _error('El pago es obligatorio.', 422, {'id_pago': 'El pago es obligatorio.'})

    pago = services.obtener_pago(id_pago, current_user)
    if pago is None:
        return _error('Pago no encontrado o sin permiso.', 404)

    monto = datos.get('monto_liberado', datos.get('monto'))
    id_entregable = _int_o_none(datos.get('id_entregable'))
    motivo = datos.get('motivo')

    try:
        liberacion = services.crear_liberacion(pago, current_user, monto, id_entregable, motivo)
        db.session.commit()
    except PermissionError as exc:
        db.session.rollback()
        return _error(str(exc), 403)
    except ValueError as exc:
        db.session.rollback()
        return _error(str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return _error(f'No se pudo registrar la liberación: {exc}', 500)

    return _ok('Liberación registrada.', 201, liberacion=_liberacion(liberacion))


@pagos_api_bp.get('/pagos/<int:id_pago>/liberaciones')
@pagos_api_bp.get('/liberaciones/<int:id_pago>')
@pagos_api_bp.get('/liberaciones')
@_requiere()
def listar_liberaciones(id_pago=None):
    if id_pago is None:
        id_pago = _int_o_none(request.args.get('id_pago'))
    if id_pago is None:
        return _error('El pago es obligatorio.', 422, {'id_pago': 'El pago es obligatorio.'})

    liberaciones = services.listar_liberaciones_pago(id_pago, current_user)
    if liberaciones is None:
        return _error('Pago no encontrado o sin permiso.', 404)
    return jsonify({'ok': True, 'items': [_liberacion(x) for x in liberaciones], 'total': len(liberaciones)})


# ---------------------------------------------------------------- recibos

@pagos_api_bp.get('/pagos/<int:id_pago>/recibo')
@pagos_api_bp.get('/recibos/<int:id_pago>')
@pagos_api_bp.get('/recibo/<int:id_pago>')
@pagos_api_bp.get('/recibos')
@_requiere()
def obtener_recibo(id_pago=None):
    if id_pago is None:
        id_pago = _int_o_none(request.args.get('id_pago'))
    if id_pago is None:
        return _error('El pago es obligatorio.', 422, {'id_pago': 'El pago es obligatorio.'})

    recibo = services.obtener_recibo_pago(id_pago, current_user)
    if recibo is None:
        # Puede que el pago exista pero sin recibo; intentar generar.
        pago = services.obtener_pago(id_pago, current_user)
        if pago is None:
            return _error('Pago no encontrado o sin permiso.', 404)
        recibo = services.generar_recibo(pago)
        db.session.commit()
    return jsonify({'ok': True, 'recibo': _recibo(recibo)})


# ---------------------------------------------------------------- disputas

@pagos_api_bp.post('/disputas/crear')
@pagos_api_bp.post('/disputas')
@pagos_api_bp.post('/contrato/<int:id>/disputa')
@_requiere()
def crear_disputa(id=None):
    datos = _datos_json()
    id_contrato = id if id is not None else _int_o_none(datos.get('id_contrato'))
    if id_contrato is None:
        return _error('El contrato es obligatorio.', 422, {'id_contrato': 'El contrato es obligatorio.'})

    from app.pagos.services import contrato_de_usuario

    contrato = contrato_de_usuario(id_contrato, current_user)
    if contrato is None:
        return _error('Contrato no encontrado o sin permiso.', 404)

    id_pago = _int_o_none(datos.get('id_pago'))
    id_entregable = _int_o_none(datos.get('id_entregable'))
    id_incidencia = _int_o_none(datos.get('id_incidencia'))

    try:
        disputa = services.abrir_disputa(
            contrato,
            current_user,
            datos.get('tipo', 'otro'),
            datos.get('descripcion', ''),
            id_pago=id_pago,
            id_entregable=id_entregable,
            id_incidencia=id_incidencia,
        )
        db.session.commit()
    except PermissionError as exc:
        db.session.rollback()
        return _error(str(exc), 403)
    except ValueError as exc:
        db.session.rollback()
        return _error(str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return _error(f'No se pudo abrir la disputa: {exc}', 500)

    return _ok('Disputa abierta.', 201, disputa=_disputa(disputa))


@pagos_api_bp.get('/disputas/<int:id>')
@_requiere()
def obtener_disputa(id):
    disputa = services.obtener_disputa(id, current_user)
    if disputa is None:
        return _error('Disputa no encontrada o sin permiso.', 404)
    return jsonify({'ok': True, 'disputa': _disputa(disputa)})


@pagos_api_bp.get('/disputas')
@_requiere()
def listar_disputas():
    items = services.listar_disputas(current_user)
    return jsonify({'ok': True, 'items': [_disputa(d) for d in items], 'total': len(items)})


# ---------------------------------------------------------------- arbitraje

@pagos_api_bp.post('/disputas/<int:id>/arbitraje')
@pagos_api_bp.post('/disputas/<int:id>/resolver')
@pagos_api_bp.post('/arbitrajes/crear')
@pagos_api_bp.post('/arbitrajes')
@_requiere('admin')
def crear_arbitraje(id=None):
    datos = _datos_json()
    if id is None:
        id = _int_o_none(datos.get('id_disputa') or datos.get('id'))
    if id is None:
        return _error('La disputa es obligatoria.', 422, {'id_disputa': 'La disputa es obligatoria.'})

    disputa = services.obtener_disputa(id, current_user)
    if disputa is None:
        return _error('Disputa no encontrada o sin permiso.', 404)

    decision = datos.get('decision')
    porcentaje = datos.get('porcentaje_desarrollador', datos.get('porcentaje'))
    notas = datos.get('notas') or datos.get('resolucion')

    try:
        arbitraje = services.crear_arbitraje(disputa, current_user, decision, porcentaje, notas)
        db.session.commit()
    except PermissionError as exc:
        db.session.rollback()
        return _error(str(exc), 403)
    except ValueError as exc:
        db.session.rollback()
        return _error(str(exc), 400)
    except Exception as exc:  # noqa: BLE001
        db.session.rollback()
        return _error(f'No se pudo crear el arbitraje: {exc}', 500)

    db.session.refresh(disputa)
    return _ok('Disputa resuelta.', 201, arbitraje=_arbitraje(arbitraje), disputa=_disputa(disputa))


@pagos_api_bp.get('/disputas/<int:id>/arbitraje')
@pagos_api_bp.get('/arbitrajes/<int:id>')
@pagos_api_bp.get('/arbitrajes')
@_requiere()
def obtener_arbitraje(id=None):
    if id is None:
        id = _int_o_none(request.args.get('id_disputa') or request.args.get('id'))
    if id is None:
        # Si no hay id, listar todos (admin) o los del usuario.
        if current_user.tipo_usuario == 'admin':
            items = db.session.execute(db.select(Arbitraje).order_by(Arbitraje.fecha_hora.desc())).scalars().all()
        else:
            items = []
        return jsonify({'ok': True, 'items': [_arbitraje(x) for x in items], 'total': len(items)})

    # id puede ser de disputa o de arbitraje: intentar ambos.
    arbitraje = db.session.get(Arbitraje, id)
    if arbitraje is None:
        arbitraje = services.obtener_arbitraje_disputa(id, current_user)
    if arbitraje is None:
        return _error('Arbitraje no encontrado o sin permiso.', 404)
    # Permiso: admin o parte de la disputa.
    disputa = arbitraje.disputa
    contrato = disputa.contrato
    if current_user.tipo_usuario != 'admin' and current_user.id not in (contrato.id_cliente, contrato.id_desarrollador):
        return _error('Sin permiso.', 403)
    return jsonify({'ok': True, 'arbitraje': _arbitraje(arbitraje)})
