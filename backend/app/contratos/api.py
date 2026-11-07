"""API JSON del módulo de Contratos Escrow para el frontend React.

Reutiliza los formularios WTForms y la lógica de negocio de ``routes.py`` pero
responde siempre JSON. La sesión es la cookie de Flask-Login que crea
``/auth/callback``.

Convenciones:
  éxito -> {"ok": true, "mensaje": "...", ...datos}
  error -> {"ok": false, "mensaje": "...", "errores": {"campo": "mensaje"}}
"""

import hashlib
import html
import uuid
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import current_user
from sqlalchemy import or_
from werkzeug.datastructures import MultiDict

from app.auth.models import Usuario
from app.catalogo.models import OfertaTrabajo, Proyecto
from app.contratos.forms import AceptacionForm, ContratoForm
from app.contratos.models import Aceptacion, Contrato, PlantillaContrato
from app.contratos.plantillas import (
    NOMBRE_PLANTILLA_BASE,
    ensure_default_plantilla,
    render_plantilla,
)
from app.extensions import db
from app.pagos.models import Pago, Recibo

contratos_api_bp = Blueprint('contratos_api', __name__, url_prefix='/contratos/api')


# ---------------------------------------------------------------- utilidades

def _ok(mensaje=None, status=200, **datos):
    return jsonify({'ok': True, 'mensaje': mensaje, **datos}), status


def _error(mensaje, status=400, errores=None):
    return jsonify({'ok': False, 'mensaje': mensaje, 'errores': errores or {}}), status


def _requiere(*roles):
    """Exige sesión iniciada y, opcionalmente, uno de los roles indicados (JSON)."""
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if not current_user.is_authenticated:
                return _error('Debes iniciar sesión para gestionar contratos.', 401)
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


def _formdata(datos, *, bools=()):
    """Convierte el JSON del cliente en el MultiDict de strings que esperan los WTForms."""
    md = MultiDict()
    for clave, valor in datos.items():
        if clave in bools:
            if valor:
                md.add(clave, 'y')
            continue
        if valor is None or valor == '':
            continue
        md.add(clave, str(valor))
    return md


def _errores_form(form):
    return {campo: msgs[0] for campo, msgs in form.errors.items() if msgs}


def _form_invalido(form):
    # La validación de WTForms se reporta como 400 Bad Request con el detalle por campo.
    return _error('Revisa los campos del formulario.', 400, _errores_form(form))


def _get_client_ip():
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or ''


def _es_parte(contrato):
    return current_user.id in (contrato.id_cliente, contrato.id_desarrollador)


def _puede_ver_contrato(contrato):
    return _es_parte(contrato) or current_user.tipo_usuario == 'admin'


def _ya_firmo(contrato, usuario_id):
    if usuario_id == contrato.id_cliente:
        return bool(contrato.firma_cliente)
    if usuario_id == contrato.id_desarrollador:
        return bool(contrato.firma_desarrollador)
    return False


def _contrato_o_error(id):
    contrato = db.session.get(Contrato, id)
    if contrato is None:
        return None, _error('Contrato no encontrado.', 404)
    if not _puede_ver_contrato(contrato):
        return None, _error('No tienes permiso para ver este contrato.', 403)
    return contrato, None


# ------------------------------------------------------------- serializadores

def _usuario_publico(usuario):
    if usuario is None:
        return None
    return {
        'id': usuario.id,
        'nombres': usuario.nombres,
        'apellido_paterno': usuario.apellido_paterno,
        'nombre_completo': usuario.nombre_completo,
    }


