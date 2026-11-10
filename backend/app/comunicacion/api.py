"""API JSON de comunicación para el frontend React.

Cubre los recursos del MR: conversaciones, mensajes, notificaciones,
calificaciones e incidencias. Usa la misma sesión de Flask-Login que el resto
de APIs (`/auth/firebase-login`).
"""

from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import or_, update

from app.auth.models import Usuario
from app.comunicacion.models import (
    Calificacion, Conversacion, Incidencia, Mensaje, Notificacion,
)
from app.contratos.models import Contrato
from app.extensions import db

comunicacion_api_bp = Blueprint(
    'comunicacion_api', __name__, url_prefix='/api/comunicacion'
)


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


def _usuario_publico(usuario):
    if usuario is None:
        return None
    return {
        'id': usuario.id,
        'nombres': usuario.nombres,
        'apellido_paterno': usuario.apellido_paterno,
        'nombre_completo': usuario.nombre_completo,
    }


def _contrato_de_usuario(id_contrato):
    contrato = db.session.get(Contrato, id_contrato)
    if contrato is None:
        return None
    if current_user.tipo_usuario == 'admin':
        return contrato
    if current_user.id not in (contrato.id_cliente, contrato.id_desarrollador):
        return None
    return contrato


def _crear_notificacion(usuario_id, texto, link=None):
    notificacion = Notificacion(
        id_usuario=usuario_id,
        asunto=texto[:200],
        mensaje=texto,
        link=link,
    )
    db.session.add(notificacion)
    return notificacion


@comunicacion_api_bp.get('/csrf')
def csrf():
    from flask_wtf.csrf import generate_csrf
    return jsonify({'csrf_token': generate_csrf()})


# --------------------------------------------------------- notificaciones

def _notificacion(item):
    return {
        'id': item.id,
        'asunto': item.asunto,
        'mensaje': item.mensaje,
        'leido': bool(item.leido),
        'fecha_hora_creacion': _iso(item.fecha_hora_creacion, utc=True),
        'link': item.link,
    }


@comunicacion_api_bp.get('/notificaciones')
@_requiere()
def listar_notificaciones():
    items = db.session.execute(
        db.select(Notificacion)
        .filter_by(id_usuario=current_user.id)
        .order_by(Notificacion.fecha_hora_creacion.desc())
        .limit(50)
    ).scalars().all()
    no_leidas = sum(1 for item in items if not item.leido)
    return jsonify({
        'items': [_notificacion(item) for item in items],
        'no_leidas': no_leidas,
        'total': len(items),
    })


@comunicacion_api_bp.post('/notificaciones/leer')
@_requiere()
def marcar_notificaciones_leidas():
    db.session.execute(
        update(Notificacion)
        .where(Notificacion.id_usuario == current_user.id)
        .values(leido=True)
    )
    db.session.commit()
    return _ok('Notificaciones marcadas como leídas.')


# ------------------------------------------------------------ conversaciones

def _mensaje(item):
    return {
        'id': item.id,
        'id_conversacion': item.id_conversacion,
        'id_emisor': item.id_emisor,
        'id_receptor': item.id_receptor,
        'contenido': item.contenido,
        'fecha_hora': _iso(item.fecha_hora, utc=True),
        'leido': bool(item.leido),
        'emisor': _usuario_publico(item.emisor),
        'receptor': _usuario_publico(item.receptor),
    }


@comunicacion_api_bp.get('/conversaciones')
@_requiere()
def listar_conversaciones():
    conversaciones = db.session.execute(
        db.select(Conversacion)
        .join(Contrato)
        .filter(or_(
            Contrato.id_cliente == current_user.id,
            Contrato.id_desarrollador == current_user.id,
        ))
        .order_by(Conversacion.fecha_creacion.desc())
    ).scalars().all()

    items = []
    for conversacion in conversaciones:
        ultimo = max(
            (conversacion.mensajes or []),
            key=lambda m: m.fecha_hora or datetime.min,
            default=None,
        )
        items.append({
            'id': conversacion.id,
            'id_contrato': conversacion.id_contrato,
            'fecha_creacion': _iso(conversacion.fecha_creacion, utc=True),
            'contrato_objeto': conversacion.contrato.objeto if conversacion.contrato else None,
            'ultimo_mensaje': _mensaje(ultimo) if ultimo else None,
            'no_leidos': sum(
                1 for m in (conversacion.mensajes or [])
                if m.id_receptor == current_user.id and not m.leido
            ),
        })
    return jsonify({'items': items})


