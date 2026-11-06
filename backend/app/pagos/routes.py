import uuid
from datetime import datetime
from flask import render_template, redirect, url_for, request, flash, abort
from flask_login import login_required, current_user
from app.pagos import pagos_bp
from app.pagos.models import Pago, Liberacion, Recibo, Disputa, Arbitraje
from app.pagos.forms import PagoForm, DisputaForm, ArbitrajeForm
from app.contratos.models import Contrato, Entregable
from app.extensions import db


@pagos_bp.route('/contrato/<int:id>/pagar', methods=['GET', 'POST'])
@login_required
def pagar_contrato(id):
    """Simula un pago: el cliente deposita fondos al escrow del contrato."""
    contrato = db.session.get(Contrato, id)
    if not contrato or contrato.id_cliente != current_user.id:
        abort(403)
    if contrato.estado not in ('aceptado', 'en_progreso'):
        flash('Este contrato no está listo para pago.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=id))

    # Verificar que ya exista un pago
    pago_existente = db.session.execute(
        db.select(Pago).filter_by(id_contrato=id)
    ).scalar_one_or_none()
    if pago_existente:
        flash('Ya existe un pago para este contrato.', 'warning')
        return redirect(url_for('pagos.ver_recibo', id=pago_existente.id))

    form = PagoForm()
    if form.validate_on_submit():
        pago = Pago(
            id_contrato=id,
            monto=contrato.costo_acordado,
            estado_escrow='retenido'
        )
        db.session.add(pago)
        db.session.commit()

        # Generar recibo
        folio = f'ZAS-{datetime.utcnow().strftime("%Y%m%d")}-{str(uuid.uuid4())[:8].upper()}'
        recibo = Recibo(
            id_pago=pago.id,
            folio=folio,
            contenido_html=_generar_html_recibo(pago, contrato)
        )
        db.session.add(recibo)
        db.session.commit()

        flash('Pago realizado. Los fondos están retenidos en escrow.', 'success')
        return redirect(url_for('pagos.ver_recibo', id=pago.id))
    return render_template('pagos/pagar.html', form=form, contrato=contrato)


@pagos_bp.route('/recibo/<int:id>')
@login_required
def ver_recibo(id):
    pago = db.session.get(Pago, id)
    if not pago:
        abort(404)
    contrato = pago.contrato
    if not (
        current_user.id == contrato.id_cliente or
        current_user.id == contrato.id_desarrollador or
        current_user.tipo_usuario == 'admin'
    ):
        abort(403)
    recibo = db.session.execute(
        db.select(Recibo).filter_by(id_pago=id)
    ).scalar_one_or_none()
    return render_template('pagos/recibo.html', pago=pago, recibo=recibo, contrato=contrato)


@pagos_bp.route('/contrato/<int:id>/liberar', methods=['POST'])
@login_required
def liberar_fondos(id):
    """El cliente aprueba el entregable y libera los fondos al desarrollador."""
    contrato = db.session.get(Contrato, id)
    if not contrato or contrato.id_cliente != current_user.id:
        abort(403)
    pago = db.session.execute(
        db.select(Pago).filter_by(id_contrato=id, estado_escrow='retenido')
    ).scalar_one_or_none()
    if not pago:
        flash('No hay fondos retenidos para este contrato.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=id))

    pago.estado_escrow = 'liberado'
    pago.fecha_liberacion = datetime.utcnow()
    contrato.estado = 'finalizado'

    liberacion = Liberacion(
        id_pago=pago.id,
        id_usuario=current_user.id,
        monto_liberado=pago.monto,
        motivo='Entregable aprobado por el cliente'
    )
    db.session.add(liberacion)
    db.session.commit()

    flash(f'Fondos liberados: ${pago.monto:.2f} al desarrollador.', 'success')
    return redirect(url_for('contratos.ver_contrato', id=id))


@pagos_bp.route('/contrato/<int:id>/disputa/nueva', methods=['GET', 'POST'])
@login_required
def nueva_disputa(id):
    contrato = db.session.get(Contrato, id)
    if not contrato or not (
        current_user.id == contrato.id_cliente or
        current_user.id == contrato.id_desarrollador
    ):
        abort(403)
    form = DisputaForm()
    if form.validate_on_submit():
        disputa = Disputa(
            id_contrato=id,
            id_reportante=current_user.id,
            tipo=form.tipo.data,
            descripcion=form.descripcion.data
        )
        db.session.add(disputa)

        # Congelar fondos si existen
        pago = db.session.execute(
            db.select(Pago).filter_by(id_contrato=id, estado_escrow='retenido')
        ).scalar_one_or_none()
        if pago:
            pago.estado_escrow = 'retenido'  # se mantiene congelado

        db.session.commit()
        flash('Disputa creada. Un administrador la revisará.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=id))
    return render_template('pagos/disputa_form.html', form=form, contrato=contrato)


@pagos_bp.route('/disputa/<int:id>/resolver', methods=['GET', 'POST'])
@login_required
def resolver_disputa(id):
    if current_user.tipo_usuario != 'admin':
        abort(403)
    disputa = db.session.get(Disputa, id)
    if not disputa:
        abort(404)
    form = ArbitrajeForm()
    if form.validate_on_submit():
        arbitraje = Arbitraje(
            id_disputa=id,
            id_arbitro=current_user.id,
            decision=form.decision.data,
            porcentaje_desarrollador=form.porcentaje_desarrollador.data or 0,
            notas=form.notas.data
        )
        db.session.add(arbitraje)

        pago = db.session.execute(
            db.select(Pago).filter_by(id_contrato=disputa.id_contrato)
        ).scalar_one_or_none()
        if pago:
            if form.decision.data == 'liberar':
                pago.estado_escrow = 'liberado'
                pago.fecha_liberacion = datetime.utcnow()
            elif form.decision.data == 'reembolsar':
                pago.estado_escrow = 'reembolsado'
                pago.fecha_liberacion = datetime.utcnow()
            elif form.decision.data == 'dividir':
                pago.estado_escrow = 'dividido'
                pago.fecha_liberacion = datetime.utcnow()

        disputa.estado = 'resuelta'
        disputa.fecha_hora_resolucion = datetime.utcnow()
        disputa.resolucion = form.notas.data
        db.session.commit()

        flash('Disputa resuelta.', 'success')
        return redirect(url_for('pagos.ver_disputa', id=id))
    return render_template('pagos/resolver_disputa.html', form=form, disputa=disputa)


@pagos_bp.route('/disputa/<int:id>')
@login_required
def ver_disputa(id):
    if current_user.tipo_usuario != 'admin':
        abort(403)
    disputa = db.session.get(Disputa, id)
    if not disputa:
        abort(404)
    return render_template('pagos/ver_disputa.html', disputa=disputa)


def _generar_html_recibo(pago, contrato):
    return f"""
    <html><body>
    <h1>Recibo de Pago - Zaas</h1>
    <p><strong>Folio:</strong> (generado al guardar)</p>
    <p><strong>Monto:</strong> ${pago.monto:.2f}</p>
    <p><strong>Contrato:</strong> #{contrato.id}</p>
    <p><strong>Cliente:</strong> {contrato.cliente.nombres} {contrato.cliente.apellido_paterno}</p>
    <p><strong>Desarrollador:</strong> {contrato.desarrollador.nombres} {contrato.desarrollador.apellido_paterno}</p>
    <p><strong>Estado:</strong> {pago.estado_escrow}</p>
    <p><strong>Fecha:</strong> {pago.fecha_pago.strftime('%Y-%m-%d %H:%M')}</p>
    </body></html>
    """
