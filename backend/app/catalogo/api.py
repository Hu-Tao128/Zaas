"""API JSON del catálogo, consumida por el frontend React.

Reutiliza la misma lógica (y las mismas operaciones atómicas) que las vistas HTML de
routes.py: cierre de ofertas, cerrojo de postulaciones, aceptar/rechazar. Todo cuelga de
/api/catalogo y usa la sesión de Flask-Login que crea /auth/callback.

Convenciones de respuesta:
  éxito  -> {"ok": true,  "mensaje": "...", ...datos}
  error  -> {"ok": false, "mensaje": "...", "errores": {"campo": "mensaje"}}
Las mutaciones exigen el token CSRF en la cabecera X-CSRFToken (se obtiene en GET /csrf).
"""
from datetime import datetime
from functools import wraps

from flask import Blueprint, jsonify, request
from flask_login import current_user
from flask_wtf.csrf import generate_csrf
from werkzeug.datastructures import MultiDict

from app.catalogo.forms import ProyectoForm, OfertaForm, PostulacionForm, DemoForm
from app.catalogo.models import (
    Proyecto, OfertaTrabajo, Postulacion, SolicitudDemo, Categoria, Tecnologia,
    CategoriaProyecto,
)
from app.catalogo.routes import (
    _aceptar_postulacion, _rechazar_postulacion, _cargar_opciones, _cerrar_oferta_atomico,
    _enviar_postulacion, _hay_aceptada, _motivo_oferta_no_abierta, _postulacion_de,
    _sincronizar_relaciones,
)
from app.extensions import db

catalogo_api_bp = Blueprint('catalogo_api', __name__, url_prefix='/api/catalogo')

POR_PAGINA = 12


# ---------------------------------------------------------------- utilidades

def _ok(mensaje=None, status=200, **datos):
    return jsonify({'ok': True, 'mensaje': mensaje, **datos}), status


def _error(mensaje, status=400, errores=None):
    return jsonify({'ok': False, 'mensaje': mensaje, 'errores': errores or {}}), status


def _requiere(*roles):
    """Exige sesión iniciada y, si se indican, que el rol sea uno de ellos (JSON, no redirect)."""
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


def _formdata(datos, *, bools=(), listas=()):
    """Convierte el JSON del cliente en el MultiDict de strings que esperan los campos WTForms."""
    md = MultiDict()
    for clave, valor in datos.items():
        if clave in listas:
            for item in valor or []:
                md.add(clave, str(item))
        elif clave in bools:
            if valor:
                md.add(clave, 'y')
        elif valor is not None:
            md.add(clave, str(valor))
    return md


def _errores_form(form):
    return {campo: msgs[0] for campo, msgs in form.errors.items() if msgs}


def _form_invalido(form):
    return _error('Revisa los campos del formulario.', 422, _errores_form(form))


def _pagina(paginacion, serializar):
    return {
        'items': [serializar(x) for x in paginacion.items],
        'page': paginacion.page,
        'pages': max(paginacion.pages, 1),
        'total': paginacion.total,
    }


# ------------------------------------------------------------- serializadores

def _usuario_publico(u):
    return {'id': u.id, 'nombres': u.nombres, 'apellido_paterno': u.apellido_paterno}


def _usuario_propio(u):
    return {
        **_usuario_publico(u),
        'email': getattr(u, 'email', None) or getattr(u, 'correo', None),
        'tipo_usuario': u.tipo_usuario,
    }


def _proyecto(p):
    return {
        'id': p.id,
        'id_usuario': p.id_usuario,
        'titulo': p.titulo,
        'descripcion': p.descripcion,
        'precio': p.precio,
        'demo_habilitada': bool(p.demo_habilitada),
        'fecha_publicacion': _iso(p.fecha_publicacion, utc=True),
        'estado': p.estado,
        'autor': _usuario_publico(p.autor),
        'categorias': [{'id': c.categoria.id, 'nombre': c.categoria.nombre} for c in p.categorias],
        'tecnologias': [{'id': t.tecnologia.id, 'nombre': t.tecnologia.nombre} for t in p.tecnologias],
    }


