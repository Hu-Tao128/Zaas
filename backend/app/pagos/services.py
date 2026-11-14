"""Servicios (reglas de negocio) del módulo de Pagos.

Toda regla de negocio del módulo vive aquí. Las capas API/rutas deben autenticar,
comprobar permisos, invocar estos servicios y traducir resultados/errores.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import threading
import time
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP, getcontext

from sqlalchemy import and_, func, or_

from app.auth.models import Usuario
from app.contratos.models import Contrato, Entregable
from app.extensions import db
from app.pagos.errors import (
    ArbitrajeDuplicadoError,
    ArbitrajeInvalidoError,
    ConfirmacionInvalidaError,
    ContratoNoAptoError,
    ContratoNoEncontradoError,
    DisputaActivaError,
    DisputaDuplicadaError,
    DisputaNoEncontradaError,
    DisputaOrigenInvalidoError,
    EntregableInvalidoError,
    IdempotenciaConflictoError,
    IncidenciaYaEscaladaError,
    MontoInvalidoError,
    PagoError,
    PagoExpiradoError,
    PagoNoEncontradoError,
    PagoNoPendienteError,
    PagoNoRetenidoError,
    PagoPermisoError,
    PagoValidacionError,
    ReembolsoError,
    RecursoNoEncontradoError,
    SaldoInsuficienteError,
    TarjetaNoAdmitidaError,
    TopeContratoSuperadoError,
    TransicionEstadoDisputaInvalidaError,
    TransicionEstadoPagoInvalidaError,
    VerificacionInvalidaError,
)
from app.pagos.models import Arbitraje, Disputa, Liberacion, Pago, Recibo

getcontext().prec = 28

# ---------------------------------------------------------------------------
# Compatibilidad/locks en memoria (complemento; la consistencia real usa BD)
# ---------------------------------------------------------------------------

_LIBERACION_LOCKS = {}
_LIBERACION_LOCKS_GUARD = threading.Lock()


def _lock_liberacion(id_pago):
    with _LIBERACION_LOCKS_GUARD:
        if id_pago not in _LIBERACION_LOCKS:
            _LIBERACION_LOCKS[id_pago] = threading.Lock()
        return _LIBERACION_LOCKS[id_pago]


# ---------------------------------------------------------------------------
# Proveedor simulado
# ---------------------------------------------------------------------------

TARJETAS_PRUEBA = {
    "4242424242424242": "aprobada",
    "4000000000000002": ("rechazada", "tarjeta_rechazada", "La tarjeta fue rechazada."),
    "4000000000009995": ("rechazada", "fondos_insuficientes", "Fondos insuficientes."),
    "4000000000003220": "verificacion",
}

CODIGO_VERIFICACION_PRUEBA = "123456"


class ProveedorPagoSimulado:
    def _validar_formato(self, numero, vencimiento, cvc):
        if not (isinstance(numero, str) and numero.isdigit() and len(numero) == 16):
            raise TarjetaNoAdmitidaError("El medio de pago no es válido.")
        if numero not in TARJETAS_PRUEBA:
            # Se rechaza sin persistir ni registrar el número.
            raise TarjetaNoAdmitidaError("El medio de pago no es admitido.")
        if not (isinstance(vencimiento, str) and len(vencimiento) == 5 and vencimiento[2] == "/"):
            raise TarjetaNoAdmitidaError("El medio de pago no es válido.")
        try:
            mm = int(vencimiento[:2])
            int(vencimiento[3:])
        except ValueError:
            raise TarjetaNoAdmitidaError("El medio de pago no es válido.")
        if mm < 1 or mm > 12:
            raise TarjetaNoAdmitidaError("El medio de pago no es válido.")
        if not (isinstance(cvc, str) and cvc.isdigit() and len(cvc) == 3):
            raise TarjetaNoAdmitidaError("El medio de pago no es válido.")

    def crear_cobro(self, monto, moneda, numero, vencimiento, cvc):
        self._validar_formato(numero, vencimiento, cvc)
        transaccion_id = f"TX-{uuid.uuid4().hex[:12].upper()}"
        resultado = TARJETAS_PRUEBA[numero]
        marca = "Visa"
        ultimos4 = numero[-4:]
        if resultado == "aprobada":
            return {"transaccion_id": transaccion_id, "marca": marca, "ultimos4": ultimos4, "resultado": "aprobada"}
        if resultado == "verificacion":
            return {"transaccion_id": transaccion_id, "marca": marca, "ultimos4": ultimos4, "resultado": "verificacion"}
        _, codigo, mensaje = resultado
        return {
            "transaccion_id": transaccion_id,
            "marca": marca,
            "ultimos4": ultimos4,
            "resultado": "rechazada",
            "codigo_fallo": codigo,
            "mensaje_fallo": mensaje,
        }

    def reembolsar(self, transaccion_id, monto):
        if monto is None or Decimal(str(monto)) <= 0:
            raise ReembolsoError("No se pudo completar el reembolso simulado.")
        # Falla controlada solo en modo de pruebas: transacciones que contienen "FAILRF"
        if _modo_pruebas() and transaccion_id and "FAILRF" in str(transaccion_id):
            raise ReembolsoError("No se pudo completar el reembolso simulado.")
        return f"RF-{uuid.uuid4().hex[:10].upper()}"


proveedor_pago = ProveedorPagoSimulado()

# Compatibilidad con código previo
ProveedorPago = ProveedorPagoSimulado
ProveedorPagoStub = ProveedorPagoSimulado


def procesar_pago_simulado(monto):
    return f"TX-{uuid.uuid4().hex[:12].upper()}"


# ---------------------------------------------------------------------------
# Utilidades y helpers
# ---------------------------------------------------------------------------


def _ahora():
    return datetime.utcnow()


def _bool_env(nombre, default=False):
    valor = os.environ.get(nombre)
    if valor is None:
        return default
    return str(valor).strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _expiracion_minutos():
    try:
        return int(os.environ.get("PAGOS_EXPIRACION_MINUTOS", "15"))
    except (TypeError, ValueError):
        return 15


def _confirm_delay():
    try:
        return int(os.environ.get("PAGOS_CONFIRM_DELAY", "3"))
    except (TypeError, ValueError):
        return 3


def _confirmacion_inmediata():
    return _bool_env("PAGOS_CONFIRMACION_INMEDIATA", False)


def _modo_pruebas():
    try:
        from flask import current_app
        if current_app and (current_app.config.get("TESTING") or current_app.testing):
            return True
    except Exception:
        pass
    env = (os.environ.get("FLASK_ENV") or os.environ.get("APP_ENV") or "").lower()
    if env in ("test", "testing"):
        return True
    return os.environ.get("PAGOS_TEST_MODE") == "1"


def _d(valor):
    if valor is None:
        return Decimal("0.00")
    return Decimal(str(valor))


def _money(valor):
    return _d(valor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _pago_expirado(pago, ahora=None):
    if not pago or pago.estado_escrow != "pendiente" or not pago.fecha_pago:
        return False
    ahora = ahora or _ahora()
    return ahora >= (pago.fecha_pago + timedelta(minutes=_expiracion_minutos()))


# ---------------------------------------------------------------------------
# Máquina de estados
# ---------------------------------------------------------------------------

_TRANSICIONES_PAGO = {
    "pendiente": {"retenido", "fallido"},
    "retenido": {"liberado", "reembolsado", "dividido"},
    "fallido": set(),
    "liberado": set(),
    "reembolsado": set(),
    "dividido": set(),
}

_TRANSICIONES_DISPUTA = {
    "abierta": {"en_revision", "cerrada"},
    "en_revision": {"resuelta", "cerrada"},
    "resuelta": set(),
    "cerrada": set(),
}


def _transicionar_pago(pago, nuevo_estado):
    actual = pago.estado_escrow
    if actual == nuevo_estado:
        return pago
    if nuevo_estado not in _TRANSICIONES_PAGO.get(actual, set()):
        raise TransicionEstadoPagoInvalidaError()
    pago.estado_escrow = nuevo_estado
    return pago


def _transicionar_disputa(disputa, nuevo_estado):
    actual = disputa.estado
    if actual == nuevo_estado:
        return disputa
    if nuevo_estado not in _TRANSICIONES_DISPUTA.get(actual, set()):
        raise TransicionEstadoDisputaInvalidaError()
    disputa.estado = nuevo_estado
    return disputa


# ---------------------------------------------------------------------------
# Acceso y permisos
# ---------------------------------------------------------------------------


def _es_parte_contrato(contrato, usuario):
    return usuario and usuario.id in (contrato.id_cliente, contrato.id_desarrollador)


def contrato_de_usuario(id_contrato, usuario):
    contrato = db.session.get(Contrato, id_contrato)
    if contrato is None:
        return None
    if getattr(usuario, "tipo_usuario", None) == "admin":
        return contrato
    if usuario.id not in (contrato.id_cliente, contrato.id_desarrollador):
        return None
    return contrato


def _contrato_permite_pagos(contrato):
    return contrato.estado in ("aceptado", "en_progreso", "entregado")


def _asegurar_pago_vigente(pago, commit=False):
    """Punto central: un pendiente vencido pasa a fallido y no sigue vigente."""
    if pago is None:
        return None
    if _pago_expirado(pago):
        if pago.estado_escrow == "pendiente":
            _transicionar_pago(pago, "fallido")
            pago.codigo_fallo = "expirado"
            pago.mensaje_fallo = "El pago expiró y ya no puede completarse."
            if commit:
                db.session.commit()
            else:
                db.session.flush()
    return pago


# ---------------------------------------------------------------------------
# Recibos y saldos
# ---------------------------------------------------------------------------


def generar_recibo(pago, contrato=None):
    existente = db.session.execute(db.select(Recibo).filter_by(id_pago=pago.id)).scalar_one_or_none()
    if existente is not None:
        return existente
    if contrato is None:
        contrato = pago.contrato
    folio = f"ZAS-{_ahora():%Y%m%d}-{uuid.uuid4().hex[:8].upper()}"
    recibo = Recibo(
        id_pago=pago.id,
        folio=folio,
        fecha_emision=_ahora(),
        total=float(_money(pago.monto)),
        contenido_html=None,
    )
    db.session.add(recibo)
    db.session.flush()
    return recibo


def _total_liberado(pago_id, bloqueado=False):
    stmt = db.select(func.coalesce(func.sum(Liberacion.monto_liberado), 0.0)).where(Liberacion.id_pago == pago_id)
    return _money(db.session.execute(stmt).scalar() or 0)


def _saldo_no_liberado(pago):
    return _money(_money(pago.monto) - _total_liberado(pago.id))


def _sumar_pagos_vigentes_contrato(contrato, excluir_pago_id=None):
    total = Decimal("0.00")
    ahora = _ahora()
    for p in (contrato.pagos or []):
        if excluir_pago_id is not None and p.id == excluir_pago_id:
            continue
        estado = p.estado_escrow
        if estado in ("retenido", "liberado", "dividido"):
            total += _money(p.monto)
        elif estado == "pendiente" and not _pago_expirado(p, ahora):
            total += _money(p.monto)
        # fallido, reembolsado y pendiente vencido no cuentan
    return _money(total)


# ---------------------------------------------------------------------------
# Pagos
# ---------------------------------------------------------------------------


def registrar_pago(contrato, usuario, monto=None, metodo_pago=None, transaccion_id=None, idempotency_key=None, tarjeta=None):
    if not contrato:
        raise ContratoNoEncontradoError()
    if getattr(usuario, "id", None) != contrato.id_cliente:
        raise PagoPermisoError("Solo el cliente del contrato puede registrar un pago.")
    if not _contrato_permite_pagos(contrato):
        raise ContratoNoAptoError()

    if monto is None:
        monto = contrato.costo_acordado
    try:
        monto_d = _money(monto)
    except Exception:
        raise MontoInvalidoError("El monto indicado no es válido.")
    if monto_d <= 0:
        raise MontoInvalidoError("El monto debe ser mayor a 0.")

    # Normalizar expiración de pendientes antes de calcular tope.
    for p in (contrato.pagos or []):
        _asegurar_pago_vigente(p, commit=False)

    if idempotency_key:
        existente = db.session.execute(db.select(Pago).filter_by(idempotency_key=idempotency_key)).scalar_one_or_none()
        if existente is not None:
            contrato_existente = existente.contrato
            mismo_usuario = contrato_existente is not None and contrato_existente.id_cliente == usuario.id
            mismos_datos = _money(existente.monto) == monto_d and existente.id_contrato == contrato.id
            if mismo_usuario and mismos_datos:
                return _asegurar_pago_vigente(existente, commit=True)
            raise IdempotenciaConflictoError()

    if _sumar_pagos_vigentes_contrato(contrato) + monto_d > _money(contrato.costo_acordado):
        raise TopeContratoSuperadoError()

    tarjeta = tarjeta or {}
    numero = str(tarjeta.get("numero", "")).replace(" ", "")
    vencimiento = str(tarjeta.get("vencimiento", ""))
    cvc = str(tarjeta.get("cvc", ""))
    if not numero:
        raise TarjetaNoAdmitidaError("El medio de pago no es válido.")
    info = proveedor_pago.crear_cobro(float(monto_d), "MXN", numero, vencimiento, cvc)

    pago = Pago(
        id_contrato=contrato.id,
        monto=float(monto_d),
        estado_escrow="pendiente",
        fecha_pago=_ahora(),
        metodo_pago=metodo_pago or "tarjeta",
        transaccion_id=info.get("transaccion_id") or transaccion_id,
        moneda="MXN",
        proveedor="simulado",
        marca_tarjeta=None,
        ultimos4=None,
        idempotency_key=idempotency_key,
        intentos_verificacion=0,
    )
    db.session.add(pago)
    db.session.flush()

    resultado = info.get("resultado")
    if resultado == "rechazada":
        # Intento rechazado: no debe bloquear reintentos ni contar como vigente.
        _transicionar_pago(pago, "fallido")
        pago.codigo_fallo = info.get("codigo_fallo")
        pago.mensaje_fallo = info.get("mensaje_fallo")
        db.session.commit()
        return pago

    if resultado == "aprobada" and _confirmacion_inmediata():
        _confirmar_como_retenido(pago)
        db.session.commit()
        return pago

    # verificacion o aprobada con flujo asíncrono: permanece pendiente
    if resultado == "verificacion":
        pago.intentos_verificacion = 0
    db.session.commit()

    if resultado == "aprobada":
        _programar_confirmacion_asincrona(pago.id, "aprobada", _confirm_delay())

    return pago


def _confirmar_como_retenido(pago):
    _asegurar_pago_vigente(pago, commit=False)
    if pago.estado_escrow != "pendiente":
        if pago.estado_escrow == "retenido":
            generar_recibo(pago)
            return pago
        raise TransicionEstadoPagoInvalidaError()
    _transicionar_pago(pago, "retenido")
    pago.fecha_confirmacion = _ahora()
    pago.codigo_fallo = None
    pago.mensaje_fallo = None
    db.session.flush()
    generar_recibo(pago)
    return pago


def _fallar_pago(pago, codigo_fallo, mensaje_fallo):
    _asegurar_pago_vigente(pago, commit=False)
    if pago.estado_escrow != "pendiente":
        if pago.estado_escrow == "fallido":
            return pago
        raise TransicionEstadoPagoInvalidaError()
    _transicionar_pago(pago, "fallido")
    pago.codigo_fallo = codigo_fallo
    pago.mensaje_fallo = mensaje_fallo
    return pago


def _programar_confirmacion_asincrona(pago_id, resultado, delay):
    from flask import current_app

    try:
        app = current_app._get_current_object()
    except Exception:
        # Sin contexto de app no se programa asincronía.
        return

    def ejecutar():
        with app.app_context():
            pago = db.session.get(Pago, pago_id)
            if pago is None:
                return
            _asegurar_pago_vigente(pago, commit=False)
            if pago.estado_escrow != "pendiente":
                db.session.commit()
                return
            try:
                if resultado == "aprobada":
                    _confirmar_como_retenido(pago)
                elif resultado == "rechazada":
                    _fallar_pago(pago, "procesamiento_fallido", "No se pudo completar el pago.")
                db.session.commit()
            except Exception:
                db.session.rollback()

    if delay and delay > 0:
        timer = threading.Timer(delay, ejecutar)
        timer.daemon = True
        timer.start()
    else:
        ejecutar()


def obtener_pago(id_pago, usuario):
    pago = db.session.get(Pago, id_pago)
    if pago is None:
        return None
    _asegurar_pago_vigente(pago, commit=True)
    contrato = pago.contrato
    if contrato is None:
        return None
    if getattr(usuario, "tipo_usuario", None) != "admin" and usuario.id not in (contrato.id_cliente, contrato.id_desarrollador):
        return None
    return pago


def confirmar_pago(pago_id, firma, timestamp):
    """Confirmación firmada del proveedor simulado."""
    secreto = os.environ.get("PAGOS_WEBHOOK_SECRET", "dev-webhook-secret")
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        raise ConfirmacionInvalidaError("La confirmación del pago no es válida.")
    if abs(time.time() - ts) > 300:
        raise ConfirmacionInvalidaError("La confirmación del pago no es válida.")
    mensaje = f"{ts}:{pago_id}"
    firma_calculada = hmac.new(secreto.encode(), mensaje.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(firma_calculada, str(firma or "")):
        raise ConfirmacionInvalidaError("La confirmación del pago no es válida.")

    pago = db.session.get(Pago, pago_id)
    if pago is None:
        raise PagoNoEncontradoError()
    _asegurar_pago_vigente(pago, commit=False)
    if pago.estado_escrow in ("retenido", "fallido", "liberado", "reembolsado", "dividido"):
        db.session.commit()
        return pago  # idempotente / ya resuelto
    if pago.estado_escrow != "pendiente":
        raise TransicionEstadoPagoInvalidaError()

    # En simulación, confirmación firmada válida aprueba el pago pendiente.
    _confirmar_como_retenido(pago)
    db.session.commit()
    return pago


def verificar_pago(pago, codigo):
    if pago is None:
        raise PagoNoEncontradoError()
    _asegurar_pago_vigente(pago, commit=False)
    if pago.estado_escrow != "pendiente":
        if pago.estado_escrow == "fallido" and pago.codigo_fallo == "expirado":
            db.session.commit()
            raise PagoExpiradoError()
        db.session.commit()
        raise PagoNoPendienteError()

    if str(codigo or "").strip() == CODIGO_VERIFICACION_PRUEBA:
        _confirmar_como_retenido(pago)
        db.session.commit()
        return pago

    pago.intentos_verificacion = int(pago.intentos_verificacion or 0) + 1
    if pago.intentos_verificacion >= 3:
        _fallar_pago(pago, "verificacion_fallida", "La verificación del pago no fue exitosa.")
        db.session.commit()
        raise VerificacionInvalidaError("La verificación del pago no fue exitosa.")
    db.session.commit()
    raise VerificacionInvalidaError("El código de verificación no es válido.")


def listar_pagos_contrato(id_contrato, usuario):
    contrato = contrato_de_usuario(id_contrato, usuario)
    if contrato is None:
        return None
    pagos = sorted(contrato.pagos or [], key=lambda p: p.fecha_pago or datetime.min)
    cambiado = False
    for p in pagos:
        antes = p.estado_escrow
        _asegurar_pago_vigente(p, commit=False)
        if p.estado_escrow != antes:
            cambiado = True
    if cambiado:
        db.session.commit()
    return pagos



def obtener_resumen_contrato(id_contrato, usuario):
    contrato = contrato_de_usuario(id_contrato, usuario)
    if contrato is None:
        return None
    pagos = listar_pagos_contrato(id_contrato, usuario) or []
    costo = _money(contrato.costo_acordado)
    depositado = Decimal("0.00")
    en_custodia = Decimal("0.00")
    liberado_total = Decimal("0.00")
    ahora = _ahora()
    vigentes = Decimal("0.00")
    for p in pagos:
        monto = _money(p.monto)
        lib_p = _total_liberado(p.id)
        liberado_total += lib_p
        estado = p.estado_escrow
        if estado in ("retenido", "liberado", "dividido"):
            vigentes += monto
            depositado += monto
        elif estado == "pendiente" and not _pago_expirado(p, ahora):
            vigentes += monto
            depositado += monto
        if estado == "retenido":
            saldo = monto - lib_p
            if saldo > 0:
                en_custodia += saldo
    por_depositar = costo - vigentes
    if por_depositar < 0:
        por_depositar = Decimal("0.00")
    moneda = "MXN"
    if pagos and getattr(pagos[0], "moneda", None):
        moneda = pagos[0].moneda
    return {
        "id_contrato": contrato.id,
        "costo_acordado": format(_money(costo), "f"),
        "moneda": moneda,
        "depositado": format(_money(depositado), "f"),
        "en_custodia": format(_money(en_custodia), "f"),
        "liberado": format(_money(liberado_total), "f"),
        "por_depositar": format(_money(por_depositar), "f"),
    }


# ---------------------------------------------------------------------------
# Liberaciones
# ---------------------------------------------------------------------------


def _hay_disputa_activa_contrato(contrato_id):
    return db.session.execute(
        db.select(Disputa.id).where(
            Disputa.id_contrato == contrato_id,
            Disputa.estado.in_(["abierta", "en_revision"]),
        )
    ).first() is not None


def crear_liberacion(pago, usuario, monto_liberado, id_entregable=None, motivo=None):
    if pago is None:
        raise PagoNoEncontradoError()

    with _lock_liberacion(pago.id):
        pago_bloqueado = db.session.execute(
            db.select(Pago).where(Pago.id == pago.id).with_for_update()
        ).scalar_one_or_none()
        if pago_bloqueado is None:
            raise PagoNoEncontradoError()
        contrato = pago_bloqueado.contrato
        if contrato is None:
            raise ContratoNoEncontradoError()

        if getattr(usuario, "tipo_usuario", None) != "admin" and usuario.id != contrato.id_cliente:
            raise PagoPermisoError("No tienes permiso para liberar fondos de este pago.")

        _asegurar_pago_vigente(pago_bloqueado, commit=False)
        if pago_bloqueado.estado_escrow != "retenido":
            raise PagoNoRetenidoError()

        try:
            monto_d = _money(monto_liberado)
        except Exception:
            raise MontoInvalidoError("El monto indicado no es válido.")
        if monto_d <= 0:
            raise MontoInvalidoError("El monto a liberar debe ser mayor a 0.")

        if id_entregable is not None:
            entregable = db.session.get(Entregable, id_entregable)
            if entregable is None or entregable.id_contrato != contrato.id:
                raise EntregableInvalidoError("El entregable seleccionado no pertenece a este contrato.")
            if entregable.estado != "aprobado":
                raise EntregableInvalidoError("Solo puedes liberar fondos contra un entregable aprobado.")
        else:
            entregable = None

        if _hay_disputa_activa_contrato(contrato.id):
            raise DisputaActivaError()

        ya_liberado = _total_liberado(pago_bloqueado.id)
        saldo = _money(_money(pago_bloqueado.monto) - ya_liberado)
        if monto_d > saldo:
            raise SaldoInsuficienteError()

        liberacion = Liberacion(
            id_pago=pago_bloqueado.id,
            id_usuario=usuario.id,
            id_entregable=id_entregable if entregable else None,
            monto_liberado=float(monto_d),
            motivo=motivo,
            fecha_hora=_ahora(),
        )
        db.session.add(liberacion)

        nuevo_liberado = _money(ya_liberado + monto_d)
        if nuevo_liberado >= _money(pago_bloqueado.monto):
            _transicionar_pago(pago_bloqueado, "liberado")
            pago_bloqueado.fecha_liberacion = _ahora()
        else:
            # permanece retenido (parcial)
            pago_bloqueado.estado_escrow = "retenido"

        db.session.flush()
        return liberacion


def listar_liberaciones_pago(id_pago, usuario):
    pago = obtener_pago(id_pago, usuario)
    if pago is None:
        return None
    return list(pago.liberaciones or [])


# ---------------------------------------------------------------------------
# Recibos
# ---------------------------------------------------------------------------


def obtener_recibo_pago(id_pago, usuario):
    pago = obtener_pago(id_pago, usuario)
    if pago is None:
        return None
    return db.session.execute(db.select(Recibo).filter_by(id_pago=id_pago)).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Disputas
# ---------------------------------------------------------------------------


def _origen_disputa_query(id_contrato, id_pago=None, id_entregable=None):
    stmt = db.select(Disputa).where(
        Disputa.id_contrato == id_contrato,
        Disputa.estado.in_(["abierta", "en_revision"]),
    )
    if id_pago is not None:
        stmt = stmt.where(Disputa.id_pago == id_pago)
    elif id_entregable is not None:
        stmt = stmt.where(Disputa.id_entregable == id_entregable)
    else:
        stmt = stmt.where(Disputa.id_pago.is_(None), Disputa.id_entregable.is_(None))
    return stmt


def abrir_disputa(contrato, reportante, tipo, descripcion, id_pago=None, id_entregable=None, id_incidencia=None):
    if contrato is None:
        raise ContratoNoEncontradoError()
    if not _es_parte_contrato(contrato, reportante):
        raise PagoPermisoError("Solo las partes del contrato pueden abrir una disputa.")
    if contrato.estado in ("finalizado", "cancelado"):
        raise PagoValidacionError("No se puede abrir una disputa en un contrato cerrado.", codigo="contrato_cerrado", status_code=409)

    if id_pago is not None and id_entregable is not None:
        raise DisputaOrigenInvalidoError("La disputa debe tener un único origen.")

    pago = None
    entregable = None
    if id_pago is not None:
        pago = db.session.get(Pago, id_pago)
        if pago is None or pago.id_contrato != contrato.id:
            raise DisputaOrigenInvalidoError("El pago seleccionado no pertenece a este contrato.")
    if id_entregable is not None:
        entregable = db.session.get(Entregable, id_entregable)
        if entregable is None or entregable.id_contrato != contrato.id:
            raise DisputaOrigenInvalidoError("El entregable seleccionado no pertenece a este contrato.")

    if id_incidencia is not None:
        from app.comunicacion.models import Incidencia

        incidencia = db.session.get(Incidencia, id_incidencia)
        if incidencia is None:
            raise RecursoNoEncontradoError("No se encontró la incidencia indicada.")
        existente_incidencia = db.session.execute(
            db.select(Disputa).where(Disputa.id_incidencia == id_incidencia)
        ).scalar_one_or_none()
        if existente_incidencia is not None:
            raise IncidenciaYaEscaladaError()
        if getattr(incidencia, "id_contrato", None) is not None and incidencia.id_contrato != contrato.id:
            raise DisputaOrigenInvalidoError("La incidencia indicada no pertenece a este contrato.")

    # Una sola disputa abierta por origen (contrato general / pago / entregable)
    existente = db.session.execute(_origen_disputa_query(contrato.id, id_pago, id_entregable)).scalars().first()
    if existente is not None:
        raise DisputaDuplicadaError()

    tipo = (tipo or "").strip() or "otro"
    descripcion = (descripcion or "").strip()
    if not descripcion:
        raise PagoValidacionError("La descripción es obligatoria.", errores={"descripcion": "La descripción es obligatoria."})

    disputa = Disputa(
        id_contrato=contrato.id,
        id_reportante=reportante.id,
        id_pago=id_pago,
        id_entregable=id_entregable,
        id_incidencia=id_incidencia,
        tipo=tipo,
        descripcion=descripcion,
        estado="abierta",
        fecha_hora_publicacion=_ahora(),
    )
    db.session.add(disputa)
    db.session.flush()
    return disputa


def obtener_disputa(id_disputa, usuario):
    disputa = db.session.get(Disputa, id_disputa)
    if disputa is None:
        return None
    contrato = disputa.contrato
    if getattr(usuario, "tipo_usuario", None) == "admin":
        return disputa
    if usuario.id not in (contrato.id_cliente, contrato.id_desarrollador):
        return None
    return disputa


def listar_disputas(usuario):
    stmt = db.select(Disputa).order_by(Disputa.fecha_hora_publicacion.desc())
    if getattr(usuario, "tipo_usuario", None) != "admin":
        stmt = stmt.join(Contrato).where(
            or_(
                Disputa.id_reportante == usuario.id,
                Contrato.id_cliente == usuario.id,
                Contrato.id_desarrollador == usuario.id,
            )
        )
    return db.session.execute(stmt).scalars().all()


def atender_disputa(disputa, admin):
    if disputa is None:
        raise DisputaNoEncontradaError()
    if getattr(admin, "tipo_usuario", None) != "admin":
        raise PagoPermisoError("Solo un administrador puede tomar esta disputa.")
    if disputa.estado != "abierta":
        raise TransicionEstadoDisputaInvalidaError("La disputa no se encuentra en un estado que permita tomarla.")
    disputa.id_admin = admin.id
    _transicionar_disputa(disputa, "en_revision")
    return disputa


# ---------------------------------------------------------------------------
# Arbitraje
# ---------------------------------------------------------------------------


def _aplicar_liberacion_total_arbitraje(pago, usuario_admin):
    pago = db.session.execute(db.select(Pago).where(Pago.id == pago.id).with_for_update()).scalar_one()
    _asegurar_pago_vigente(pago, commit=False)
    if pago.estado_escrow not in ("retenido",):
        # si ya no está retenido, no se fuerza otra transición inválida
        return pago
    saldo = _saldo_no_liberado(pago)
    if saldo > 0:
        db.session.add(
            Liberacion(
                id_pago=pago.id,
                id_usuario=usuario_admin.id,
                monto_liberado=float(saldo),
                motivo="Arbitraje: liberar",
                fecha_hora=_ahora(),
            )
        )
    _transicionar_pago(pago, "liberado")
    pago.fecha_liberacion = _ahora()
    return pago


def _aplicar_reembolso_arbitraje(pago, usuario_admin):
    pago = db.session.execute(db.select(Pago).where(Pago.id == pago.id).with_for_update()).scalar_one()
    _asegurar_pago_vigente(pago, commit=False)
    if pago.estado_escrow != "retenido":
        return pago
    saldo = _saldo_no_liberado(pago)
    if saldo > 0:
        # Llamada al proveedor simulado; si falla, la transacción completa debe revertirse.
        reembolso_id = proveedor_pago.reembolsar(pago.transaccion_id, float(saldo))
        pago.reembolso_id = reembolso_id
        pago.fecha_reembolso = _ahora()
    _transicionar_pago(pago, "reembolsado")
    pago.fecha_liberacion = _ahora()
    return pago


def _aplicar_division_arbitraje(pago, usuario_admin, porcentaje_desarrollador):
    pago = db.session.execute(db.select(Pago).where(Pago.id == pago.id).with_for_update()).scalar_one()
    _asegurar_pago_vigente(pago, commit=False)
    if pago.estado_escrow != "retenido":
        return pago
    saldo = _saldo_no_liberado(pago)
    pct = Decimal(str(porcentaje_desarrollador))
    # Redondeo explícito a centavos: parte dev se redondea hacia abajo, resto al cliente,
    # garantizando que dev + cliente == saldo.
    parte_dev = (saldo * pct / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    if parte_dev > saldo:
        parte_dev = saldo
    parte_cliente = _money(saldo - parte_dev)
    # Ajuste final de consistencia por redondeo
    if parte_dev + parte_cliente != saldo:
        parte_cliente = _money(saldo - parte_dev)
    if parte_dev + parte_cliente != saldo:
        # último recurso: asignar diferencia al cliente
        parte_cliente = saldo - parte_dev

    if parte_dev > 0:
        db.session.add(
            Liberacion(
                id_pago=pago.id,
                id_usuario=usuario_admin.id,
                monto_liberado=float(parte_dev),
                motivo="Arbitraje: dividir",
                fecha_hora=_ahora(),
            )
        )
    if parte_cliente > 0:
        reembolso_id = proveedor_pago.reembolsar(pago.transaccion_id, float(parte_cliente))
        pago.reembolso_id = reembolso_id
        pago.fecha_reembolso = _ahora()

    _transicionar_pago(pago, "dividido")
    pago.fecha_liberacion = _ahora()
    return pago


def crear_arbitraje(disputa, arbitro, decision, porcentaje=None, notas=None):
    if disputa is None:
        raise DisputaNoEncontradaError()
    if getattr(arbitro, "tipo_usuario", None) != "admin":
        raise PagoPermisoError("Solo un administrador puede registrar una decisión de arbitraje.")
    if disputa.estado in ("resuelta", "cerrada"):
        raise ArbitrajeInvalidoError("La disputa ya se encuentra resuelta.")

    existente = db.session.execute(db.select(Arbitraje).filter_by(id_disputa=disputa.id)).scalar_one_or_none()
    if existente is not None:
        raise ArbitrajeDuplicadoError()

    # Si está abierta, tomar en revisión dentro de la misma transacción antes de resolver.
    # Si algo falla después, el llamador revierte todo (incluido este paso).
    if disputa.estado == "abierta":
        atender_disputa(disputa, arbitro)
    if disputa.estado != "en_revision":
        raise TransicionEstadoDisputaInvalidaError()

    if decision not in ("liberar", "reembolsar", "dividir"):
        raise ArbitrajeInvalidoError("La decisión indicada no es válida.", errores={"decision": "La decisión indicada no es válida."})

    porcentaje_val = None
    if decision == "dividir":
        if porcentaje is None or porcentaje == "":
            raise ArbitrajeInvalidoError("Debes indicar el porcentaje para el desarrollador.", errores={"porcentaje_desarrollador": "Debes indicar el porcentaje para el desarrollador."})
        try:
            porcentaje_val = float(Decimal(str(porcentaje)))
        except Exception:
            raise ArbitrajeInvalidoError("El porcentaje indicado no es válido.", errores={"porcentaje_desarrollador": "El porcentaje indicado no es válido."})
        if porcentaje_val < 0 or porcentaje_val > 100:
            raise ArbitrajeInvalidoError("El porcentaje debe estar entre 0 y 100.", errores={"porcentaje_desarrollador": "El porcentaje debe estar entre 0 y 100."})
    elif porcentaje is not None and porcentaje != "":
        try:
            porcentaje_val = float(Decimal(str(porcentaje)))
        except Exception:
            porcentaje_val = None

    # Determinar pagos afectados
    pagos_afectados = []
    if disputa.id_pago is not None:
        pago = db.session.get(Pago, disputa.id_pago)
        if pago is not None:
            pagos_afectados = [pago]
    else:
        # TODO: disputa sin origen específico o asociada a entregable: se aplica sobre pagos
        # retenidos del contrato. Cada pago se procesa con su propia liberación/reembolso.
        pagos_afectados = [p for p in (disputa.contrato.pagos or []) if p.estado_escrow == "retenido"]

    arbitraje = Arbitraje(
        id_disputa=disputa.id,
        id_arbitro=arbitro.id,
        decision=decision,
        porcentaje_desarrollador=porcentaje_val,
        notas=(notas or "").strip() or None,
        fecha_hora=_ahora(),
    )
    db.session.add(arbitraje)

    disputa.id_admin = arbitro.id
    disputa.resolucion = (notas or "").strip() or None

    # Aplicar decisión dentro de la misma transacción. Si el reembolso simulado falla,
    # se propaga la excepción y el llamador debe hacer rollback de todo.
    for pago in pagos_afectados:
        if decision == "liberar":
            _aplicar_liberacion_total_arbitraje(pago, arbitro)
        elif decision == "reembolsar":
            _aplicar_reembolso_arbitraje(pago, arbitro)
        elif decision == "dividir":
            _aplicar_division_arbitraje(pago, arbitro, porcentaje_val)

    disputa.fecha_hora_resolucion = _ahora()
    _transicionar_disputa(disputa, "resuelta")
    db.session.flush()
    return arbitraje


def obtener_arbitraje_disputa(id_disputa, usuario):
    disputa = obtener_disputa(id_disputa, usuario)
    if disputa is None:
        return None
    return db.session.execute(db.select(Arbitraje).filter_by(id_disputa=disputa.id)).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Compatibilidad / helpers legacy
# ---------------------------------------------------------------------------


def depositar_escrow(contrato):
    """Crea el pago inicial (escrow) de un contrato si no existe."""
    existente = db.session.execute(db.select(Pago).filter_by(id_contrato=contrato.id)).scalars().first()
    if existente:
        return existente

    pago = Pago(
        id_contrato=contrato.id,
        monto=float(_money(contrato.costo_acordado)),
        estado_escrow="retenido",
        metodo_pago="simulado",
        transaccion_id=f"TX-{uuid.uuid4().hex[:12].upper()}",
        moneda="MXN",
        proveedor="simulado",
        marca_tarjeta=None,
        ultimos4=None,
        intentos_verificacion=0,
        fecha_confirmacion=_ahora(),
    )
    db.session.add(pago)
    db.session.flush()
    generar_recibo(pago)
    return pago


# Alias de compatibilidad con nombres usados históricamente
def listar_pagos(id_contrato, usuario):
    return listar_pagos_contrato(id_contrato, usuario)


def atender(DisputaObj, admin):
    return atender_disputa(DisputaObj, admin)
