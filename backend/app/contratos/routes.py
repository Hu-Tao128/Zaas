import hashlib
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.contratos import contratos_bp
from app.contratos.models import Contrato, PlantillaContrato, Entregable, Aceptacion
from app.contratos.forms import ContratoForm, EntregableForm
from app.extensions import db


def _get_client_ip():
    return request.headers.get('X-Forwarded-For', request.remote_addr)


@contratos_bp.route('/')
@login_required
def listar_contratos():
    contratos = db.session.execute(
        db.select(Contrato).filter(
            (Contrato.id_cliente == current_user.id) |
            (Contrato.id_desarrollador == current_user.id)
        ).order_by(Contrato.fecha_creacion.desc())
    ).scalars().all()
    return render_template('contratos/listar.html', contratos=contratos)


@contratos_bp.route('/<int:id>')
@login_required
def ver_contrato(id):
    contrato = db.session.get(Contrato, id)
    if not contrato or not _puede_ver_contrato(contrato):
        abort(403)
    return render_template('contratos/ver.html', contrato=contrato)


@contratos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_contrato():
    form = ContratoForm()
    if form.validate_on_submit():
        contrato = Contrato(
            id_cliente=form.id_cliente.data,
            id_desarrollador=form.id_desarrollador.data,
            id_producto=form.id_producto.data or None,
            id_encargo=form.id_encargo.data or None,
            costo_acordado=form.costo_acordado.data,
            terminos_condiciones=form.terminos_condiciones.data,
            estado='borrador'
        )
        db.session.add(contrato)
        db.session.commit()
        flash('Contrato creado como borrador.', 'success')
        return redirect(url_for('contratos.ver_contrato', id=contrato.id))
    return render_template('contratos/form.html', form=form)


@contratos_bp.route('/<int:id>/aceptar', methods=['POST'])
@login_required
def aceptar_contrato(id):
    contrato = db.session.get(Contrato, id)
    if not contrato or not _puede_ver_contrato(contrato):
        abort(403)
    if contrato.estado not in ('borrador', 'pendiente'):
        flash('Este contrato no puede ser aceptado en su estado actual.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=id))

    firma_hash = hashlib.sha256(
        f'{current_user.id}:{contrato.id}:{datetime.utcnow().isoformat()}:{_get_client_ip()}'.encode()
    ).hexdigest()[:16]

    if current_user.id == contrato.id_cliente:
        contrato.firma_cliente = firma_hash
    elif current_user.id == contrato.id_desarrollador:
        contrato.firma_desarrollador = firma_hash
    else:
        abort(403)

    aceptacion = Aceptacion(
        id_contrato=id,
        id_usuario=current_user.id,
        ip=_get_client_ip()
    )
    db.session.add(aceptacion)

    if contrato.firma_cliente and contrato.firma_desarrollador:
        contrato.estado = 'aceptado'
    elif contrato.estado == 'borrador':
        contrato.estado = 'pendiente'

    db.session.commit()
    flash('Contrato aceptado exitosamente.', 'success')
    return redirect(url_for('contratos.ver_contrato', id=id))


@contratos_bp.route('/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar_contrato(id):
    contrato = db.session.get(Contrato, id)
    if not contrato or not _puede_ver_contrato(contrato):
        abort(403)
    if contrato.estado in ('finalizado', 'cancelado'):
        flash('Este contrato ya está cerrado.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=id))
    contrato.estado = 'cancelado'
    db.session.commit()
    flash('Contrato cancelado.', 'info')
    return redirect(url_for('contratos.ver_contrato', id=id))


@contratos_bp.route('/<int:id>/entregable/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_entregable(id):
    contrato = db.session.get(Contrato, id)
    if not contrato or contrato.id_desarrollador != current_user.id:
        abort(403)
    form = EntregableForm()
    if form.validate_on_submit():
        entregable = Entregable(
            id_contrato=id,
            titulo=form.titulo.data,
            descripcion=form.descripcion.data,
            url_archivo=form.url_archivo.data
        )
        db.session.add(entregable)
        if contrato.estado == 'aceptado':
            contrato.estado = 'en_progreso'
        db.session.commit()
        flash('Entregable subido.', 'success')
        return redirect(url_for('contratos.ver_contrato', id=id))
    return render_template('contratos/entregable_form.html', form=form, contrato=contrato)


@contratos_bp.route('/entregable/<int:id>/revisar', methods=['POST'])
@login_required
def revisar_entregable(id):
    entregable = db.session.get(Entregable, id)
    if not entregable:
        abort(404)
    contrato = db.session.get(Contrato, entregable.id_contrato)
    if not contrato or contrato.id_cliente != current_user.id:
        abort(403)
    if entregable.estado != 'pendiente':
        flash('Este entregable ya fue revisado.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=contrato.id))

    accion = request.form.get('accion')  # 'aprobar' o 'rechazar'
    comentario = request.form.get('comentario', '')
    entregable.comentario_revision = comentario
    entregable.fecha_revision = datetime.utcnow()

    if accion == 'aprobar':
        entregable.estado = 'aprobado'
        contrato.estado = 'entregado'
        flash('Entregable aprobado.', 'success')
    elif accion == 'rechazar':
        entregable.estado = 'rechazado'
        flash('Entregable rechazado. El desarrollador debe corregirlo.', 'warning')
    else:
        flash('Acción no válida.', 'danger')
        return redirect(url_for('contratos.ver_contrato', id=contrato.id))

    db.session.commit()
    return redirect(url_for('contratos.ver_contrato', id=contrato.id))


def _puede_ver_contrato(contrato):
    return (
        current_user.id == contrato.id_cliente or
        current_user.id == contrato.id_desarrollador or
        current_user.tipo_usuario == 'admin'
    )