def _oferta(o):
    return {
        'id': o.id,
        'id_cliente': o.id_cliente,
        'titulo': o.titulo,
        'descripcion_requerimientos': o.descripcion_requerimientos,
        'presupuesto': o.presupuesto,
        'estado': o.estado,
        'fecha_publicacion': _iso(o.fecha_publicacion, utc=True),
        'fecha_entrega': _iso(o.fecha_entrega),
        'cliente': _usuario_publico(o.cliente),
        'num_postulaciones': len(o.postulaciones),
    }


def _postulacion(p):
    return {
        'id': p.id,
        'id_desarrollador': p.id_desarrollador,
        'id_oferta': p.id_oferta,
        'detalles': p.detalles,
        'costo_propuesto': p.costo_propuesto,
        'estado': p.estado,
        'fecha_hora': _iso(p.fecha_hora, utc=True),
        'desarrollador': _usuario_publico(p.desarrollador),
        'oferta': {
            'id': p.oferta.id,
            'titulo': p.oferta.titulo,
            'estado': p.oferta.estado,
            'id_cliente': p.oferta.id_cliente,
        },
    }


# ------------------------------------------------------------ sesión y opciones

@catalogo_api_bp.get('/csrf')
def csrf():
    return jsonify({'csrf_token': generate_csrf()})


@catalogo_api_bp.get('/me')
@_requiere()
def me():
    return jsonify({'usuario': _usuario_propio(current_user)})


@catalogo_api_bp.get('/opciones')
def opciones():
    categorias = db.session.execute(db.select(Categoria).order_by(Categoria.nombre)).scalars().all()
    tecnologias = db.session.execute(db.select(Tecnologia).order_by(Tecnologia.nombre)).scalars().all()
    return jsonify({
        'categorias': [{'id': c.id, 'nombre': c.nombre} for c in categorias],
        'tecnologias': [{'id': t.id, 'nombre': t.nombre} for t in tecnologias],
    })


# ------------------------------------------------------------------- proyectos

@catalogo_api_bp.get('/proyectos')
def listar_proyectos():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '', type=str).strip()
    categoria = request.args.get('categoria', type=int)

    query = db.select(Proyecto).filter_by(estado='activo').order_by(Proyecto.fecha_publicacion.desc())
    if q:
        query = query.filter(Proyecto.titulo.ilike(f'%{q}%'))
    if categoria:
        query = query.filter(Proyecto.categorias.any(CategoriaProyecto.id_categoria == categoria))
    return jsonify(_pagina(db.paginate(query, page=page, per_page=POR_PAGINA, error_out=False), _proyecto))


@catalogo_api_bp.get('/proyectos/<int:id>')
def detalle_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        return _error('Proyecto no encontrado.', 404)
    es_dueno = current_user.is_authenticated and current_user.id == proyecto.id_usuario
    return jsonify({'proyecto': _proyecto(proyecto), 'es_dueno': es_dueno})


@catalogo_api_bp.get('/mis-productos')
@_requiere('desarrollador')
def mis_productos():
    proyectos = db.session.execute(
        db.select(Proyecto).filter_by(id_usuario=current_user.id).order_by(Proyecto.fecha_publicacion.desc())
    ).scalars().all()
    return jsonify({'items': [_proyecto(p) for p in proyectos]})


def _guardar_proyecto(proyecto=None):
    """Valida el JSON y crea (proyecto=None) o actualiza un proyecto. Devuelve (proyecto, respuesta_error)."""
    form = ProyectoForm(
        formdata=_formdata(_datos_json(), bools=('demo_habilitada',),
                           listas=('categorias_ids', 'tecnologias_ids')),
        meta={'csrf': False},
    )
    _cargar_opciones(form)
    if not form.validate():
        return None, _form_invalido(form)
    if proyecto is None:
        proyecto = Proyecto(id_usuario=current_user.id, estado='activo')
        db.session.add(proyecto)
    proyecto.titulo = form.titulo.data.strip()
    proyecto.descripcion = form.descripcion.data.strip()
    proyecto.precio = form.precio.data
    proyecto.demo_habilitada = form.demo_habilitada.data
    _sincronizar_relaciones(proyecto, form.categorias_ids.data, form.tecnologias_ids.data)
    db.session.commit()
    return proyecto, None


