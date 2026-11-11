"""Reglas compartidas de comunicación. El llamador confirma la transacción."""

from datetime import datetime, timezone
from email_validator import EmailNotValidError, validate_email
from app.extensions import db
from app.auth.models import Usuario
from app.catalogo.models import SolicitudDemo
from app.contratos.models import Contrato
from app.comunicacion.models import Conversacion, Mensaje, Notificacion, Calificacion, Incidencia


class ErrorComunicacion(ValueError):
    def __init__(self, mensaje, status=400):
        super().__init__(mensaje)
        self.status = status


def texto_requerido(valor, campo, maximo):
    if not isinstance(valor, str) or not valor.strip():
        raise ErrorComunicacion(f'{campo} es obligatorio.')
    valor = valor.strip()
    if len(valor) > maximo:
        raise ErrorComunicacion(f'{campo} admite hasta {maximo} caracteres.')
    return valor


def verificar_participante(contrato, usuario):
    if usuario.id not in (contrato.id_cliente, contrato.id_desarrollador):
        raise ErrorComunicacion('No participas en este contrato.', 403)


def crear_notificacion(usuario, texto, link=None):
    """Acepta Usuario o ID. No hace commit: evento y aviso se guardan juntos."""
    usuario_id = usuario.id if isinstance(usuario, Usuario) else usuario
    if type(usuario_id) is not int or db.session.get(Usuario, usuario_id) is None:
        raise ErrorComunicacion('El destinatario no existe.', 404)
    texto = texto_requerido(texto, 'El texto', 5000)
    if link is not None and (
        not isinstance(link, str) or len(link) > 500 or not link.startswith('/')
        or link.startswith('//') or '\\' in link or any(ord(c) < 32 for c in link)
    ):
        raise ErrorComunicacion('El enlace debe ser una ruta interna válida.')
    notificacion = Notificacion(id_usuario=usuario_id, asunto=texto[:200], mensaje=texto, link=link)
    db.session.add(notificacion)
    return notificacion


def obtener_conversacion(contrato, usuario):
    verificar_participante(contrato, usuario)
    conversacion = db.session.scalar(
        db.select(Conversacion).filter_by(id_contrato=contrato.id).order_by(Conversacion.id)
    )
    if conversacion is None:
        conversacion = Conversacion(id_contrato=contrato.id)
        db.session.add(conversacion)
        db.session.flush()
    return conversacion


def enviar_mensaje(conversacion, usuario, contenido):
    contrato = conversacion.contrato
    verificar_participante(contrato, usuario)
    contenido = texto_requerido(contenido, 'El mensaje', 5000)
    receptor = contrato.id_desarrollador if usuario.id == contrato.id_cliente else contrato.id_cliente
    mensaje = Mensaje(id_conversacion=conversacion.id, id_emisor=usuario.id,
                      id_receptor=receptor, contenido=contenido)
    db.session.add(mensaje)
    crear_notificacion(receptor, f'Nuevo mensaje en contrato #{contrato.id}',
                       f'/comunicacion?tab=mensajes&contrato={contrato.id}')
    return mensaje


def registrar_calificacion(contrato, usuario, puntaje, comentarios=''):
    verificar_participante(contrato, usuario)
    if contrato.estado != 'finalizado':
        raise ErrorComunicacion('Solo se pueden calificar contratos finalizados.', 409)
    if type(puntaje) is not int or not 1 <= puntaje <= 5:
        raise ErrorComunicacion('El puntaje debe ser un entero entre 1 y 5.')
    if not isinstance(comentarios, str) or len(comentarios) > 2000:
        raise ErrorComunicacion('Los comentarios admiten hasta 2000 caracteres.')
    existente = db.session.scalar(db.select(Calificacion).filter_by(
        id_contrato=contrato.id, id_evaluador=usuario.id))
    if existente:
        raise ErrorComunicacion('Ya calificaste este contrato.', 409)
    evaluado = contrato.id_desarrollador if usuario.id == contrato.id_cliente else contrato.id_cliente
    calificacion = Calificacion(id_contrato=contrato.id, id_evaluador=usuario.id,
                               id_evaluado=evaluado, puntaje=puntaje, comentarios=comentarios.strip())
    db.session.add(calificacion)
    crear_notificacion(evaluado, f'Recibiste una calificación de {puntaje}/5 en contrato #{contrato.id}',
                       f'/comunicacion?tab=calificaciones&contrato={contrato.id}')
    return calificacion


