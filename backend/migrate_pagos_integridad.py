"""Migración aditiva de integridad para el módulo de Pagos.

Uso:
    python migrate_pagos_integridad.py
    python migrate_pagos_integridad.py downgrade

- Agrega columnas/índices faltantes de forma idempotente.
- Valida datos existentes antes de aplicar restricciones lógicas nuevas.
- No borra ni modifica filas de negocio.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db


def _columnas(conexion, tabla):
    try:
        filas = conexion.execute(text(f"PRAGMA table_info({tabla})")).mappings().all()
        return {f["name"] for f in filas}
    except Exception:
        insp = inspect(conexion)
        try:
            return {c["name"] for c in insp.get_columns(tabla)}
        except Exception:
            return set()


def _listar(conexion, sql):
    return conexion.execute(text(sql)).mappings().all()


def main():
    app = create_app()
    with app.app_context():
        # Asegura tablas base según modelos actuales
        db.create_all()
        conexion = db.session.connection()

        # 1) Columna aditiva para intentos de verificación (BD, no memoria)
        cols_pago = _columnas(conexion, "pago")
        if cols_pago and "intentos_verificacion" not in cols_pago:
            conexion.execute(text("ALTER TABLE pago ADD COLUMN intentos_verificacion INTEGER NOT NULL DEFAULT 0"))
            print("  + pago.intentos_verificacion")
        # Normalizar nulos/valores previos si existieran en motores que lo permitan
        try:
            conexion.execute(text("UPDATE pago SET intentos_verificacion = 0 WHERE intentos_verificacion IS NULL"))
        except Exception:
            pass

        # 2) Validar datos existentes que incumplan reglas críticas antes de reforzar
        errores = []

        # Montos inválidos
        for f in _listar(conexion, "SELECT id, monto FROM pago WHERE monto IS NULL OR monto <= 0"):
            errores.append(f"pago.id={f['id']}: monto inválido ({f['monto']})")
        for f in _listar(conexion, "SELECT id, monto_liberado FROM liberacion WHERE monto_liberado IS NULL OR monto_liberado <= 0"):
            errores.append(f"liberacion.id={f['id']}: monto_liberado inválido ({f['monto_liberado']})")

        # Estados inválidos
        for f in _listar(conexion, "SELECT id, estado_escrow FROM pago WHERE estado_escrow NOT IN ('pendiente','fallido','retenido','liberado','reembolsado','dividido')"):
            errores.append(f"pago.id={f['id']}: estado_escrow inválido ({f['estado_escrow']})")
        for f in _listar(conexion, "SELECT id, estado FROM disputa WHERE estado NOT IN ('abierta','en_revision','resuelta','cerrada')"):
            errores.append(f"disputa.id={f['id']}: estado inválido ({f['estado']})")
        for f in _listar(conexion, "SELECT id, decision FROM arbitraje WHERE decision NOT IN ('liberar','reembolsar','dividir')"):
            errores.append(f"arbitraje.id={f['id']}: decision inválida ({f['decision']})")

        # Disputa con pago y entregable a la vez
        for f in _listar(conexion, "SELECT id FROM disputa WHERE id_pago IS NOT NULL AND id_entregable IS NOT NULL"):
            errores.append(f"disputa.id={f['id']}: tiene pago y entregable a la vez")

        # Porcentajes fuera de rango
        for f in _listar(conexion, "SELECT id, porcentaje_desarrollador FROM arbitraje WHERE porcentaje_desarrollador IS NOT NULL AND (porcentaje_desarrollador < 0 OR porcentaje_desarrollador > 100)"):
            errores.append(f"arbitraje.id={f['id']}: porcentaje fuera de rango ({f['porcentaje_desarrollador']})")

        # Duplicados de recibo por pago (además de unique)
        for f in _listar(conexion, "SELECT id_pago, COUNT(*) AS n FROM recibo GROUP BY id_pago HAVING COUNT(*) > 1"):
            errores.append(f"recibo.id_pago={f['id_pago']}: recibos duplicados ({f['n']})")

        # Arbitrajes duplicados por disputa
        for f in _listar(conexion, "SELECT id_disputa, COUNT(*) AS n FROM arbitraje GROUP BY id_disputa HAVING COUNT(*) > 1"):
            errores.append(f"arbitraje.id_disputa={f['id_disputa']}: arbitrajes duplicados ({f['n']})")

        # Incidencia escalada más de una vez
        for f in _listar(conexion, "SELECT id_incidencia, COUNT(*) AS n FROM disputa WHERE id_incidencia IS NOT NULL GROUP BY id_incidencia HAVING COUNT(*) > 1"):
            errores.append(f"disputa.id_incidencia={f['id_incidencia']}: incidencia escalada en múltiples disputas ({f['n']})")

        # Disputas abiertas/en revisión duplicadas por origen
        for f in _listar(conexion, """
            SELECT id_contrato,
                   COALESCE(CAST(id_pago AS TEXT), 'null') AS id_pago,
                   COALESCE(CAST(id_entregable AS TEXT), 'null') AS id_entregable,
                   CASE WHEN id_pago IS NULL AND id_entregable IS NULL THEN 1 ELSE 0 END AS origen_contrato,
                   COUNT(*) AS n
            FROM disputa
            WHERE estado IN ('abierta','en_revision')
            GROUP BY id_contrato, origen_contrato, id_pago, id_entregable
            HAVING COUNT(*) > 1
        """):
            errores.append(
                "disputa origen duplicado abierto: "
                f"contrato={f['id_contrato']} pago={f['id_pago']} entregable={f['id_entregable']} cantidad={f['n']}"
            )

        if errores:
            db.session.rollback()
            print("ERROR: datos existentes incumplen restricciones/consistencia del módulo de Pagos:")
            for e in errores:
                print("  - " + e)
            raise SystemExit(1)

        # 3) Índices/uniques faltantes (idempotentes)
        indices = [
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_transaccion_id ON pago(transaccion_id) WHERE transaccion_id IS NOT NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_idempotency_key ON pago(idempotency_key) WHERE idempotency_key IS NOT NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_recibo_id_pago_integridad ON recibo(id_pago)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_recibo_folio_integridad ON recibo(folio)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_arbitraje_id_disputa_integridad ON arbitraje(id_disputa)",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_id_incidencia_integridad ON disputa(id_incidencia) WHERE id_incidencia IS NOT NULL",
            # Una sola disputa abierta/en revisión por origen (SQLite soporta índices parciales)
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_abierta_contrato ON disputa(id_contrato) WHERE estado IN ('abierta','en_revision') AND id_pago IS NULL AND id_entregable IS NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_abierta_pago ON disputa(id_pago) WHERE estado IN ('abierta','en_revision') AND id_pago IS NOT NULL",
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_abierta_entregable ON disputa(id_entregable) WHERE estado IN ('abierta','en_revision') AND id_entregable IS NOT NULL",
        ]
        for sql in indices:
            try:
                conexion.execute(text(sql))
            except Exception as exc:
                # No silencioso: si no se puede crear, fallar con detalle.
                db.session.rollback()
                print(f"ERROR: no se pudo crear índice requerido: {exc}\nSQL: {sql}")
                raise SystemExit(1)

        db.session.commit()
        print("Migración de integridad de Pagos completada.")


def downgrade():
    app = create_app()
    with app.app_context():
        conexion = db.session.connection()
        # Solo se eliminan índices creados por esta migración. No se eliminan columnas
        # para evitar pérdida de datos (SQLite requiere recrear tabla).
        indices = [
            "DROP INDEX IF EXISTS uq_pago_transaccion_id",
            "DROP INDEX IF EXISTS uq_pago_idempotency_key",
            "DROP INDEX IF EXISTS uq_recibo_id_pago_integridad",
            "DROP INDEX IF EXISTS uq_recibo_folio_integridad",
            "DROP INDEX IF EXISTS uq_arbitraje_id_disputa_integridad",
            "DROP INDEX IF EXISTS uq_disputa_id_incidencia_integridad",
            "DROP INDEX IF EXISTS uq_disputa_abierta_contrato",
            "DROP INDEX IF EXISTS uq_disputa_abierta_pago",
            "DROP INDEX IF EXISTS uq_disputa_abierta_entregable",
        ]
        for sql in indices:
            try:
                conexion.execute(text(sql))
            except Exception as exc:
                print(f"  ! No se pudo eliminar índice ({exc}): {sql}")
        db.session.commit()
        print("Downgrade de integridad de Pagos completado (columnas conservadas).")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        main()