def _escrow(contrato):
    pagos = sorted(contrato.pagos or [], key=lambda p: p.fecha_pago or datetime.min)
    total = float(contrato.costo_acordado or 0)
    retenido = sum(float(p.monto or 0) for p in pagos if p.estado_escrow == 'retenido')
    liberado = sum(float(p.monto or 0) for p in pagos if p.estado_escrow == 'liberado')

    if not pagos:
        estado = 'sin_deposito'
    elif retenido > 0:
        estado = 'retenido'
    elif liberado > 0:
        estado = 'liberado'
    else:
        estado = pagos[-1].estado_escrow or 'sin_deposito'

    return {
        'estado': estado,
        'monto_total': total,
        'monto_retenido': retenido,
        'monto_liberado': liberado,
        'num_pagos': len(pagos),
        'moneda': 'MXN',
    }


def _pago(pago):
    return {
        'id': pago.id,
        'monto': pago.monto,
        'estado_escrow': pago.estado_escrow,
        'fecha_pago': _iso(pago.fecha_pago, utc=True),
        'fecha_liberacion': _iso(pago.fecha_liberacion, utc=True),
    }


def _entregable(entregable):
    return {
        'id': entregable.id,
        'titulo': entregable.titulo,
        'descripcion': entregable.descripcion,
        'url_archivo': entregable.url_archivo,
        'estado': entregable.estado,
        'fecha_subida': _iso(entregable.fecha_subida, utc=True),
        'fecha_revision': _iso(entregable.fecha_revision, utc=True),
        'comentario_revision': entregable.comentario_revision,
    }


def _aceptacion(aceptacion):
    return {
        'id': aceptacion.id,
        'usuario': _usuario_publico(aceptacion.usuario),
        'fecha_hora': _iso(aceptacion.fecha_hora, utc=True),
        'ip': aceptacion.ip,
    }


def _contrato_resumen(contrato):
    soy_cliente = current_user.id == contrato.id_cliente
    contraparte = contrato.desarrollador if soy_cliente else contrato.cliente
    return {
        'id': contrato.id,
        'rol': 'cliente' if soy_cliente else 'desarrollador',
        'estado': contrato.estado,
        'objeto': contrato.objeto,
        'costo_acordado': contrato.costo_acordado,
        'moneda': 'MXN',
        'fecha_creacion': _iso(contrato.fecha_creacion, utc=True),
        'cliente': _usuario_publico(contrato.cliente),
        'desarrollador': _usuario_publico(contrato.desarrollador),
        'contraparte': _usuario_publico(contraparte),
        'producto': (
            {'id': contrato.producto.id, 'titulo': contrato.producto.titulo}
            if contrato.producto else None
        ),
        'encargo': (
            {'id': contrato.encargo.id, 'titulo': contrato.encargo.titulo}
            if contrato.encargo else None
        ),
        'firmas': {
            'cliente': bool(contrato.firma_cliente),
            'desarrollador': bool(contrato.firma_desarrollador),
            'completas': contrato.firmas_completas,
        },
        'escrow': _escrow(contrato),
    }


def _acciones(contrato):
    soy_cliente = current_user.id == contrato.id_cliente
    soy_desarrollador = current_user.id == contrato.id_desarrollador
    es_parte = soy_cliente or soy_desarrollador
    ya_firme = _ya_firmo(contrato, current_user.id)
    puede_firmar = (
        es_parte
        and contrato.estado in ('borrador', 'pendiente')
        and not ya_firme
    )
    return {
        'es_parte': es_parte,
        'soy_cliente': soy_cliente,
        'soy_desarrollador': soy_desarrollador,
        'ya_firme': ya_firme,
        'puede_firmar': puede_firmar,
        'puede_cancelar': es_parte and contrato.estado not in ('finalizado', 'cancelado'),
        'puede_subir_entregable': (
            soy_desarrollador and contrato.estado in ('aceptado', 'en_progreso')
        ),
        'puede_revisar_entregables': soy_cliente,
        'puede_depositar_escrow': soy_cliente and not (contrato.pagos or []),
    }


