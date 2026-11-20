"""Rutas HTML legacy del módulo de pagos.

Adaptadores sobre la capa de servicios para conservar compatibilidad con las
plantillas existentes.
"""

from __future__ import annotations

from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.contratos.models import Contrato
from app.extensions import db
from app.pagos import pagos_bp, services
from app.pagos.errors import PagoError
from app.pagos.forms import ArbitrajeForm, DisputaForm
from app.pagos.models import Disputa, Pago, Recibo


def _flash_error(exc: Exception, default="No se pudo completar la operación."):
    if isinstance(exc, PagoError):
        flash(exc.mensaje, "danger")
    elif isinstance(exc, PermissionError):
        flash("No tienes permiso para realizar esta acción.", "danger")
    elif isinstance(exc, ValueError):
        flash(str(exc) or default, "danger")
    else:
        flash(default, "danger")


def _pago_retenido_contrato(id_contrato):
    pagos = db.session.execute(
        db.select(Pago).filter_by(id_contrato=id_contrato).order_by(Pago.fecha_pago.desc())
    ).scalars().all()
    for p in pagos:
        services._asegurar_pago_vigente(p, commit=False)
    db.session.commit()
    for p in pagos:
        if p.estado_escrow == "retenido":
            return p
    return None


@pagos_bp.route("/contrato/<int:id>/pagar", methods=["GET", "POST"])
@login_required
def pagar_contrato(id):
    contrato = db.session.get(Contrato, id)
    if not contrato or contrato.id_cliente != current_user.id:
        abort(403)

    if request.method == "POST":
        monto = request.form.get("monto") or contrato.costo_acordado
        tarjeta = {
            "numero": request.form.get("numero", ""),
            "vencimiento": request.form.get("vencimiento", ""),
            "cvc": request.form.get("cvc", ""),
        }
        try:
            pago = services.registrar_pago(
                contrato,
                current_user,
                monto=monto,
                tarjeta=tarjeta,
                idempotency_key=request.form.get("idempotency_key") or None,
            )
            db.session.commit()
            flash("Pago registrado. Se está procesando la confirmación.", "info")
            return redirect(url_for("pagos.ver_pago", id=pago.id))
        except Exception as error:
            db.session.rollback()
            _flash_error(error)

    return render_template("pagos/pagar.html", contrato=contrato)


@pagos_bp.route("/pago/<int:id>")
@login_required
def ver_pago(id):
    pago = services.obtener_pago(id, current_user)
    if not pago:
        abort(404)
    contrato = pago.contrato
    if not (
        current_user.id == contrato.id_cliente
        or current_user.id == contrato.id_desarrollador
        or current_user.tipo_usuario == "admin"
    ):
        abort(403)
    refrescar = pago.estado_escrow == "pendiente"
    return render_template("pagos/pago_detalle.html", pago=pago, contrato=contrato, refrescar=refrescar)


@pagos_bp.route("/pago/<int:id>/verificar", methods=["POST"])
@login_required
def verificar_pago(id):
    try:
        pago = services.obtener_pago(id, current_user)
        if not pago or pago.contrato.id_cliente != current_user.id:
            abort(403)
        services.verificar_pago(pago, request.form.get("codigo", ""))
        flash("Pago verificado.", "success")
    except Exception as error:
        db.session.rollback()
        _flash_error(error)
    return redirect(url_for("pagos.ver_pago", id=id))


@pagos_bp.route("/recibo/<int:id>")
@login_required
def ver_recibo(id):
    pago = services.obtener_pago(id, current_user)
    if not pago:
        abort(404)
    contrato = pago.contrato
    recibo = services.obtener_recibo_pago(id, current_user)
    if recibo is None and pago.estado_escrow in ("retenido", "liberado", "dividido", "reembolsado"):
        try:
            recibo = services.generar_recibo(pago)
            db.session.commit()
        except Exception:
            db.session.rollback()
            recibo = None
    return render_template("pagos/recibo.html", pago=pago, recibo=recibo, contrato=contrato)


