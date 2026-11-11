"""API JSON para React; usa la sesión Flask y CSRF en las escrituras."""

from flask import Blueprint, jsonify, request
from flask_login import current_user
from flask_wtf.csrf import generate_csrf, validate_csrf
from wtforms.validators import ValidationError
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from app.extensions import db
from app.contratos.models import Contrato
from app.catalogo.models import OfertaTrabajo, Proyecto, SolicitudDemo
from app.comunicacion.models import Conversacion, Mensaje, Notificacion, Calificacion, Incidencia
from app.comunicacion.services import (
    ErrorComunicacion, verificar_participante, obtener_conversacion, enviar_mensaje,
    registrar_calificacion, registrar_solicitud_demo, registrar_incidencia, resolver_incidencia,
)

comunicacion_api = Blueprint('comunicacion_api', __name__, url_prefix='/api/comunicacion')


@comunicacion_api.before_request
def proteger_api():
    if request.method == 'OPTIONS':
        return None
    if not current_user.is_authenticated:
        raise ErrorComunicacion('Debes iniciar sesión.', 401)
    if request.method not in ('GET', 'HEAD'):
        try:
            validate_csrf(request.headers.get('X-CSRFToken'))
        except ValidationError:
            raise ErrorComunicacion('La protección de sesión expiró. Recarga la página.', 400)


@comunicacion_api.errorhandler(ErrorComunicacion)
def error_comunicacion(error):
    db.session.rollback()
    return jsonify(error=str(error)), error.status


@comunicacion_api.errorhandler(HTTPException)
def error_http(error):
    db.session.rollback()
    return jsonify(error=error.description), error.code


@comunicacion_api.errorhandler(SQLAlchemyError)
def error_db(error):
    from flask import current_app
    db.session.rollback()
    current_app.logger.exception('Error de persistencia en comunicación')
    return jsonify(error='No se pudieron guardar o consultar los datos.'), 500


def datos_json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ErrorComunicacion('Envía un objeto JSON válido.')
    return data


def obtener(modelo, id):
    registro = db.session.get(modelo, id)
    if registro is None:
        raise ErrorComunicacion('El registro no existe.', 404)
    return registro


def fecha(valor):
    return valor.isoformat() + 'Z' if valor else None


def persona(usuario):
    return {'id': usuario.id, 'nombre': f'{usuario.nombres} {usuario.apellido_paterno}'.strip()}


def contrato_json(contrato):
    otro = contrato.desarrollador if current_user.id == contrato.id_cliente else contrato.cliente
    return {'id': contrato.id, 'estado': contrato.estado, 'contraparte': persona(otro)}


def mensaje_json(mensaje):
    return {campo: getattr(mensaje, campo) for campo in
            ('id', 'id_conversacion', 'id_emisor', 'id_receptor', 'contenido', 'leido')} | {
                'fecha_hora': fecha(mensaje.fecha_hora),
                'emisor': {'nombre_completo': mensaje.emisor.nombre_completo} if mensaje.emisor else None}


def notificacion_json(notificacion):
    return {campo: getattr(notificacion, campo) for campo in
            ('id', 'asunto', 'mensaje', 'leido', 'link')} | {
                'fecha_hora_creacion': fecha(notificacion.fecha_hora_creacion)}


def demo_json(solicitud):
    return {'id': solicitud.id, 'id_producto': solicitud.id_producto,
            'proyecto': solicitud.producto.titulo, 'id_cliente': solicitud.id_cliente,
            'id_autor': solicitud.producto.id_usuario,
            'nombre_contacto': solicitud.nombre_contacto, 'correo_contacto': solicitud.correo_contacto,
            'fecha_solicitud': fecha(solicitud.fecha_solicitud)}


def calificacion_json(calificacion):
    return {campo: getattr(calificacion, campo) for campo in
            ('id', 'id_contrato', 'id_evaluador', 'id_evaluado', 'puntaje', 'comentarios')} | {
                'evaluador': persona(calificacion.evaluador),
                'evaluado': persona(calificacion.evaluado), 'fecha_hora': fecha(calificacion.fecha_hora)}