@catalogo_api_bp.post('/proyectos')
@_requiere('desarrollador')
def crear_proyecto():
    proyecto, error = _guardar_proyecto()
    if error:
        return error
    return _ok('Proyecto publicado.', 201, proyecto=_proyecto(proyecto))


@catalogo_api_bp.put('/proyectos/<int:id>')
@_requiere('desarrollador')
def editar_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        return _error('Proyecto no encontrado.', 404)
    if proyecto.id_usuario != current_user.id:
        return _error('No tienes permiso para editar este proyecto.', 403)
    proyecto, error = _guardar_proyecto(proyecto)
    if error:
        return error
    return _ok('Proyecto actualizado.', proyecto=_proyecto(proyecto))


@catalogo_api_bp.post('/proyectos/<int:id>/cerrar')
@_requiere('desarrollador')
def cerrar_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        return _error('Proyecto no encontrado.', 404)
    if proyecto.id_usuario != current_user.id:
        return _error('No tienes permiso para cerrar este proyecto.', 403)
    if proyecto.estado == 'cerrado':
        return _error('El proyecto ya estaba cerrado.', 409)
    proyecto.estado = 'cerrado'
    db.session.commit()
    return _ok('Proyecto cerrado. Ya no aparece en el catálogo público.', proyecto=_proyecto(proyecto))


