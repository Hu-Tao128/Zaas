from math import isfinite

from app.extensions import db
from app.models.iot import TelemetriaECBD


def _normalizar_float(valor):
    if valor is None:
        return None
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        return None
    if not isfinite(numero) or numero < 0:
        return None
    return numero


def _normalizar_entero(valor):
    if valor is None:
        return None
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None
    if numero < 0:
        return None
    return numero


def _serializar(registro):
    return {
        'id_registro': registro.id_registro,
        'id_dispositivo': registro.id_dispositivo,
        'tipo_evento': registro.tipo_evento,
        'modulo_evaluado': registro.modulo_evaluado,
        'latencia_ms': registro.latencia_ms,
        'memoria_libre_kb': registro.memoria_libre_kb,
        'anomalia_detectada': bool(registro.anomalia_detectada),
        'payload_crudo': registro.payload_crudo,
        'resumen_agente': registro.resumen_agente,
        'fecha_captura': (
            registro.fecha_captura.isoformat()
            if registro.fecha_captura is not None
            else None
        ),
    }


def ejecutar_etl_saneamiento():
    """Sanea telemetrías pendientes y marca cada registro como procesado."""
    pendientes = db.session.scalars(
        db.select(TelemetriaECBD).where(TelemetriaECBD.procesado_etl.is_(False))
    ).all()

    saneados = 0
    descartados = 0

    for registro in pendientes:
        latencia = _normalizar_float(registro.latencia_ms)
        memoria = _normalizar_entero(registro.memoria_libre_kb)
        payload_valido = isinstance(registro.payload_crudo, dict)

        if not payload_valido or (latencia is None and memoria is None):
            descartados += 1
        else:
            saneados += 1

        registro.latencia_ms = latencia if latencia is not None else 0.0
        registro.memoria_libre_kb = memoria if memoria is not None else 0
        modulo = (registro.modulo_evaluado or '').strip().lower()
        registro.modulo_evaluado = modulo or 'general'
        registro.payload_crudo = registro.payload_crudo if payload_valido else {}
        registro.procesado_etl = True

    db.session.commit()

    return {
        'saneados': saneados,
        'descartados': descartados,
        'total_procesados': saneados + descartados,
    }


def exportar_dataset_limpio(limite=500):
    """Devuelve registros procesados como diccionarios planos para modelado."""
    try:
        limite = int(limite)
    except (TypeError, ValueError):
        limite = 500
    limite = max(1, min(limite, 5000))

    registros = db.session.scalars(
        db.select(TelemetriaECBD)
        .where(TelemetriaECBD.procesado_etl.is_(True))
        .order_by(TelemetriaECBD.fecha_captura.desc(), TelemetriaECBD.id_registro.desc())
        .limit(limite)
    ).all()

    return [_serializar(registro) for registro in registros]


def obtener_kpis_dashboard():
    """Calcula métricas agregadas para el dashboard ECBD."""
    total_registros = db.session.scalar(
        db.select(db.func.count(TelemetriaECBD.id_registro))
    ) or 0

    total_anomalias = db.session.scalar(
        db.select(db.func.count(TelemetriaECBD.id_registro)).where(
            TelemetriaECBD.anomalia_detectada.is_(True)
        )
    ) or 0

    latencia_promedio = db.session.scalar(
        db.select(db.func.avg(TelemetriaECBD.latencia_ms))
    )

    filas_modulo = db.session.execute(
        db.select(
            TelemetriaECBD.modulo_evaluado,
            db.func.count(TelemetriaECBD.id_registro),
        ).group_by(TelemetriaECBD.modulo_evaluado)
    ).all()

    eventos_por_modulo = {
        (modulo or 'sin_modulo'): int(cantidad)
        for modulo, cantidad in filas_modulo
    }

    return {
        'total_registros': int(total_registros),
        'total_anomalias': int(total_anomalias),
        'latencia_promedio_ms': (
            round(float(latencia_promedio), 2)
            if latencia_promedio is not None
            else 0.0
        ),
        'eventos_por_modulo': eventos_por_modulo,
    }