def _contrato_detalle(contrato):
    data = _contrato_resumen(contrato)
    data.update({
        'documento_html': contrato.terminos_condiciones or '',
        'firma_cliente': contrato.firma_cliente,
        'firma_desarrollador': contrato.firma_desarrollador,
        'aceptaciones': [_aceptacion(a) for a in (contrato.aceptaciones or [])],
        'entregables': [_entregable(e) for e in (contrato.entregables or [])],
        'pagos': [_pago(p) for p in (contrato.pagos or [])],
        'acciones': _acciones(contrato),
    })
    return data


# ------------------------------------------------------------------ opciones

def _opciones_contrato():
    desarrolladores = db.session.execute(
        db.select(Usuario)
        .filter(
            Usuario.tipo_usuario == 'desarrollador',
            Usuario.id != current_user.id,
        )
        .order_by(Usuario.nombres, Usuario.apellido_paterno)
    ).scalars().all()

    proyectos = db.session.execute(
        db.select(Proyecto)
        .filter(Proyecto.estado == 'activo')
        .order_by(Proyecto.titulo)
    ).scalars().all()

    ofertas = db.session.execute(
        db.select(OfertaTrabajo)
        .filter(OfertaTrabajo.id_cliente == current_user.id)
        .order_by(OfertaTrabajo.titulo)
    ).scalars().all()

    plantillas = db.session.execute(
        db.select(PlantillaContrato).order_by(PlantillaContrato.id)
    ).scalars().all()
    if not plantillas:
        plantillas = [ensure_default_plantilla()]
    plantillas = sorted(
        plantillas,
        key=lambda p: (p.nombre != NOMBRE_PLANTILLA_BASE, p.id),
    )

    usuario_actual = _usuario_publico(current_user)
    usuario_actual['email'] = current_user.email

    return {
        'usuario': usuario_actual,
        'desarrolladores': [_usuario_publico(u) for u in desarrolladores],
        'productos': [
            {
                'id': p.id,
                'titulo': p.titulo,
                'id_usuario': p.id_usuario,
                'precio': p.precio,
            }
            for p in proyectos
        ],
        'ofertas': [
            {
                'id': o.id,
                'titulo': o.titulo,
                'presupuesto': o.presupuesto,
                'estado': o.estado,
            }
            for o in ofertas
        ],
        'plantillas': [
            {
                'id': p.id,
                'nombre': p.nombre,
                'es_base': p.nombre == NOMBRE_PLANTILLA_BASE,
            }
            for p in plantillas
        ],
    }


@contratos_api_bp.get('/csrf')
def csrf():
    """Token CSRF reutilizable por el frontend (compatibilidad con catalogoApi)."""
    from flask_wtf.csrf import generate_csrf
    return jsonify({'csrf_token': generate_csrf()})


@contratos_api_bp.get('/opciones')
@_requiere()
def opciones():
    return jsonify(_opciones_contrato())


# -------------------------------------------------------------------- rutas

@contratos_api_bp.get('/')
@_requiere()
def listar_contratos():
    estado = request.args.get('estado', '', type=str).strip()
    query = (
        db.select(Contrato)
        .filter(or_(
            Contrato.id_cliente == current_user.id,
            Contrato.id_desarrollador == current_user.id,
        ))
        .order_by(Contrato.fecha_creacion.desc())
    )
    if estado:
        query = query.filter(Contrato.estado == estado)
    contratos = db.session.execute(query).scalars().all()
    return jsonify({
        'ok': True,
        'items': [_contrato_resumen(c) for c in contratos],
        'total': len(contratos),
    })


@contratos_api_bp.get('/<int:id>')
@_requiere()
def detalle_contrato(id):
    contrato, error = _contrato_o_error(id)
    if error:
        return error
    if not contrato.terminos_condiciones:
        # Contratos antiguos sin documento: generarlo con la plantilla base.
        plantilla = ensure_default_plantilla()
        contrato.terminos_condiciones = render_plantilla(
            plantilla.contenido_html,
            _contexto_plantilla(contrato),
            claves_html={'notas_html'},
        )
        db.session.commit()
    return jsonify({'ok': True, 'contrato': _contrato_detalle(contrato)})


