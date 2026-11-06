from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.comunicacion import comunicacion_bp
from app.comunicacion.models import Conversacion, Mensaje, Notificacion, Calificacion, Incidencia
from app.comunicacion.forms import MensajeForm, CalificacionForm, IncidenciaForm
from app.contratos.models import Contrato
from app.auth.models import Usuario
from app.extensions import db


# ── Función central para crear notificaciones ──
def crear_notificacion(usuario_id, texto, link=None):
    """Crear una notificación para un usuario. Llamar desde cualquier módulo."""
    notif = Notificacion(
        id_usuario=usuario_id,
        asunto=texto[:200],
        mensaje=texto,
        link=link
    )
    db.session.add(notif)
    db.session.commit()
    return notif


# ── Mensajería ──
@comunicacion_bp.route('/')
@login_required
def lista_conversaciones():
    conversaciones = db.session.execute(
        db.select(Conversacion)
        .join(Contrato)
        .filter(
            (Contrato.id_cliente == current_user.id) |
            (Contrato.id_desarrollador == current_user.id)
        )
        .order_by(Conversacion.fecha_creacion.desc())
    ).scalars().all()
    return render_template('comunicacion/conversaciones.html', conversaciones=conversaciones)


@comunicacion_bp.route('/contrato/<int:id>', methods=['GET', 'POST'])
@login_required
def chat_contrato(id):
    contrato = db.session.get(Contrato, id)
    if not contrato or not (
        current_user.id == contrato.id_cliente or
        current_user.id == contrato.id_desarrollador
    ):
        abort(403)

    # Buscar o crear conversación
    conversacion = db.session.execute(
        db.select(Conversacion).filter_by(id_contrato=id)
    ).scalar_one_or_none()
    if not conversacion:
        conversacion = Conversacion(id_contrato=id)
        db.session.add(conversacion)
        db.session.commit()

    receptor_id = (
        contrato.id_desarrollador if current_user.id == contrato.id_cliente
        else contrato.id_cliente
    )

    form = MensajeForm()
    if form.validate_on_submit():
        mensaje = Mensaje(
            id_conversacion=conversacion.id,
            id_emisor=current_user.id,
            id_receptor=receptor_id,
            contenido=form.contenido.data
        )
        db.session.add(mensaje)
        crear_notificacion(receptor_id, f'Nuevo mensaje en contrato #{id}', link=url_for('comunicacion.chat_contrato', id=id))
        db.session.commit()
        return redirect(url_for('comunicacion.chat_contrato', id=id))

    mensajes = db.session.execute(
        db.select(Mensaje).filter_by(id_conversacion=conversacion.id).order_by(Mensaje.fecha_hora)
    ).scalars().all()

    # Marcar como leídos
    for m in mensajes:
        if m.id_receptor == current_user.id and not m.leido:
            m.leido = True
    db.session.commit()

    return render_template('comunicacion/chat.html', form=form, mensajes=mensajes, contrato=contrato, receptor_id=receptor_id)


# ── Notificaciones ──
@comunicacion_bp.route('/notificaciones')
@login_required
def ver_notificaciones():
    notificaciones = db.session.execute(
        db.select(Notificacion).filter_by(id_usuario=current_user.id).order_by(Notificacion.fecha_hora_creacion.desc()).limit(50)
    ).scalars().all()
    return render_template('comunicacion/notificaciones.html', notificaciones=notificaciones)


@comunicacion_bp.route('/notificaciones/marcar-leidas', methods=['POST'])
@login_required
def marcar_leidas():
    db.session.execute(
        db.update(Notificacion)
        .where(Notificacion.id_usuario == current_user.id)
        .values(leido=True)
    )
    db.session.commit()
    return redirect(url_for('comunicacion.ver_notificaciones'))