@catalogo_api_bp.post('/proyectos/<int:id>/demo')
@_requiere()
def solicitar_demo(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        return _error('Proyecto no encontrado.', 404)
    form = DemoForm(formdata=_formdata(_datos_json()), meta={'csrf': False})
    if not form.validate():
        return _form_invalido(form)
    db.session.add(SolicitudDemo(
        id_producto=id,
        id_cliente=current_user.id,
        nombre_contacto=form.nombre_contacto.data,
        correo_contacto=form.correo_contacto.data,
    ))
    db.session.commit()
    return _ok('Solicitud de demo enviada.', 201)


# ---------------------------------------------------------------------- ofertas

@catalogo_api_bp.get('/ofertas')
def listar_ofertas():
    page = request.args.get('page', 1, type=int)
    query = db.select(OfertaTrabajo).filter_by(estado='abierto').order_by(OfertaTrabajo.fecha_publicacion.desc())
    return jsonify(_pagina(db.paginate(query, page=page, per_page=POR_PAGINA, error_out=False), _oferta))


@catalogo_api_bp.get('/ofertas/<int:id>')
def detalle_oferta(id):
    oferta = db.session.get(OfertaTrabajo, id)
    if not oferta:
        return _error('Oferta no encontrada.', 404)
    es_dueno = current_user.is_authenticated and current_user.id == oferta.id_cliente
    mi_postulacion = None
    if current_user.is_authenticated and current_user.tipo_usuario == 'desarrollador':
        existente = _postulacion_de(current_user.id, id)
        if existente:
            mi_postulacion = {'id': existente.id, 'estado': existente.estado}
    datos = {'oferta': _oferta(oferta), 'es_dueno': es_dueno, 'mi_postulacion': mi_postulacion}
    if es_dueno:
        recibidas = sorted(oferta.postulaciones, key=lambda p: p.fecha_hora or datetime.min, reverse=True)
        datos['postulaciones'] = [_postulacion(p) for p in recibidas]
    return jsonify(datos)


@catalogo_api_bp.get('/mis-ofertas')
@_requiere('cliente')
def mis_ofertas():
    ofertas = db.session.execute(
        db.select(OfertaTrabajo).filter_by(id_cliente=current_user.id)
        .order_by(OfertaTrabajo.fecha_publicacion.desc())
    ).scalars().all()
    return jsonify({'items': [_oferta(o) for o in ofertas]})


@catalogo_api_bp.post('/ofertas')
@_requiere('cliente')
def crear_oferta():
    form = OfertaForm(formdata=_formdata(_datos_json()), meta={'csrf': False})
    if not form.validate():
        return _form_invalido(form)
    oferta = OfertaTrabajo(
        id_cliente=current_user.id,
        titulo=form.titulo.data.strip(),
        descripcion_requerimientos=form.descripcion.data.strip(),
        presupuesto=form.presupuesto.data,
        fecha_entrega=form.fecha_entrega.data,
        estado='abierto',
    )
    db.session.add(oferta)
    db.session.commit()
    return _ok('Oferta publicada.', 201, oferta=_oferta(oferta))


@catalogo_api_bp.post('/ofertas/<int:id>/cerrar')
@_requiere('cliente')
def cerrar_oferta(id):
    oferta = db.session.get(OfertaTrabajo, id)
    if not oferta:
        return _error('Oferta no encontrada.', 404)
    if oferta.id_cliente != current_user.id:
        return _error('No tienes permiso para cerrar esta oferta.', 403)
    ok, _nivel, mensaje = _cerrar_oferta_atomico(id, current_user.id)
    if not ok:
        return _error(mensaje, 409)
    return _ok(mensaje, oferta=_oferta(db.session.get(OfertaTrabajo, id)))


# ---------------------------------------------------------------- postulaciones

@catalogo_api_bp.post('/ofertas/<int:id>/postular')
@_requiere('desarrollador')
def postular(id):
    oferta = db.session.get(OfertaTrabajo, id)
    if not oferta:
        return _error('Oferta no encontrada.', 404)
    existente = _postulacion_de(current_user.id, id)
    if existente:
        return _error('Ya te postulaste a esta oferta.', 409, {'id_postulacion': existente.id})
    if oferta.estado != 'abierto' or _hay_aceptada(id):
        return _error(_motivo_oferta_no_abierta(oferta.estado if oferta.estado != 'abierto' else 'en_progreso'), 409)
    form = PostulacionForm(formdata=_formdata(_datos_json()), meta={'csrf': False})
    if not form.validate():
        return _form_invalido(form)
    ok, _nivel, mensaje, _destino = _enviar_postulacion(
        current_user.id, id, form.detalles.data.strip(), form.costo_propuesto.data)
    if not ok:
        return _error(mensaje, 409)
    return _ok(mensaje, 201, postulacion=_postulacion(_postulacion_de(current_user.id, id)))


@catalogo_api_bp.get('/mis-postulaciones')
@_requiere('desarrollador')
def mis_postulaciones():
    postulaciones = db.session.execute(
        db.select(Postulacion).filter_by(id_desarrollador=current_user.id)
        .order_by(Postulacion.fecha_hora.desc())
    ).scalars().all()
    return jsonify({'items': [_postulacion(p) for p in postulaciones]})


@catalogo_api_bp.get('/postulaciones/<int:id>')
@_requiere()
def detalle_postulacion(id):
    postulacion = db.session.get(Postulacion, id)
    if not postulacion:
        return _error('Postulación no encontrada.', 404)
    es_cliente = postulacion.oferta.id_cliente == current_user.id
    if not es_cliente and postulacion.id_desarrollador != current_user.id:
        return _error('No tienes permiso para ver esta postulación.', 403)
    return jsonify({'postulacion': _postulacion(postulacion), 'es_cliente': es_cliente})


def _resolver(id, nuevo_estado):
    postulacion = db.session.get(Postulacion, id)
    if not postulacion:
        return _error('Postulación no encontrada.', 404)
    oferta = postulacion.oferta
    if oferta.id_cliente != current_user.id:
        return _error('No tienes permiso para gestionar esta postulación.', 403)
    if postulacion.estado != 'pendiente':
        return _error('Esta postulación ya fue resuelta y no puede cambiarse.', 409)
    id_oferta, id_cliente = oferta.id, current_user.id
    if nuevo_estado == 'aceptada':
        ok, mensaje = _aceptar_postulacion(id, id_oferta, id_cliente)
    else:
        ok, mensaje = _rechazar_postulacion(id)
    if not ok:
        return _error(mensaje, 409)
    db.session.expire_all()
    return _ok(mensaje, postulacion=_postulacion(db.session.get(Postulacion, id)))


@catalogo_api_bp.post('/postulaciones/<int:id>/aceptar')
@_requiere('cliente')
def aceptar_postulacion(id):
    return _resolver(id, 'aceptada')


@catalogo_api_bp.post('/postulaciones/<int:id>/rechazar')
@_requiere('cliente')
def rechazar_postulacion(id):
    return _resolver(id, 'rechazada')