def incidencia_json(incidencia):
    return {campo: getattr(incidencia, campo) for campo in
            ('id', 'id_usuario', 'tipo', 'descripcion', 'estado', 'resolucion', 'id_admin', 'id_contrato')} | {
                'fecha_hora': fecha(incidencia.fecha_hora),
                'fecha_resolucion': fecha(incidencia.fecha_resolucion),
                'contrato_objeto': incidencia.contrato.objeto if incidencia.contrato else None}


def paginar(query, serializar, **extra):
    try:
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 20))
    except ValueError:
        raise ErrorComunicacion('La paginación debe usar números enteros.')
    if page < 1 or not 1 <= per_page <= 100:
        raise ErrorComunicacion('Usa page >= 1 y per_page entre 1 y 100.')
    pagina = db.paginate(query, page=page, per_page=per_page, error_out=False)
    return jsonify(data=[serializar(item) for item in pagina.items],
                   meta={'page': page, 'per_page': per_page, 'total': pagina.total,
                         'pages': pagina.pages, 'has_next': pagina.has_next}, **extra)


@comunicacion_api.get('/sesion')
def sesion():
    return jsonify(data=persona(current_user) | {'email': current_user.email,
                   'tipo_usuario': current_user.tipo_usuario}, csrf_token=generate_csrf())


@comunicacion_api.get('/admin/resumen')
def resumen_admin():
    if current_user.tipo_usuario != 'admin':
        raise ErrorComunicacion('Solo un administrador puede ingresar a este panel.', 403)
    por_estado = dict(db.session.execute(db.select(
        Incidencia.estado, db.func.count(Incidencia.id)).group_by(Incidencia.estado)).all())
    recientes = db.session.scalars(db.select(Incidencia).order_by(Incidencia.id.desc()).limit(5)).all()
    return jsonify(data={
        'usuario': persona(current_user) | {'tipo_usuario': current_user.tipo_usuario},
        'incidencias': {
            'total': sum(por_estado.values()),
            'pendientes': sum(por_estado.get(estado, 0) for estado in ('abierta', 'en_proceso')),
            'resueltas': sum(por_estado.get(estado, 0) for estado in ('resuelta', 'cerrada')),
        },
        'recientes': [incidencia_json(item) for item in recientes],
    })


@comunicacion_api.get('/admin/catalogo')
def catalogo_admin():
    if current_user.tipo_usuario != 'admin':
        raise ErrorComunicacion('Solo un administrador puede consultar este catálogo.', 403)

    tipo = request.args.get('tipo', 'proyectos')
    if tipo not in ('proyectos', 'ofertas'):
        raise ErrorComunicacion('Elige proyectos u ofertas.')
    es_proyecto = tipo == 'proyectos'
    modelo = Proyecto if es_proyecto else OfertaTrabajo
    estados = ('activo', 'cerrado') if es_proyecto else ('abierto', 'en_progreso', 'cerrado')
    estado = request.args.get('estado', '')
    if estado and estado not in estados:
        raise ErrorComunicacion('El estado seleccionado no corresponde al tipo de publicación.')

    conteos = {}
    for nombre, tabla in (('proyectos', Proyecto), ('ofertas', OfertaTrabajo)):
        por_estado = {estado or 'sin_estado': cantidad for estado, cantidad in db.session.execute(
            db.select(tabla.estado, db.func.count(tabla.id)).group_by(tabla.estado)
        )}
        conteos[nombre] = {'total': sum(por_estado.values()), 'estados': por_estado}

    relacion = Proyecto.autor if es_proyecto else OfertaTrabajo.cliente
    query = db.select(modelo).options(selectinload(relacion))
    if estado:
        query = query.where(modelo.estado == estado)

    def serializar(publicacion):
        responsable = publicacion.autor if es_proyecto else publicacion.cliente
        return {
            'id': publicacion.id,
            'titulo': publicacion.titulo,
            'responsable': persona(responsable) if responsable else None,
            'estado': publicacion.estado,
            'monto': publicacion.precio if es_proyecto else publicacion.presupuesto,
            'fecha_publicacion': fecha(publicacion.fecha_publicacion),
        }

    return paginar(query.order_by(modelo.fecha_publicacion.desc(), modelo.id.desc()),
                   serializar, conteos=conteos)