# ── Calificaciones ──
@comunicacion_bp.route('/contrato/<int:id>/calificar', methods=['GET', 'POST'])
@login_required
def calificar_contrato(id):
    contrato = db.session.get(Contrato, id)
    if not contrato or contrato.estado != 'finalizado':
        flash('Solo se pueden calificar contratos finalizados.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=id))

    evaluado_id = (
        contrato.id_desarrollador if current_user.id == contrato.id_cliente
        else contrato.id_cliente
    )

    # Verificar que ya no haya calificado
    ya_califico = db.session.execute(
        db.select(Calificacion).filter_by(
            id_contrato=id,
            id_evaluador=current_user.id
        )
    ).scalar_one_or_none()
    if ya_califico:
        flash('Ya calificaste este contrato.', 'info')
        return redirect(url_for('contratos.ver_contrato', id=id))

    form = CalificacionForm()
    if form.validate_on_submit():
        calificacion = Calificacion(
            id_contrato=id,
            id_evaluador=current_user.id,
            id_evaluado=evaluado_id,
            puntaje=form.puntaje.data,
            comentarios=form.comentarios.data
        )
        db.session.add(calificacion)
        crear_notificacion(evaluado_id, f'Recibiste una calificación de {form.puntaje.data}/5 en contrato #{id}', link=url_for('auth.ver_perfil', id=evaluado_id))
        db.session.commit()
        flash('Calificación enviada.', 'success')
        return redirect(url_for('contratos.ver_contrato', id=id))
    return render_template('comunicacion/calificar.html', form=form, contrato=contrato)


# ── Incidencias ──
@comunicacion_bp.route('/incidencia/nueva', methods=['GET', 'POST'])
@login_required
def nueva_incidencia():
    form = IncidenciaForm()
    if form.validate_on_submit():
        incidencia = Incidencia(
            id_usuario=current_user.id,
            tipo=form.tipo.data,
            descripcion=form.descripcion.data
        )
        db.session.add(incidencia)
        # Notificar a admins
        admins = db.session.execute(
            db.select(Usuario).filter_by(tipo_usuario='admin')
        ).scalars().all()
        for admin in admins:
            crear_notificacion(admin.id, f'Nueva incidencia de {current_user.nombres}: {form.tipo.data}', link=url_for('comunicacion.ver_incidencia', id=incidencia.id))
        db.session.commit()
        flash('Incidencia reportada.', 'success')
        return redirect(url_for('comunicacion.lista_incidencias'))
    return render_template('comunicacion/incidencia_form.html', form=form)


@comunicacion_bp.route('/incidencias')
@login_required
def lista_incidencias():
    if current_user.tipo_usuario == 'admin':
        incidencias = db.session.execute(
            db.select(Incidencia).order_by(Incidencia.fecha_hora.desc())
        ).scalars().all()
    else:
        incidencias = db.session.execute(
            db.select(Incidencia).filter_by(id_usuario=current_user.id).order_by(Incidencia.fecha_hora.desc())
        ).scalars().all()
    return render_template('comunicacion/incidencias.html', incidencias=incidencias)


@comunicacion_bp.route('/incidencia/<int:id>/resolver', methods=['GET', 'POST'])
@login_required
def resolver_incidencia(id):
    if current_user.tipo_usuario != 'admin':
        abort(403)
    incidencia = db.session.get(Incidencia, id)
    if not incidencia:
        abort(404)
    resolucion = request.form.get('resolucion', '')
    incidencia.resolucion = resolucion
    incidencia.estado = 'resuelta'
    incidencia.fecha_resolucion = db.func.now()
    incidencia.id_admin = current_user.id
    db.session.commit()
    crear_notificacion(incidencia.id_usuario, f'Tu incidencia #{id} ha sido resuelta.', link=url_for('comunicacion.lista_incidencias'))
    flash('Incidencia resuelta.', 'success')
    return redirect(url_for('comunicacion.ver_incidencia', id=id))


@comunicacion_bp.route('/incidencia/<int:id>')
@login_required
def ver_incidencia(id):
    incidencia = db.session.get(Incidencia, id)
    if not incidencia:
        abort(404)
    if current_user.tipo_usuario != 'admin' and incidencia.id_usuario != current_user.id:
        abort(403)
    return render_template('comunicacion/ver_incidencia.html', incidencia=incidencia)
