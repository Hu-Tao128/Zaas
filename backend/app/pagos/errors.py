"""Errores de dominio del módulo de pagos."""

from __future__ import annotations


class PagoError(Exception):
    """Error base de dominio para pagos."""

    codigo = "pago_error"
    mensaje = "No se pudo completar la operación."
    status_code = 400

    def __init__(self, mensaje: str | None = None, codigo: str | None = None, status_code: int | None = None, errores: dict | None = None):
        self.mensaje = mensaje or self.mensaje
        self.codigo = codigo or self.codigo
        self.status_code = status_code or self.status_code
        self.errores = errores or {}
        super().__init__(self.mensaje)


class PagoValidacionError(PagoError, ValueError):
    codigo = "validacion_invalida"


class PagoPermisoError(PagoError, PermissionError):
    codigo = "permiso_denegado"
    mensaje = "No tienes permiso para realizar esta acción."
    status_code = 403


class PagoNoEncontradoError(PagoValidacionError):
    codigo = "pago_no_encontrado"
    mensaje = "No se encontró el pago solicitado."
    status_code = 404


class ContratoNoEncontradoError(PagoValidacionError):
    codigo = "contrato_no_encontrado"
    mensaje = "No se encontró el contrato solicitado."
    status_code = 404


class ContratoNoAptoError(PagoValidacionError):
    codigo = "contrato_no_apto"
    mensaje = "Este contrato aún no admite pagos."
    status_code = 409


class MontoInvalidoError(PagoValidacionError):
    codigo = "monto_invalido"
    mensaje = "El monto indicado no es válido."


class TopeContratoSuperadoError(PagoValidacionError):
    codigo = "tope_contrato_superado"
    mensaje = "La suma de pagos vigentes supera el costo acordado del contrato."


class TarjetaNoAdmitidaError(PagoValidacionError):
    codigo = "tarjeta_no_admitida"
    mensaje = "El medio de pago no es válido para esta operación."
    status_code = 422


class IdempotenciaConflictoError(PagoValidacionError):
    codigo = "idempotencia_conflicto"
    mensaje = "La clave de idempotencia ya fue usada con datos distintos."
    status_code = 409


class TransicionEstadoPagoInvalidaError(PagoValidacionError):
    codigo = "transicion_pago_invalida"
    mensaje = "No es posible cambiar el estado del pago en su situación actual."
    status_code = 409


class PagoNoRetenidoError(PagoValidacionError):
    codigo = "pago_no_retenido"
    mensaje = "El pago no tiene fondos retenidos disponibles para esta acción."
    status_code = 409


class SaldoInsuficienteError(PagoValidacionError):
    codigo = "saldo_insuficiente"
    mensaje = "El monto supera el saldo disponible de este pago."


class EntregableInvalidoError(PagoValidacionError):
    codigo = "entregable_invalido"
    mensaje = "El entregable seleccionado no es válido para esta operación."


class DisputaActivaError(PagoValidacionError):
    codigo = "disputa_activa"
    mensaje = "No se pueden liberar fondos mientras haya una disputa en curso."
    status_code = 409


class DisputaNoEncontradaError(PagoValidacionError):
    codigo = "disputa_no_encontrada"
    mensaje = "No se encontró la disputa solicitada."
    status_code = 404


class DisputaOrigenInvalidoError(PagoValidacionError):
    codigo = "disputa_origen_invalido"
    mensaje = "El origen de la disputa no es válido."


class DisputaDuplicadaError(PagoValidacionError):
    codigo = "disputa_duplicada"
    mensaje = "Ya existe una disputa abierta para este origen."
    status_code = 409


class IncidenciaYaEscaladaError(PagoValidacionError):
    codigo = "incidencia_ya_escalada"
    mensaje = "La incidencia ya está vinculada a una disputa."
    status_code = 409


class TransicionEstadoDisputaInvalidaError(PagoValidacionError):
    codigo = "transicion_disputa_invalida"
    mensaje = "No es posible cambiar el estado de la disputa en su situación actual."
    status_code = 409


class ArbitrajeInvalidoError(PagoValidacionError):
    codigo = "arbitraje_invalido"
    mensaje = "No se pudo registrar la decisión de arbitraje."
    status_code = 409


class ArbitrajeDuplicadoError(PagoValidacionError):
    codigo = "arbitraje_duplicado"
    mensaje = "Esta disputa ya cuenta con una decisión registrada."
    status_code = 409


class ReembolsoError(PagoValidacionError):
    codigo = "reembolso_fallido"
    mensaje = "No se pudo completar el reembolso simulado."
    status_code = 409


class ConfirmacionInvalidaError(PagoValidacionError):
    codigo = "confirmacion_invalida"
    mensaje = "La confirmación del pago no es válida."
    status_code = 400


class VerificacionInvalidaError(PagoValidacionError):
    codigo = "verificacion_invalida"
    mensaje = "La verificación del pago no es válida."
    status_code = 400


class PagoNoPendienteError(PagoValidacionError):
    codigo = "pago_no_pendiente"
    mensaje = "El pago no se encuentra pendiente."
    status_code = 409


class PagoExpiradoError(PagoValidacionError):
    codigo = "pago_expirado"
    mensaje = "El pago expiró y ya no puede completarse."
    status_code = 409


class RecursoNoEncontradoError(PagoValidacionError):
    codigo = "recurso_no_encontrado"
    mensaje = "No se encontró el recurso solicitado."
    status_code = 404