def registrar_solicitud_demo(proyecto, usuario, nombre, correo):
    if usuario.tipo_usuario != 'cliente' or proyecto.id_usuario == usuario.id:
        raise ErrorComunicacion('Solo un cliente puede solicitar una demo a otro usuario.', 403)
    if not proyecto.demo_habilitada or proyecto.estado != 'activo':
        raise ErrorComunicacion('Este proyecto no tiene demos disponibles.', 409)
    nombre = texto_requerido(nombre, 'El nombre de contacto', 150)
    correo = texto_requerido(correo, 'El correo de contacto', 150)
    try:
        correo = validate_email(correo, check_deliverability=False).normalized
    except EmailNotValidError:
        raise ErrorComunicacion('El correo de contacto no es válido.')
    existente = db.session.scalar(db.select(SolicitudDemo).filter_by(
        id_producto=proyecto.id, id_cliente=usuario.id))
    if existente:
        raise ErrorComunicacion('Ya solicitaste una demo de este proyecto.', 409)
    solicitud = SolicitudDemo(id_producto=proyecto.id, id_cliente=usuario.id,
                             nombre_contacto=nombre, correo_contacto=correo)
    db.session.add(solicitud)
    crear_notificacion(proyecto.id_usuario, f'{nombre} solicitó una demo de {proyecto.titulo}',
                       '/comunicacion?tab=demos')
    return solicitud


def registrar_incidencia(usuario, tipo, descripcion, id_contrato=None):
    if tipo not in ('acoso', 'fraude', 'incumplimiento', 'bug', 'otro'):
        raise ErrorComunicacion('El tipo de incidencia no es válido.')
    descripcion = texto_requerido(descripcion, 'La descripción', 5000)
    if id_contrato is not None:
        if type(id_contrato) is not int or id_contrato < 1:
            raise ErrorComunicacion('El contrato indicado no es válido.')
        contrato = db.session.get(Contrato, id_contrato)
        if contrato is None:
            raise ErrorComunicacion('El contrato indicado no existe.', 404)
        verificar_participante(contrato, usuario)
    incidencia = Incidencia(id_usuario=usuario.id, tipo=tipo, descripcion=descripcion, id_contrato=id_contrato)
    db.session.add(incidencia)
    db.session.flush()
    admins = db.session.scalars(db.select(Usuario).filter_by(tipo_usuario='admin')).all()
    for admin in admins:
        crear_notificacion(admin, f'Nueva incidencia #{incidencia.id}: {tipo}',
                           '/comunicacion?tab=incidencias')
    return incidencia


def resolver_incidencia(incidencia, usuario, resolucion):
    if usuario.tipo_usuario != 'admin':
        raise ErrorComunicacion('Solo un administrador puede resolver incidencias.', 403)
    if incidencia.estado in ('resuelta', 'cerrada'):
        raise ErrorComunicacion('La incidencia ya está resuelta o cerrada.', 409)
    incidencia.resolucion = texto_requerido(resolucion, 'La resolución', 5000)
    incidencia.estado = 'resuelta'
    incidencia.fecha_resolucion = datetime.now(timezone.utc).replace(tzinfo=None)
    incidencia.id_admin = usuario.id
    crear_notificacion(incidencia.id_usuario, f'Tu incidencia #{incidencia.id} ha sido resuelta.',
                       '/comunicacion?tab=incidencias')
    return incidencia
