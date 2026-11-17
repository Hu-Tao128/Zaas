"""API JSON del módulo de Pagos para el frontend React.

Capa adaptadora: autentica/comprueba permisos, delega en servicios y traduce
errores de dominio a respuestas JSON estables.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from functools import wraps

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user
from sqlalchemy import or_

from app.contratos.models import Contrato
from app.extensions import db
from app.pagos import services
from app.pagos.errors import PagoError, PagoPermisoError, PagoValidacionError
from app.pagos.models import Arbitraje, Disputa, Liberacion, Pago, Recibo


def _money_str(valor):
    return format(Decimal(str(valor or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP), "f")

pagos_api_bp = Blueprint("pagos_api", __name__, url_prefix="/pagos/api")

try:
    from flask_wtf.csrf import csrf_exempt  # type: ignore
except Exception:  # pragma: no cover
    csrf_exempt = lambda f: f  # noqa: E731


# ---------------------------------------------------------------------------
# utilidades
# ---------------------------------------------------------------------------


def _ok(mensaje=None, status=200, **datos):
    payload = {"ok": True, "mensaje": mensaje}
    payload.update(datos)
    return jsonify(payload), status


def _error(mensaje, status=400, errores=None, codigo=None):
    payload = {
        "ok": False,
        "mensaje": mensaje,
        "errores": errores or {},
    }
    if codigo:
        payload["codigo"] = codigo
    return jsonify(payload), status


def _error_desde_exc(exc: Exception):
    if isinstance(exc, PagoError):
        return _error(exc.mensaje, exc.status_code, getattr(exc, "errores", None), getattr(exc, "codigo", None))
    if isinstance(exc, PermissionError):
        return _error("No tienes permiso para realizar esta acción.", 403, codigo="permiso_denegado")
    if isinstance(exc, ValueError):
        return _error(str(exc) or "La solicitud no es válida.", 400, codigo="validacion_invalida")
    # Error inesperado: sin detalles técnicos al cliente.
    try:
        current_app.logger.exception("Error inesperado en API de pagos")
    except Exception:
        pass
    return _error("No se pudo completar la operación. Inténtalo de nuevo más tarde.", 500, codigo="error_interno")


def _requiere(*roles):
    def decorador(vista):
        @wraps(vista)
        def envoltura(*args, **kwargs):
            if not current_user.is_authenticated:
                return _error("Debes iniciar sesión.", 401, codigo="no_autenticado")
            if roles and current_user.tipo_usuario not in roles:
                return _error("No tienes permiso para realizar esta acción.", 403, codigo="permiso_denegado")
            return vista(*args, **kwargs)

        return envoltura

    return decorador


def _iso(valor, utc=False):
    if not valor:
        return None
    texto = valor.isoformat()
    return texto + "Z" if utc else texto


def _datos_json():
    datos = request.get_json(silent=True)
    return datos if isinstance(datos, dict) else {}


def _int_o_none(valor):
    if valor is None or valor == "":
        return None
    try:
        return int(valor)
    except (TypeError, ValueError):
        return None


def _usuario_publico(usuario):
    if usuario is None:
        return None
    return {
        "id": usuario.id,
        "nombres": usuario.nombres,
        "apellido_paterno": usuario.apellido_paterno,
        "nombre_completo": getattr(usuario, "nombre_completo", None),
    }


def _liberacion(item):
    return {
        "id": item.id,
        "id_pago": item.id_pago,
        "id_entregable": item.id_entregable,
        "monto_liberado": _money_str(item.monto_liberado),
        "motivo": item.motivo,
        "fecha_hora": _iso(item.fecha_hora, utc=True),
        "usuario": _usuario_publico(getattr(item, "usuario", None)),
    }


def _recibo(item):
    if item is None:
        return None
    return {
        "id": item.id,
        "id_pago": item.id_pago,
        "folio": item.folio,
        "fecha_emision": _iso(item.fecha_emision, utc=True),
        "total": item.total,
        "contenido_html": item.contenido_html,
    }


def _disputa(item):
    arbitraje = None
    if getattr(item, "arbitrajes", None):
        arb = item.arbitrajes[0]
        arbitraje = {
            "id": arb.id,
            "decision": arb.decision,
            "porcentaje_desarrollador": arb.porcentaje_desarrollador,
            "notas": arb.notas,
            "fecha_hora": _iso(arb.fecha_hora, utc=True),
        }
    return {
        "id": item.id,
        "id_contrato": item.id_contrato,
        "id_admin": item.id_admin,
        "id_reportante": item.id_reportante,
        "id_pago": item.id_pago,
        "id_entregable": item.id_entregable,
        "id_incidencia": item.id_incidencia,
        "tipo": item.tipo,
        "descripcion": item.descripcion,
        "estado": item.estado,
        "fecha_hora_publicacion": _iso(item.fecha_hora_publicacion, utc=True),
        "fecha_hora_resolucion": _iso(item.fecha_hora_resolucion, utc=True),
        "resolucion": item.resolucion,
        "reportante": _usuario_publico(getattr(item, "reportante", None)),
        "arbitraje": arbitraje,
    }


def _pago(item):
    recibo = item.recibos[0] if getattr(item, "recibos", None) else None
    monto = Decimal(str(item.monto or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    liberado_total = sum(
        (Decimal(str(x.monto_liberado or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for x in (item.liberaciones or [])),
        Decimal("0.00"),
    )
    disponible = monto - liberado_total
    if disponible < Decimal("0.00"):
        disponible = Decimal("0.00")
    return {
        "id": item.id,
        "id_contrato": item.id_contrato,
        "monto": _money_str(monto),
        "estado_escrow": item.estado_escrow,
        "moneda": item.moneda,
        "proveedor": item.proveedor,
        "codigo_fallo": item.codigo_fallo,
        "mensaje_fallo": item.mensaje_fallo,
        "metodo_pago": item.metodo_pago,
        "transaccion_id": item.transaccion_id,
        "fecha_pago": _iso(item.fecha_pago, utc=True),
        "fecha_confirmacion": _iso(item.fecha_confirmacion, utc=True),
        "fecha_liberacion": _iso(item.fecha_liberacion, utc=True),
        "reembolso_id": item.reembolso_id,
        "fecha_reembolso": _iso(item.fecha_reembolso, utc=True),
        "liberado": _money_str(liberado_total),
        "disponible": _money_str(disponible),
        "recibo": _recibo(recibo),
        "liberaciones": [_liberacion(x) for x in (item.liberaciones or [])],
    }


def _arbitraje(item):
    if item is None:
        return None
    return {
        "id": item.id,
        "id_disputa": item.id_disputa,
        "id_arbitro": item.id_arbitro,
        "decision": item.decision,
        "porcentaje_desarrollador": item.porcentaje_desarrollador,
        "notas": item.notas,
        "fecha_hora": _iso(item.fecha_hora, utc=True),
    }


@pagos_api_bp.get("/csrf")
def csrf():
    from flask_wtf.csrf import generate_csrf

    return jsonify({"csrf_token": generate_csrf()})


# ---------------------------------------------------------------------------
# pagos
# ---------------------------------------------------------------------------


@pagos_api_bp.post("/crear")
@pagos_api_bp.post("/")
@_requiere()
def crear_pago():
    datos = _datos_json()
    id_contrato = _int_o_none(datos.get("id_contrato"))
    if id_contrato is None:
        return _error("El contrato es obligatorio.", 422, {"id_contrato": "El contrato es obligatorio."}, codigo="validacion_invalida")

    try:
        contrato = services.contrato_de_usuario(id_contrato, current_user)
        if contrato is None:
            return _error("No se encontró el contrato solicitado.", 404, codigo="contrato_no_encontrado")
        pago = services.registrar_pago(
            contrato,
            current_user,
            monto=datos.get("monto"),
            metodo_pago=datos.get("metodo_pago"),
            transaccion_id=datos.get("transaccion_id"),
            idempotency_key=request.headers.get("Idempotency-Key") or datos.get("idempotency_key"),
            tarjeta=datos.get("tarjeta"),
        )
        db.session.commit()
        return _ok("Pago registrado correctamente.", 201, pago=_pago(pago))
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.post("/pagos/<int:id>/verificar")
@pagos_api_bp.post("/<int:id>/verificar")
@_requiere()
def verificar_pago(id):
    try:
        pago = services.obtener_pago(id, current_user)
        if pago is None:
            return _error("No se encontró el pago solicitado.", 404, codigo="pago_no_encontrado")
        datos = _datos_json()
        services.verificar_pago(pago, datos.get("codigo"))
        db.session.refresh(pago)
        return _ok("Pago verificado correctamente.", pago=_pago(pago))
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.post("/confirmar")
@pagos_api_bp.post("/webhook/confirmar")
@pagos_api_bp.post("/pagos/<int:id>/confirmar")
@csrf_exempt
def confirmar_pago(id=None):
    datos = _datos_json()
    if id is None:
        id = _int_o_none(datos.get("pago_id") or datos.get("id"))
    if id is None:
        return _error("El pago es obligatorio.", 422, {"pago_id": "El pago es obligatorio."}, codigo="validacion_invalida")
    firma = datos.get("firma") or request.headers.get("X-Signature")
    timestamp = datos.get("timestamp") or request.headers.get("X-Timestamp")
    try:
        pago = services.confirmar_pago(id, firma, timestamp)
        return _ok("Confirmación procesada.", pago=_pago(pago))
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.get("/<int:id>")
@pagos_api_bp.get("/pago/<int:id>")
@_requiere()
def obtener_pago(id):
    try:
        pago = services.obtener_pago(id, current_user)
        if pago is None:
            return _error("No se encontró el pago solicitado.", 404, codigo="pago_no_encontrado")
        return jsonify({"ok": True, "pago": _pago(pago)})
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.get("/contrato/<int:id>")
@pagos_api_bp.get("/contrato/<int:id>/pagos")
@_requiere()
def listar_pagos_contrato(id):
    try:
        pagos = services.listar_pagos_contrato(id, current_user)
        if pagos is None:
            return _error("No se encontró el contrato solicitado.", 404, codigo="contrato_no_encontrado")
        return jsonify({"ok": True, "items": [_pago(p) for p in pagos], "total": len(pagos)})
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.get("/contrato/<int:id>/resumen")
@_requiere()
def resumen_contrato(id):
    try:
        resumen = services.obtener_resumen_contrato(id, current_user)
        if resumen is None:
            return _error("No se encontró el contrato solicitado.", 404, codigo="contrato_no_encontrado")
        return jsonify({"ok": True, "resumen": resumen})
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.get("/pagos")
@pagos_api_bp.get("/")
@_requiere()
def listar_pagos():
    try:
        id_contrato = _int_o_none(request.args.get("id_contrato") or request.args.get("contrato"))
        if id_contrato is not None:
            pagos = services.listar_pagos_contrato(id_contrato, current_user)
            if pagos is None:
                return _error("No se encontró el contrato solicitado.", 404, codigo="contrato_no_encontrado")
            return jsonify({"ok": True, "items": [_pago(p) for p in pagos], "total": len(pagos)})

        if current_user.tipo_usuario == "admin":
            query = db.select(Pago).order_by(Pago.fecha_pago.desc())
        else:
            query = (
                db.select(Pago)
                .join(Contrato)
                .filter(or_(Contrato.id_cliente == current_user.id, Contrato.id_desarrollador == current_user.id))
                .order_by(Pago.fecha_pago.desc())
            )
        pagos = db.session.execute(query).scalars().all()
        # Normalizar expiraciones al consultar listados generales
        cambiado = False
        for p in pagos:
            antes = p.estado_escrow
            services._asegurar_pago_vigente(p, commit=False)
            if p.estado_escrow != antes:
                cambiado = True
        if cambiado:
            db.session.commit()
        return jsonify({"ok": True, "items": [_pago(p) for p in pagos], "total": len(pagos)})
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


# ---------------------------------------------------------------------------
# liberaciones
# ---------------------------------------------------------------------------


@pagos_api_bp.post("/liberaciones/crear")
@pagos_api_bp.post("/liberaciones")
@pagos_api_bp.post("/pagos/<int:id_pago>/liberar")
@pagos_api_bp.post("/pagos/<int:id_pago>/liberaciones")
@_requiere()
def crear_liberacion(id_pago=None):
    datos = _datos_json()
    if id_pago is None:
        id_pago = _int_o_none(datos.get("id_pago"))
    if id_pago is None:
        return _error("El pago es obligatorio.", 422, {"id_pago": "El pago es obligatorio."}, codigo="validacion_invalida")
    try:
        pago = services.obtener_pago(id_pago, current_user)
        if pago is None:
            return _error("No se encontró el pago solicitado.", 404, codigo="pago_no_encontrado")
        monto = datos.get("monto_liberado", datos.get("monto"))
        id_entregable = _int_o_none(datos.get("id_entregable"))
        motivo = datos.get("motivo")
        liberacion = services.crear_liberacion(pago, current_user, monto, id_entregable, motivo)
        db.session.commit()
        return _ok("Liberación registrada.", 201, liberacion=_liberacion(liberacion))
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.get("/pagos/<int:id_pago>/liberaciones")
@pagos_api_bp.get("/liberaciones/<int:id_pago>")
@pagos_api_bp.get("/liberaciones")
@_requiere()
def listar_liberaciones(id_pago=None):
    if id_pago is None:
        id_pago = _int_o_none(request.args.get("id_pago"))
    if id_pago is None:
        return _error("El pago es obligatorio.", 422, {"id_pago": "El pago es obligatorio."}, codigo="validacion_invalida")
    try:
        liberaciones = services.listar_liberaciones_pago(id_pago, current_user)
        if liberaciones is None:
            return _error("No se encontró el pago solicitado.", 404, codigo="pago_no_encontrado")
        return jsonify({"ok": True, "items": [_liberacion(x) for x in liberaciones], "total": len(liberaciones)})
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


# ---------------------------------------------------------------------------
# recibos
# ---------------------------------------------------------------------------


@pagos_api_bp.get("/pagos/<int:id_pago>/recibo")
@pagos_api_bp.get("/recibos/<int:id_pago>")
@pagos_api_bp.get("/recibo/<int:id_pago>")
@pagos_api_bp.get("/recibos")
@_requiere()
def obtener_recibo(id_pago=None):
    if id_pago is None:
        id_pago = _int_o_none(request.args.get("id_pago"))
    if id_pago is None:
        return _error("El pago es obligatorio.", 422, {"id_pago": "El pago es obligatorio."}, codigo="validacion_invalida")
    try:
        pago = services.obtener_pago(id_pago, current_user)
        if pago is None:
            return _error("No se encontró el pago solicitado.", 404, codigo="pago_no_encontrado")
        recibo = services.obtener_recibo_pago(id_pago, current_user)
        if recibo is None:
            # Solo generar si el pago ya está en un estado que puede tener recibo (retenido/liberado/dividido/reembolsado)
            if pago.estado_escrow in ("retenido", "liberado", "dividido", "reembolsado"):
                recibo = services.generar_recibo(pago)
                db.session.commit()
            else:
                return _error("No se encontró el recibo solicitado.", 404, codigo="recurso_no_encontrado")
        return jsonify({"ok": True, "recibo": _recibo(recibo)})
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


# ---------------------------------------------------------------------------
# disputas
# ---------------------------------------------------------------------------


@pagos_api_bp.post("/disputas/crear")
@pagos_api_bp.post("/disputas")
@pagos_api_bp.post("/contrato/<int:id>/disputa")
@_requiere()
def crear_disputa(id=None):
    datos = _datos_json()
    id_contrato = id if id is not None else _int_o_none(datos.get("id_contrato"))
    if id_contrato is None:
        return _error("El contrato es obligatorio.", 422, {"id_contrato": "El contrato es obligatorio."}, codigo="validacion_invalida")
    try:
        contrato = services.contrato_de_usuario(id_contrato, current_user)
        if contrato is None:
            return _error("No se encontró el contrato solicitado.", 404, codigo="contrato_no_encontrado")
        disputa = services.abrir_disputa(
            contrato,
            current_user,
            datos.get("tipo", "otro"),
            datos.get("descripcion", ""),
            id_pago=_int_o_none(datos.get("id_pago")),
            id_entregable=_int_o_none(datos.get("id_entregable")),
            id_incidencia=_int_o_none(datos.get("id_incidencia")),
        )
        db.session.commit()
        return _ok("Disputa abierta.", 201, disputa=_disputa(disputa))
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.post("/disputas/<int:id>/atender")
@pagos_api_bp.post("/disputas/<int:id>/tomar")
@_requiere("admin")
def atender_disputa(id):
    try:
        disputa = services.obtener_disputa(id, current_user)
        if disputa is None:
            return _error("No se encontró la disputa solicitada.", 404, codigo="disputa_no_encontrada")
        services.atender_disputa(disputa, current_user)
        db.session.commit()
        db.session.refresh(disputa)
        return _ok("Disputa en revisión.", disputa=_disputa(disputa))
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.get("/disputas/<int:id>")
@_requiere()
def obtener_disputa(id):
    try:
        disputa = services.obtener_disputa(id, current_user)
        if disputa is None:
            return _error("No se encontró la disputa solicitada.", 404, codigo="disputa_no_encontrada")
        return jsonify({"ok": True, "disputa": _disputa(disputa)})
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.get("/disputas")
@_requiere()
def listar_disputas():
    try:
        items = services.listar_disputas(current_user)
        return jsonify({"ok": True, "items": [_disputa(d) for d in items], "total": len(items)})
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


# ---------------------------------------------------------------------------
# arbitraje
# ---------------------------------------------------------------------------


@pagos_api_bp.post("/disputas/<int:id>/arbitraje")
@pagos_api_bp.post("/disputas/<int:id>/resolver")
@pagos_api_bp.post("/arbitrajes/crear")
@pagos_api_bp.post("/arbitrajes")
@_requiere("admin")
def crear_arbitraje(id=None):
    datos = _datos_json()
    if id is None:
        id = _int_o_none(datos.get("id_disputa") or datos.get("id"))
    if id is None:
        return _error("La disputa es obligatoria.", 422, {"id_disputa": "La disputa es obligatoria."}, codigo="validacion_invalida")
    try:
        disputa = services.obtener_disputa(id, current_user)
        if disputa is None:
            return _error("No se encontró la disputa solicitada.", 404, codigo="disputa_no_encontrada")
        arbitraje = services.crear_arbitraje(
            disputa,
            current_user,
            datos.get("decision"),
            datos.get("porcentaje_desarrollador", datos.get("porcentaje")),
            datos.get("notas") or datos.get("resolucion"),
        )
        db.session.commit()
        db.session.refresh(disputa)
        return _ok("Disputa resuelta.", 201, arbitraje=_arbitraje(arbitraje), disputa=_disputa(disputa))
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)


@pagos_api_bp.get("/disputas/<int:id>/arbitraje")
@pagos_api_bp.get("/arbitrajes/<int:id>")
@pagos_api_bp.get("/arbitrajes")
@_requiere()
def obtener_arbitraje(id=None):
    try:
        if id is None:
            id = _int_o_none(request.args.get("id_disputa") or request.args.get("id"))
        if id is None:
            if current_user.tipo_usuario == "admin":
                items = db.session.execute(db.select(Arbitraje).order_by(Arbitraje.fecha_hora.desc())).scalars().all()
            else:
                items = []
            return jsonify({"ok": True, "items": [_arbitraje(x) for x in items], "total": len(items)})

        arbitraje = db.session.get(Arbitraje, id)
        if arbitraje is None:
            arbitraje = services.obtener_arbitraje_disputa(id, current_user)
        if arbitraje is None:
            return _error("No se encontró el arbitraje solicitado.", 404, codigo="recurso_no_encontrado")

        disputa = arbitraje.disputa
        contrato = disputa.contrato
        if current_user.tipo_usuario != "admin" and current_user.id not in (contrato.id_cliente, contrato.id_desarrollador):
            return _error("No tienes permiso para realizar esta acción.", 403, codigo="permiso_denegado")
        return jsonify({"ok": True, "arbitraje": _arbitraje(arbitraje)})
    except Exception as exc:
        db.session.rollback()
        return _error_desde_exc(exc)