@comunicacion_api.get('/contratos')
def contratos():
    query = db.select(Contrato).where(
        (Contrato.id_cliente == current_user.id) | (Contrato.id_desarrollador == current_user.id))
    return paginar(query.order_by(Contrato.id.desc()), contrato_json)


@comunicacion_api.get('/conversaciones')
def conversaciones():
    query = db.select(Conversacion).join(Contrato).where(
        (Contrato.id_cliente == current_user.id) | (Contrato.id_desarrollador == current_user.id))
    def serializar(item):
        no_leidos = db.session.scalar(db.select(db.func.count(Mensaje.id)).where(
            Mensaje.id_conversacion == item.id, Mensaje.id_receptor == current_user.id,
            Mensaje.leido.is_(False)))
        return {'id': item.id, 'contrato': contrato_json(item.contrato),
                'no_leidos': no_leidos, 'fecha_creacion': fecha(item.fecha_creacion)}
    return paginar(query.order_by(Conversacion.id.desc()), serializar)


@comunicacion_api.post('/contratos/<int:id>/conversacion')
def abrir_conversacion(id):
    conversacion = obtener_conversacion(obtener(Contrato, id), current_user)
    db.session.commit()
    return jsonify(data={'id': conversacion.id, 'contrato': contrato_json(conversacion.contrato)})


@comunicacion_api.get('/contratos/<int:id>/mensajes')
def mensajes_del_contrato(id):
    contrato = obtener(Contrato, id)
    verificar_participante(contrato, current_user)
    query = (db.select(Mensaje).join(Conversacion).options(selectinload(Mensaje.emisor))
             .where(Conversacion.id_contrato == id).order_by(Mensaje.id.desc()))
    return paginar(query, mensaje_json)


@comunicacion_api.route('/conversaciones/<int:id>/mensajes', methods=['GET', 'POST'])
def mensajes(id):
    conversacion = obtener(Conversacion, id)
    verificar_participante(conversacion.contrato, current_user)
    if request.method == 'POST':
        mensaje = enviar_mensaje(conversacion, current_user, datos_json().get('contenido'))
        db.session.commit()
        return jsonify(data=mensaje_json(mensaje)), 201
    query = db.select(Mensaje).filter_by(id_conversacion=id).order_by(Mensaje.id.desc())
    return paginar(query, mensaje_json)


@comunicacion_api.post('/conversaciones/<int:id>/leer')
def leer_mensajes(id):
    conversacion = obtener(Conversacion, id)
    verificar_participante(conversacion.contrato, current_user)
    resultado = db.session.execute(db.update(Mensaje).where(
        Mensaje.id_conversacion == id, Mensaje.id_receptor == current_user.id,
        Mensaje.leido.is_(False)).values(leido=True))
    db.session.commit()
    return jsonify(data={'actualizados': resultado.rowcount})


@comunicacion_api.get('/notificaciones')
def notificaciones():
    query = db.select(Notificacion).filter_by(id_usuario=current_user.id)
    total_no_leidas = db.session.scalar(db.select(db.func.count(Notificacion.id)).where(
        Notificacion.id_usuario == current_user.id, Notificacion.leido.is_(False)))
    if request.args.get('solo_no_leidas') == 'true':
        query = query.where(Notificacion.leido.is_(False))
    return paginar(query.order_by(Notificacion.id.desc()), notificacion_json, no_leidas=total_no_leidas)