@pagos_bp.route("/contrato/<int:id>/liberar", methods=["GET", "POST"])
@login_required
def liberar_fondos(id):
    contrato = db.session.get(Contrato, id)
    if not contrato or contrato.id_cliente != current_user.id:
        abort(403)

    pago = _pago_retenido_contrato(id)
    if not pago:
        flash("No hay fondos retenidos para este contrato.", "warning")
        return redirect(url_for("contratos.ver_contrato", id=id))

    if request.method == "POST":
        try:
            monto = request.form.get("monto_liberado") or pago.monto
            entregable_id = request.form.get("id_entregable") or None
            if entregable_id in ("", "None", None):
                entregable_id = None
            else:
                entregable_id = int(entregable_id)
            motivo = request.form.get("motivo") or "Liberación manual"
            services.crear_liberacion(pago, current_user, monto, entregable_id, motivo)
            db.session.commit()
            flash("Liberación registrada.", "success")
            return redirect(url_for("contratos.ver_contrato", id=id))
        except Exception as error:
            db.session.rollback()
            _flash_error(error)

    aprobados = [e for e in (contrato.entregables or []) if e.estado == "aprobado"]
    return render_template("pagos/liberar.html", contrato=contrato, pago=pago, entregables=aprobados)


@pagos_bp.route("/contrato/<int:id>/disputa/nueva", methods=["GET", "POST"])
@login_required
def nueva_disputa(id):
    contrato = db.session.get(Contrato, id)
    if not contrato or not (current_user.id == contrato.id_cliente or current_user.id == contrato.id_desarrollador):
        abort(403)
    form = DisputaForm()
    if form.validate_on_submit():
        try:
            pago = _pago_retenido_contrato(id)
            aprobados = [e for e in (contrato.entregables or []) if e.estado in ("pendiente", "aprobado")]
            entregable = max(aprobados, key=lambda e: e.fecha_subida or datetime.min, default=None)
            if form.tipo.data == "entregable" and entregable:
                id_pago, id_entregable = None, entregable.id
            elif pago:
                id_pago, id_entregable = pago.id, None
            else:
                id_pago, id_entregable = None, (entregable.id if entregable else None)
            services.abrir_disputa(
                contrato,
                current_user,
                form.tipo.data or "otro",
                form.descripcion.data or "",
                id_pago=id_pago,
                id_entregable=id_entregable,
            )
            db.session.commit()
            flash("Disputa creada. Un administrador la revisará.", "warning")
            return redirect(url_for("contratos.ver_contrato", id=id))
        except Exception as error:
            db.session.rollback()
            _flash_error(error)
    return render_template("pagos/disputa_form.html", form=form, contrato=contrato)


@pagos_bp.route("/disputa/<int:id>/resolver", methods=["GET", "POST"])
@login_required
def resolver_disputa(id):
    if current_user.tipo_usuario != "admin":
        abort(403)
    disputa = db.session.get(Disputa, id)
    if not disputa:
        abort(404)
    if disputa.estado in ("resuelta", "cerrada"):
        flash("Esta disputa ya fue resuelta.", "warning")
        return redirect(url_for("pagos.ver_disputa", id=id))
    form = ArbitrajeForm()
    if form.validate_on_submit():
        try:
            # crear_arbitraje atiende internamente si la disputa está abierta (misma transacción)
            services.crear_arbitraje(
                disputa,
                current_user,
                form.decision.data,
                form.porcentaje_desarrollador.data,
                form.notas.data,
            )
            db.session.commit()
            flash("Disputa resuelta.", "success")
            return redirect(url_for("pagos.ver_disputa", id=id))
        except Exception as error:
            db.session.rollback()
            _flash_error(error)
    return render_template("pagos/resolver_disputa.html", form=form, disputa=disputa)


@pagos_bp.route("/disputa/<int:id>")
@login_required
def ver_disputa(id):
    if current_user.tipo_usuario != "admin":
        abort(403)
    disputa = db.session.get(Disputa, id)
    if not disputa:
        abort(404)
    return render_template("pagos/ver_disputa.html", disputa=disputa)


def _generar_html_recibo(pago, contrato, folio=""):
    return (
        "<html><body>"
        "<h1>Recibo de Pago - Zaas</h1>"
        f"<p><strong>Folio:</strong> {folio}</p>"
        f"<p><strong>Monto:</strong> ${float(pago.monto):.2f}</p>"
        f"<p><strong>Contrato:</strong> #{contrato.id}</p>"
        f"<p><strong>Estado:</strong> {pago.estado_escrow}</p>"
        "</body></html>"
    )