@comunicacion_api_bp.get('/contrato/<int:id>')
@_requiere()
def obtener_chat(id):
    contrato = _contrato_de_usuario(id)
    if contrato is None:
        return _error('Contrato no encontrado o sin permiso.', 404)

    conversacion = db.session.execute(
        db.select(Conversacion).filter_by(id_contrato=id)
    ).scalars().first()
    if conversacion is None:
        conversacion = Conversacion(id_contrato=id)
        db.session.add(conversacion)
        db.session.commit()

    mensajes = db.session.execute(
        db.select(Mensaje)
        .filter_by(id_conversacion=conversacion.id)
        .order_by(Mensaje.fecha_hora)
    ).scalars().all()

    for mensaje in mensajes:
        if mensaje.id_receptor == current_user.id and not mensaje.leido:
            mensaje.leido = True
    db.session.commit()

    receptor = (
        contrato.id_desarrollador
        if current_user.id == contrato.id_cliente
        else contrato.id_cliente
    )
    return jsonify({
        'conversacion': {
            'id': conversacion.id,
            'id_contrato': conversacion.id_contrato,
            'fecha_creacion': _iso(conversacion.fecha_creacion, utc=True),
        },
        'mensajes': [_mensaje(m) for m in mensajes],
        'receptor_id': receptor,
    })


@comunicacion_api_bp.post('/contrato/<int:id>')
@_requiere()
def enviar_mensaje(id):
    contrato = _contrato_de_usuario(id)
    if contrato is None:
        return _error('Contrato no encontrado o sin permiso.', 404)

    datos = _datos_json()
    contenido = str(datos.get('contenido', '')).strip()
    if not contenido:
        return _error('El mensaje no puede estar vacío.', 422, {
            'contenido': 'El mensaje no puede estar vacío.',
        })

    conversacion = db.session.execute(
        db.select(Conversacion).filter_by(id_contrato=id)
    ).scalars().first()
    if conversacion is None:
        conversacion = Conversacion(id_contrato=id)
        db.session.add(conversacion)
        db.session.flush()

    receptor = (
        contrato.id_desarrollador
        if current_user.id == contrato.id_cliente
        else contrato.id_cliente
    )
    mensaje = Mensaje(
        id_conversacion=conversacion.id,
        id_emisor=current_user.id,
        id_receptor=receptor,
        contenido=contenido,
    )
    db.session.add(mensaje)
    _crear_notificacion(
        receptor,
        f'Nuevo mensaje en contrato #{id}',
        link=f'/contratos/{id}',
    )
    db.session.commit()
    return _ok('Mensaje enviado.', 201, mensaje_enviado=_mensaje(mensaje))


# ------------------------------------------------------------ calificaciones

@comunicacion_api_bp.post('/contrato/<int:id>/calificar')
@_requiere()
def calificar_contrato(id):
    contrato = _contrato_de_usuario(id)
    if contrato is None:
        return _error('Contrato no encontrado o sin permiso.', 404)
    if contrato.estado != 'finalizado':
        return _error('Solo se pueden calificar contratos finalizados.', 409)
    if current_user.id not in (contrato.id_cliente, contrato.id_desarrollador):
        return _error('Solo las partes pueden calificar este contrato.', 403)

    ya_califico = db.session.execute(
        db.select(Calificacion).filter_by(
            id_contrato=id, id_evaluador=current_user.id
        )
    ).scalars().first()
    if ya_califico:
        return _error('Ya calificaste este contrato.', 409)

    datos = _datos_json()
    try:
        puntaje = int(datos.get('puntaje'))
    except (TypeError, ValueError):
        return _error('El puntaje es obligatorio.', 422, {
            'puntaje': 'El puntaje es obligatorio.',
        })
    if not 1 <= puntaje <= 5:
        return _error('El puntaje debe estar entre 1 y 5.', 422, {
            'puntaje': 'El puntaje debe estar entre 1 y 5.',
        })

    evaluado = (
        contrato.id_desarrollador
        if current_user.id == contrato.id_cliente
        else contrato.id_cliente
    )
    calificacion = Calificacion(
        id_contrato=id,
        id_evaluador=current_user.id,
        id_evaluado=evaluado,
        puntaje=puntaje,
        comentarios=str(datos.get('comentarios', '')).strip() or None,
    )
    db.session.add(calificacion)
    _crear_notificacion(
        evaluado,
        f'Recibiste una calificación de {puntaje}/5 en contrato #{id}',
        link=f'/perfil/{evaluado}',
    )
    db.session.commit()
    return _ok('Calificación enviada.', 201, calificacion={
        'id': calificacion.id,
        'puntaje': calificacion.puntaje,
        'comentarios': calificacion.comentarios,
    })