def _contexto_plantilla(contrato, notas=''):
    notas = (notas or '').strip()
    notas_html = ''
    if notas:
        notas_html = (
            '<h3>Notas adicionales</h3><p>'
            + html.escape(notas).replace('\n', '<br>')
            + '</p>'
        )
    fecha = contrato.fecha_creacion or datetime.utcnow()
    return {
        'contrato_id': contrato.id,
        'fecha': fecha.strftime('%d/%m/%Y'),
        'cliente_nombre': contrato.cliente.nombre_completo,
        'cliente_email': contrato.cliente.email,
        'desarrollador_nombre': contrato.desarrollador.nombre_completo,
        'desarrollador_email': contrato.desarrollador.email,
        'objeto': (
            f'Desarrollo del proyecto "{contrato.producto.titulo}"'
            if contrato.producto else
            f'Desarrollo del encargo "{contrato.encargo.titulo}"'
            if contrato.encargo else
            'Servicio de desarrollo de software'
        ),
        'costo': f'{contrato.costo_acordado:,.2f}',
        'notas_html': notas_html,
    }


@contratos_api_bp.post('/crear')
@_requiere()
def crear_contrato():
    datos = _datos_json()
    form = ContratoForm(formdata=_formdata(datos), meta={'csrf': False})

    if not form.validate():
        return _form_invalido(form)

    valido = True

    desarrollador = db.session.get(Usuario, form.id_desarrollador.data)
    if not desarrollador or desarrollador.tipo_usuario != 'desarrollador':
        form.id_desarrollador.errors.append('Selecciona un desarrollador válido.')
        valido = False
    elif desarrollador.id == current_user.id:
        form.id_desarrollador.errors.append('No puedes crear un contrato contigo mismo.')
        valido = False

    producto = None
    if form.id_producto.data:
        producto = db.session.get(Proyecto, form.id_producto.data)
        if producto is None:
            form.id_producto.errors.append('El producto seleccionado no existe.')
            valido = False
        elif desarrollador and producto.id_usuario != desarrollador.id:
            form.id_producto.errors.append(
                'El producto no pertenece al desarrollador seleccionado.'
            )
            valido = False

    encargo = None
    if form.id_encargo.data:
        encargo = db.session.get(OfertaTrabajo, form.id_encargo.data)
        if encargo is None:
            form.id_encargo.errors.append('La oferta seleccionada no existe.')
            valido = False
        elif encargo.id_cliente != current_user.id:
            form.id_encargo.errors.append('La oferta no pertenece a tu cuenta.')
            valido = False

    plantilla = db.session.get(PlantillaContrato, form.plantilla_id.data)
    if plantilla is None:
        form.plantilla_id.errors.append('La plantilla seleccionada no existe.')
        valido = False

    if not valido:
        return _form_invalido(form)

    contrato = Contrato(
        id_cliente=current_user.id,
        id_desarrollador=desarrollador.id,
        id_producto=producto.id if producto else None,
        id_encargo=encargo.id if encargo else None,
        costo_acordado=float(form.costo_acordado.data),
        estado='borrador',
    )
    db.session.add(contrato)
    db.session.flush()

    contrato.terminos_condiciones = render_plantilla(
        plantilla.contenido_html,
        _contexto_plantilla(contrato, form.notas.data),
        claves_html={'notas_html'},
    )
    db.session.commit()

    return _ok(
        'Contrato creado como borrador. Revisa y firma para formalizarlo.',
        201,
        contrato=_contrato_detalle(contrato),
    )