@comunicacion_api.patch('/notificaciones/<int:id>/leer')
def leer_notificacion(id):
    notificacion = obtener(Notificacion, id)
    if notificacion.id_usuario != current_user.id:
        raise ErrorComunicacion('No puedes modificar esta notificación.', 403)
    notificacion.leido = True
    db.session.commit()
    return jsonify(data=notificacion_json(notificacion))


@comunicacion_api.post('/notificaciones/leer')
def leer_notificaciones():
    resultado = db.session.execute(db.update(Notificacion).where(
        Notificacion.id_usuario == current_user.id, Notificacion.leido.is_(False)).values(leido=True))
    db.session.commit()
    return jsonify(data={'actualizados': resultado.rowcount})


@comunicacion_api.get('/proyectos-demo')
def proyectos_demo():
    query = db.select(Proyecto).where(Proyecto.demo_habilitada.is_(True),
                                     Proyecto.estado == 'activo', Proyecto.id_usuario != current_user.id)
    return paginar(query.order_by(Proyecto.id.desc()), lambda p: {
        'id': p.id, 'titulo': p.titulo, 'autor': persona(p.autor)})


@comunicacion_api.get('/solicitudes-demo')
def solicitudes_demo():
    query = db.select(SolicitudDemo).join(Proyecto).where(
        (SolicitudDemo.id_cliente == current_user.id) | (Proyecto.id_usuario == current_user.id))
    return paginar(query.order_by(SolicitudDemo.id.desc()), demo_json)


@comunicacion_api.post('/proyectos/<int:id>/solicitudes-demo')
def solicitar_demo(id):
    data = datos_json()
    solicitud = registrar_solicitud_demo(obtener(Proyecto, id), current_user,
                                        data.get('nombre_contacto'), data.get('correo_contacto'))
    db.session.commit()
    return jsonify(data=demo_json(solicitud)), 201


@comunicacion_api.get('/calificaciones')
def calificaciones():
    query = db.select(Calificacion).where(
        (Calificacion.id_evaluador == current_user.id) | (Calificacion.id_evaluado == current_user.id))
    return paginar(query.order_by(Calificacion.id.desc()), calificacion_json)


@comunicacion_api.post('/contratos/<int:id>/calificaciones')
def calificar(id):
    data = datos_json()
    calificacion = registrar_calificacion(obtener(Contrato, id), current_user,
                                          data.get('puntaje'), data.get('comentarios', ''))
    db.session.commit()
    return jsonify(data=calificacion_json(calificacion)), 201


@comunicacion_api.route('/incidencias', methods=['GET', 'POST'])
def incidencias():
    if request.method == 'POST':
        data = datos_json()
        incidencia = registrar_incidencia(current_user, data.get('tipo'), data.get('descripcion'),
                                          data.get('id_contrato'))
        db.session.commit()
        return jsonify(data=incidencia_json(incidencia)), 201
    query = db.select(Incidencia)
    # La vista provisional siempre muestra los reportes propios.
    if request.args.get('todas') == 'true':
        if current_user.tipo_usuario != 'admin':
            raise ErrorComunicacion('Solo un administrador puede consultar todos los reportes.', 403)
    else:
        query = query.where(Incidencia.id_usuario == current_user.id)
    return paginar(query.order_by(Incidencia.id.desc()), incidencia_json)


@comunicacion_api.get('/incidencias/<int:id>')
def ver_incidencia(id):
    incidencia = obtener(Incidencia, id)
    if incidencia.id_usuario != current_user.id and current_user.tipo_usuario != 'admin':
        raise ErrorComunicacion('No puedes consultar esta incidencia.', 403)
    return jsonify(data=incidencia_json(incidencia))


@comunicacion_api.patch('/incidencias/<int:id>/resolver')
def resolver(id):
    incidencia = resolver_incidencia(obtener(Incidencia, id), current_user,
                                    datos_json().get('resolucion'))
    db.session.commit()
    return jsonify(data=incidencia_json(incidencia))