# --------------------------------------------------------------- incidencias

def _incidencia(item):
    return {
        'id': item.id,
        'id_usuario': item.id_usuario,
        'id_admin': item.id_admin,
        'id_contrato': item.id_contrato,
        'tipo': item.tipo,
        'descripcion': item.descripcion,
        'estado': item.estado,
        'fecha_hora': _iso(item.fecha_hora, utc=True),
        'resolucion': item.resolucion,
        'fecha_resolucion': _iso(item.fecha_resolucion, utc=True),
        'usuario': _usuario_publico(item.usuario),
        'admin': _usuario_publico(item.admin),
        'contrato_objeto': item.contrato.objeto if item.contrato else None,
    }


@comunicacion_api_bp.get('/incidencias')
@_requiere()
def listar_incidencias():
    query = db.select(Incidencia).order_by(Incidencia.fecha_hora.desc())
    if current_user.tipo_usuario != 'admin':
        query = query.filter_by(id_usuario=current_user.id)
    items = db.session.execute(query).scalars().all()
    return jsonify({'items': [_incidencia(item) for item in items]})


@comunicacion_api_bp.post('/incidencias')
@_requiere()
def crear_incidencia():
    datos = _datos_json()
    tipo = str(datos.get('tipo', '')).strip() or 'otro'
    descripcion = str(datos.get('descripcion', '')).strip()
    if not descripcion:
        return _error('La descripción es obligatoria.', 422, {
            'descripcion': 'La descripción es obligatoria.',
        })

    id_contrato = datos.get('id_contrato')
    if id_contrato:
        try:
            id_contrato = int(id_contrato)
        except (TypeError, ValueError):
            return _error('El contrato indicado no es válido.', 422, {
                'id_contrato': 'El contrato indicado no es válido.',
            })
        contrato = _contrato_de_usuario(id_contrato)
        if contrato is None:
            return _error('El contrato indicado no existe o no te pertenece.', 422, {
                'id_contrato': 'El contrato indicado no existe o no te pertenece.',
            })
        id_contrato = contrato.id
    else:
        id_contrato = None

    incidencia = Incidencia(
        id_usuario=current_user.id,
        id_contrato=id_contrato,
        tipo=tipo,
        descripcion=descripcion,
        estado='abierta',
    )
    db.session.add(incidencia)
    db.session.flush()

    admins = db.session.execute(
        db.select(Usuario).filter_by(tipo_usuario='admin')
    ).scalars().all()
    for admin in admins:
        _crear_notificacion(
            admin.id,
            f'Nueva incidencia de {current_user.nombres}: {tipo}',
            link='/incidencias',
        )

    db.session.commit()
    return _ok('Incidencia reportada.', 201, incidencia=_incidencia(incidencia))


@comunicacion_api_bp.get('/incidencias/<int:id>')
@_requiere()
def ver_incidencia(id):
    incidencia = db.session.get(Incidencia, id)
    if incidencia is None:
        return _error('Incidencia no encontrada.', 404)
    if current_user.tipo_usuario != 'admin' and incidencia.id_usuario != current_user.id:
        return _error('No tienes permiso para ver esta incidencia.', 403)
    return jsonify({'incidencia': _incidencia(incidencia)})


@comunicacion_api_bp.post('/incidencias/<int:id>/resolver')
@_requiere('admin')
def resolver_incidencia(id):
    incidencia = db.session.get(Incidencia, id)
    if incidencia is None:
        return _error('Incidencia no encontrada.', 404)
    if incidencia.estado in ('resuelta', 'cerrada'):
        return _error('Esta incidencia ya fue resuelta.', 409)

    datos = _datos_json()
    resolucion = str(datos.get('resolucion', '')).strip()
    if not resolucion:
        return _error('La resolución es obligatoria.', 422, {
            'resolucion': 'La resolución es obligatoria.',
        })

    incidencia.resolucion = resolucion
    incidencia.estado = 'resuelta'
    incidencia.fecha_resolucion = datetime.utcnow()
    incidencia.id_admin = current_user.id

    _crear_notificacion(
        incidencia.id_usuario,
        f'Tu incidencia #{id} ha sido resuelta.',
        link='/incidencias',
    )
    db.session.commit()
    return _ok('Incidencia resuelta.', incidencia=_incidencia(incidencia))
