from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.comunicacion import comunicacion_bp
from app.comunicacion.models import Conversacion, Mensaje, Notificacion, Calificacion, Incidencia
from app.comunicacion.forms import MensajeForm, CalificacionForm, IncidenciaForm
from app.contratos.models import Contrato
from app.extensions import db
from app.comunicacion.services import (
    crear_notificacion, ErrorComunicacion, registrar_calificacion,
    registrar_incidencia, resolver_incidencia as resolver_reporte,
    obtener_conversacion, enviar_mensaje,
)


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
    conversacion = obtener_conversacion(contrato, current_user)

    receptor_id = (
        contrato.id_desarrollador if current_user.id == contrato.id_cliente
        else contrato.id_cliente
    )

    form = MensajeForm()
    if form.validate_on_submit():
        try:
            enviar_mensaje(conversacion, current_user, form.contenido.data)
            db.session.commit()
            return redirect(url_for('comunicacion.chat_contrato', id=id))
        except ErrorComunicacion as error:
            db.session.rollback()
            flash(str(error), 'danger')

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
    if contrato and current_user.id not in (contrato.id_cliente, contrato.id_desarrollador):
        abort(403)
    if not contrato or contrato.estado != 'finalizado':
        flash('Solo se pueden calificar contratos finalizados.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=id))

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
        try:
            registrar_calificacion(contrato, current_user, form.puntaje.data, form.comentarios.data or '')
            db.session.commit()
            flash('Calificación enviada.', 'success')
            return redirect(url_for('contratos.ver_contrato', id=id))
        except ErrorComunicacion as error:
            db.session.rollback()
            flash(str(error), 'danger')
    return render_template('comunicacion/calificar.html', form=form, contrato=contrato)


# ── Incidencias ──
@comunicacion_bp.route('/incidencia/nueva', methods=['GET', 'POST'])
@login_required
def nueva_incidencia():
    form = IncidenciaForm()
    contratos = db.session.execute(
        db.select(Contrato).filter(or_(
            Contrato.id_cliente == current_user.id,
            Contrato.id_desarrollador == current_user.id,
        )).order_by(Contrato.fecha_creacion.desc())
    ).scalars().all()
    form.id_contrato.choices = [(0, 'Sin contrato relacionado')] + [
        (c.id, f'Contrato #{c.id} — {c.objeto}') for c in contratos
    ]
    if form.validate_on_submit():
        try:
            registrar_incidencia(current_user, form.tipo.data, form.descripcion.data, form.id_contrato.data or None)
            db.session.commit()
            flash('Incidencia reportada.', 'success')
            return redirect(url_for('comunicacion.lista_incidencias'))
        except ErrorComunicacion as error:
            db.session.rollback()
            flash(str(error), 'danger')
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
    if request.method == 'POST':
        try:
            resolver_reporte(incidencia, current_user, request.form.get('resolucion', ''))
            db.session.commit()
            flash('Incidencia resuelta.', 'success')
        except ErrorComunicacion as error:
            db.session.rollback()
            flash(str(error), 'danger')
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