def _html_recibo(pago, contrato):
    return (
        '<html><body>'
        '<h1>Recibo de depósito Escrow - Zaas</h1>'
        f'<p><strong>Monto:</strong> ${pago.monto:,.2f} MXN</p>'
        f'<p><strong>Contrato:</strong> #{contrato.id}</p>'
        f'<p><strong>Cliente:</strong> {html.escape(contrato.cliente.nombre_completo)}</p>'
        f'<p><strong>Desarrollador:</strong> {html.escape(contrato.desarrollador.nombre_completo)}</p>'
        f'<p><strong>Estado:</strong> {pago.estado_escrow}</p>'
        '</body></html>'
    )


def _depositar_escrow(contrato):
    existente = db.session.execute(
        db.select(Pago).filter_by(id_contrato=contrato.id)
    ).scalars().first()
    if existente:
        return existente

    pago = Pago(
        id_contrato=contrato.id,
        monto=contrato.costo_acordado,
        estado_escrow='retenido',
    )
    db.session.add(pago)
    db.session.flush()

    folio = f'ZAS-{datetime.utcnow():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}'
    db.session.add(Recibo(
        id_pago=pago.id,
        folio=folio,
        contenido_html=_html_recibo(pago, contrato),
    ))
    return pago


@contratos_api_bp.post('/<int:id>/aceptar')
@_requiere()
def aceptar_contrato(id):
    contrato, error = _contrato_o_error(id)
    if error:
        return error

    if not _es_parte(contrato):
        return _error('No tienes permiso para firmar este contrato.', 403)
    if contrato.estado not in ('borrador', 'pendiente'):
        return _error('Este contrato ya no se puede aceptar en su estado actual.', 409)
    if _ya_firmo(contrato, current_user.id):
        return _error('Ya firmaste este contrato.', 409)

    if not contrato.terminos_condiciones:
        plantilla = ensure_default_plantilla()
        contrato.terminos_condiciones = render_plantilla(
            plantilla.contenido_html,
            _contexto_plantilla(contrato),
            claves_html={'notas_html'},
        )

    form = AceptacionForm(
        formdata=_formdata(_datos_json(), bools=('acepto',)),
        meta={'csrf': False},
    )
    if not form.validate():
        return _form_invalido(form)

    firma_hash = hashlib.sha256(
        f'{current_user.id}:{contrato.id}:{datetime.utcnow().isoformat()}:{_get_client_ip()}'.encode()
    ).hexdigest()[:16]

    if current_user.id == contrato.id_cliente:
        contrato.firma_cliente = firma_hash
    elif current_user.id == contrato.id_desarrollador:
        contrato.firma_desarrollador = firma_hash

    db.session.add(Aceptacion(
        id_contrato=contrato.id,
        id_usuario=current_user.id,
        ip=_get_client_ip(),
    ))

    contrato.estado = 'aceptado' if contrato.firmas_completas else 'pendiente'

    deposito = None
    if current_user.id == contrato.id_cliente and not contrato.pagos:
        deposito = _depositar_escrow(contrato)

    db.session.commit()

    if deposito is not None:
        mensaje = 'Contrato aceptado y fondos retenidos en Escrow.'
    elif contrato.estado == 'aceptado':
        mensaje = 'Contrato aceptado por ambas partes. Ya pueden comenzar.'
    else:
        mensaje = 'Tu aceptación fue registrada. Falta la firma de la otra parte.'

    return _ok(mensaje, contrato=_contrato_detalle(contrato))


@contratos_api_bp.post('/<int:id>/cancelar')
@_requiere()
def cancelar_contrato(id):
    contrato, error = _contrato_o_error(id)
    if error:
        return error
    if not _es_parte(contrato):
        return _error('No tienes permiso para cancelar este contrato.', 403)
    if contrato.estado in ('finalizado', 'cancelado'):
        return _error('Este contrato ya está cerrado.', 409)

    datos = _datos_json()
    if not datos.get('confirmar'):
        return _error('Confirma la cancelación del contrato.', 422, {
            'confirmar': 'Debes confirmar la cancelación.',
        })

    contrato.estado = 'cancelado'
    db.session.commit()
    return _ok('Contrato cancelado.', contrato=_contrato_detalle(contrato))
