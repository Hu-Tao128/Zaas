"""Migración aditiva/reversible: incidencias.tipo_detalle y unicidad de contratos.

Uso:
    python migrate_incidencias_contratos.py
    python migrate_incidencias_contratos.py downgrade

- Agrega columna incidencia.tipo_detalle VARCHAR(100) NULL (idempotente).
- Detecta contratos existentes que violen los índices únicos parciales requeridos
  y falla con listado claro (sin corregir datos).
- Crea índices únicos parciales (PostgreSQL/SQLite):
    uq_contrato_cliente_producto_activo: (id_cliente, id_producto)
        WHERE id_producto IS NOT NULL AND estado <> 'cancelado'
    uq_contrato_encargo_activo: (id_encargo)
        WHERE id_encargo IS NOT NULL AND estado <> 'cancelado'
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app import create_app
from app.extensions import db


IDX_CLIENTE_PRODUCTO = "uq_contrato_cliente_producto_activo"
IDX_ENCARGO = "uq_contrato_encargo_activo"


def _columnas(conexion, tabla):
    try:
        filas = conexion.execute(text(f"PRAGMA table_info({tabla})")).mappings().all()
        if filas:
            return {f["name"] for f in filas}
    except Exception:
        pass
    try:
        insp = inspect(conexion)
        return {c["name"] for c in insp.get_columns(tabla)}
    except Exception:
        return set()


def _tabla_existe(conexion, tabla):
    try:
        insp = inspect(conexion)
        if tabla in insp.get_table_names():
            return True
    except Exception:
        pass
    try:
        row = conexion.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
            {"t": tabla},
        ).first()
        if row is not None:
            return True
    except Exception:
        pass
    try:
        row = conexion.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_name=:t"),
            {"t": tabla},
        ).first()
        if row is not None:
            return True
    except Exception:
        pass
    # probe directo (funciona si la tabla existe)
    try:
        conexion.execute(text(f'SELECT 1 FROM "{tabla}" WHERE 1=0'))
        return True
    except Exception:
        return False


def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        conexion = db.session.connection()

        # 1) incidencia.tipo_detalle (independiente e idempotente)
        if _tabla_existe(conexion, "incidencia"):
            cols = _columnas(conexion, "incidencia")
            if "tipo_detalle" not in cols:
                conexion.execute(text("ALTER TABLE incidencia ADD COLUMN tipo_detalle VARCHAR(100)"))
                db.session.commit()
                conexion = db.session.connection()
                print("  + incidencia.tipo_detalle")
            else:
                print("  = incidencia.tipo_detalle ya existe")
        else:
            print("  ! tabla incidencia no existe; omitiendo tipo_detalle")

        if not _tabla_existe(conexion, "contrato"):
            print("  ! tabla contrato no existe; omitiendo indices de unicidad")
            return

        # 2) Detectar conflictos antes de crear índices únicos parciales
        conflictos = []

        dup_producto = conexion.execute(text(
            """
            SELECT id_cliente, id_producto, COUNT(*) AS n,
                   GROUP_CONCAT(id) AS ids
            FROM contrato
            WHERE id_producto IS NOT NULL
              AND (estado IS NULL OR estado <> 'cancelado')
            GROUP BY id_cliente, id_producto
            HAVING COUNT(*) > 1
            """
        )).mappings().all()
        for f in dup_producto:
            conflictos.append(
                "contrato duplicado (cliente+proyecto, no cancelado): "
                f"id_cliente={f['id_cliente']} id_producto={f['id_producto']} "
                f"cantidad={f['n']} ids={f['ids']}"
            )

        dup_encargo = conexion.execute(text(
            """
            SELECT id_encargo, COUNT(*) AS n,
                   GROUP_CONCAT(id) AS ids
            FROM contrato
            WHERE id_encargo IS NOT NULL
              AND (estado IS NULL OR estado <> 'cancelado')
            GROUP BY id_encargo
            HAVING COUNT(*) > 1
            """
        )).mappings().all()
        for f in dup_encargo:
            conflictos.append(
                "contrato duplicado (encargo/oferta, no cancelado): "
                f"id_encargo={f['id_encargo']} cantidad={f['n']} ids={f['ids']}"
            )

        if conflictos:
            print("ERROR: existen contratos que incumplen las reglas de unicidad requeridas.")
            print("No se crearon los indices. Corrige/gestiona manualmente las filas listadas:")
            for c in conflictos:
                print("  - " + c)
            raise SystemExit(1)

        # 3) Crear indices unicos parciales (idempotente)
        stmts = [
            (
                f"CREATE UNIQUE INDEX IF NOT EXISTS {IDX_CLIENTE_PRODUCTO} "
                "ON contrato (id_cliente, id_producto) "
                "WHERE id_producto IS NOT NULL AND estado <> 'cancelado'"
            ),
            (
                f"CREATE UNIQUE INDEX IF NOT EXISTS {IDX_ENCARGO} "
                "ON contrato (id_encargo) "
                "WHERE id_encargo IS NOT NULL AND estado <> 'cancelado'"
            ),
        ]
        for sql in stmts:
            try:
                conexion.execute(text(sql))
                idx_name = IDX_CLIENTE_PRODUCTO if IDX_CLIENTE_PRODUCTO in sql else IDX_ENCARGO
                print(f"  + indice {idx_name}")
            except Exception as exc:
                db.session.rollback()
                print(f"ERROR: no se pudo crear indice requerido: {exc}\nSQL: {sql}")
                raise SystemExit(1)

        db.session.commit()
        print("Migracion incidencias/contratos completada.")


def downgrade():
    app = create_app()
    with app.app_context():
        conexion = db.session.connection()
        for idx in (IDX_CLIENTE_PRODUCTO, IDX_ENCARGO):
            try:
                conexion.execute(text(f"DROP INDEX IF EXISTS {idx}"))
                print(f"  - indice {idx}")
            except Exception as exc:
                print(f"  ! No se pudo eliminar indice {idx}: {exc}")
        # No se elimina columna tipo_detalle para evitar pérdida de datos (SQLite requiere recrear tabla).
        db.session.commit()
        print("Downgrade completado (columna incidencia.tipo_detalle conservada).")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "downgrade":
        downgrade()
    else:
        main()
