"""Consolida las migraciones del Modelo Relacional y del módulo de pagos.

Ejecutar desde ``backend`` después de configurar ``DATABASE_URL``:

    python migrate_mr.py

Soporta PostgreSQL (incluido Supabase) y SQLite para desarrollo local. El
script es idempotente: crea tablas faltantes, agrega columnas, migra los
campos legados del perfil y crea índices después de validar duplicados.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text

from app import create_app
from app.auth.models import Perfil
from app.auth.perfil_utils import sincronizar_habilidades, sincronizar_tecnologias
from app.extensions import db


# Columnas que fueron agregadas en migraciones previas. Los tipos son válidos
# tanto en PostgreSQL como SQLite.
COLUMNAS_NUEVAS = {
    "contrato": {
        "id_plantilla": "INTEGER",
        "notas": "TEXT",
        "monto_negociable": "BOOLEAN NOT NULL DEFAULT FALSE",
        "rechazado": "BOOLEAN NOT NULL DEFAULT FALSE",
        "motivo_rechazo": "TEXT",
        "fecha_rechazo": "TIMESTAMP",
        "id_rechazado_por": "INTEGER",
    },
    "proyecto": {"precio_negociable": "BOOLEAN NOT NULL DEFAULT FALSE"},
    "postulacion": {"costo_negociable": "BOOLEAN NOT NULL DEFAULT FALSE"},
    "pago": {
        "metodo_pago": "VARCHAR(50)",
        "transaccion_id": "VARCHAR(100)",
        "moneda": "VARCHAR(3) NOT NULL DEFAULT 'MXN'",
        "proveedor": "VARCHAR(30)",
        "marca_tarjeta": "VARCHAR(20)",
        "ultimos4": "VARCHAR(4)",
        "codigo_fallo": "VARCHAR(50)",
        "mensaje_fallo": "VARCHAR(200)",
        "idempotency_key": "VARCHAR(64)",
        "fecha_confirmacion": "TIMESTAMP",
        "reembolso_id": "VARCHAR(100)",
        "fecha_reembolso": "TIMESTAMP",
        "intentos_verificacion": "INTEGER NOT NULL DEFAULT 0",
    },
    "liberacion": {"id_entregable": "INTEGER"},
    "recibo": {"total": "DOUBLE PRECISION"},
    "disputa": {
        "id_pago": "INTEGER",
        "id_entregable": "INTEGER",
        "id_incidencia": "INTEGER",
    },
    "incidencia": {"id_contrato": "INTEGER", "tipo_detalle": "VARCHAR(100)"},
}

INDICES_UNICOS = [
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_perfil_id_usuario ON perfil (id_usuario)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_postulacion_oferta_dev ON postulacion (id_oferta, id_desarrollador)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_perfil_habilidad ON perfil_habilidad (id_perfil, id_habilidad)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_perfil_tecnologia ON perfil_tecnologia (id_perfil, id_tecnologia)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_categoria_proyecto ON categoria_proyecto (id_proyecto, id_categoria)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_tecnologia_proyecto ON tecnologia_proyecto (id_proyecto, id_tecnologia)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_recibo_id_pago ON recibo (id_pago)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_recibo_folio_integridad ON recibo (folio)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_arbitraje_disputa ON arbitraje (id_disputa)",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_transaccion ON pago (transaccion_id) WHERE transaccion_id IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_idempotency ON pago (idempotency_key) WHERE idempotency_key IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_incidencia ON disputa (id_incidencia) WHERE id_incidencia IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_contrato_cliente_producto_activo ON contrato (id_cliente, id_producto) WHERE id_producto IS NOT NULL AND estado <> 'cancelado'",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_contrato_encargo_activo ON contrato (id_encargo) WHERE id_encargo IS NOT NULL AND estado <> 'cancelado'",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_abierta_contrato ON disputa (id_contrato) WHERE estado IN ('abierta','en_revision') AND id_pago IS NULL AND id_entregable IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_abierta_pago ON disputa (id_pago) WHERE estado IN ('abierta','en_revision') AND id_pago IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_abierta_entregable ON disputa (id_entregable) WHERE estado IN ('abierta','en_revision') AND id_entregable IS NOT NULL",
]


def _columnas(conexion, tabla):
    try:
        return {columna["name"] for columna in inspect(conexion).get_columns(tabla)}
    except Exception:
        return set()


def _validar_sin_duplicados(conexion, tabla, campo, etiqueta, where=""):
    sql = f"""SELECT {campo}, COUNT(*) AS cantidad
              FROM {tabla} {where}
              GROUP BY {campo} HAVING COUNT(*) > 1"""
    filas = conexion.execute(text(sql)).mappings().all()
    campos = [nombre.strip() for nombre in campo.split(",")]
    errores = []
    for fila in filas:
        claves = ", ".join(f"{nombre}:{fila[nombre]}" for nombre in campos)
        errores.append(f"{etiqueta} ({claves}): {fila['cantidad']} filas")
    return errores


def _validar_datos(conexion):
    errores = []
    consultas = [
        ("pago", "SELECT id FROM pago WHERE monto IS NULL OR monto <= 0", "monto inválido"),
        ("liberacion", "SELECT id FROM liberacion WHERE monto_liberado IS NULL OR monto_liberado <= 0", "monto_liberado inválido"),
        ("pago", "SELECT id FROM pago WHERE estado_escrow NOT IN ('pendiente','fallido','retenido','liberado','reembolsado','dividido')", "estado_escrow inválido"),
        ("disputa", "SELECT id FROM disputa WHERE estado NOT IN ('abierta','en_revision','resuelta','cerrada')", "estado inválido"),
        ("arbitraje", "SELECT id FROM arbitraje WHERE decision NOT IN ('liberar','reembolsar','dividir')", "decisión inválida"),
        ("arbitraje", "SELECT id FROM arbitraje WHERE decision IS NULL OR TRIM(decision)=''", "decisión vacía"),
        ("disputa", "SELECT id FROM disputa WHERE id_pago IS NOT NULL AND id_entregable IS NOT NULL", "tiene pago y entregable"),
        ("arbitraje", "SELECT id FROM arbitraje WHERE porcentaje_desarrollador IS NOT NULL AND (porcentaje_desarrollador < 0 OR porcentaje_desarrollador > 100)", "porcentaje fuera de rango"),
        ("disputa", "SELECT id FROM disputa WHERE tipo IS NULL OR TRIM(tipo)='' OR descripcion IS NULL OR TRIM(descripcion)=''", "tipo o descripción vacíos"),
    ]
    for tabla, sql, detalle in consultas:
        for fila in conexion.execute(text(sql)).mappings():
            errores.append(f"{tabla}.id={fila['id']}: {detalle}")

    errores.extend(_validar_sin_duplicados(conexion, "contrato", "id_cliente, id_producto", "contrato cliente+proyecto", "WHERE id_producto IS NOT NULL AND (estado IS NULL OR estado <> 'cancelado')"))
    errores.extend(_validar_sin_duplicados(conexion, "contrato", "id_encargo", "contrato encargo", "WHERE id_encargo IS NOT NULL AND (estado IS NULL OR estado <> 'cancelado')"))
    errores.extend(_validar_sin_duplicados(conexion, "recibo", "id_pago", "recibo id_pago"))
    errores.extend(_validar_sin_duplicados(conexion, "recibo", "folio", "recibo folio"))
    errores.extend(_validar_sin_duplicados(conexion, "arbitraje", "id_disputa", "arbitraje id_disputa"))
    errores.extend(_validar_sin_duplicados(conexion, "disputa", "id_incidencia", "disputa id_incidencia", "WHERE id_incidencia IS NOT NULL"))
    return errores


def _migrar_columnas(conexion):
    for tabla, columnas in COLUMNAS_NUEVAS.items():
        existentes = _columnas(conexion, tabla)
        if not existentes:
            print(f"  ! tabla {tabla} no existe; se omiten sus columnas")
            continue
        for nombre, tipo in columnas.items():
            if nombre not in existentes:
                conexion.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}"))
                print(f"  + {tabla}.{nombre}")
        if tabla == "pago" and "intentos_verificacion" in columnas:
            conexion.execute(text("UPDATE pago SET intentos_verificacion = 0 WHERE intentos_verificacion IS NULL"))


def _migrar_perfiles(conexion):
    columnas = _columnas(conexion, "perfil")
    legadas = [c for c in ("habilidades", "stack_tecnologico") if c in columnas]
    if not legadas:
        return
    campos = ", ".join(["id"] + legadas)
    for fila in conexion.execute(text(f"SELECT {campos} FROM perfil")).mappings():
        perfil = db.session.get(Perfil, fila["id"])
        if not perfil:
            continue
        if fila.get("habilidades"):
            sincronizar_habilidades(perfil, fila["habilidades"])
        if fila.get("stack_tecnologico"):
            sincronizar_tecnologias(perfil, fila["stack_tecnologico"])


def main():
    app = create_app()
    with app.app_context():
        # create_app/db.create_all crea las tablas faltantes desde los modelos.
        db.create_all()
        conexion = db.session.connection()
        _migrar_columnas(conexion)
        _migrar_perfiles(conexion)

        errores = _validar_datos(conexion)
        if errores:
            db.session.rollback()
            print("ERROR: los datos existentes impiden aplicar los índices:")
            for error in errores:
                print(f"  - {error}")
            raise SystemExit(1)

        for sentencia in INDICES_UNICOS:
            try:
                conexion.execute(text(sentencia))
            except Exception as error:
                db.session.rollback()
                print(f"ERROR al crear índice: {error}\nSQL: {sentencia}")
                raise SystemExit(1)

        # En PostgreSQL se pueden mantener los CHECK en una base ya existente
        # sin reconstruir la tabla (la antigua migración lo hacía solo en SQLite).
        if conexion.dialect.name == "postgresql":
            estados = "'pendiente','fallido','retenido','liberado','reembolsado','dividido'"
            constraint = conexion.execute(text("""
                SELECT pg_get_constraintdef(oid) AS definicion
                FROM pg_constraint
                WHERE conrelid = 'pago'::regclass AND conname = 'ck_pago_estado_escrow'
            """)).mappings().first()
            if constraint and "pendiente" not in constraint["definicion"]:
                conexion.execute(text("ALTER TABLE pago DROP CONSTRAINT ck_pago_estado_escrow"))
                constraint = None
            if not constraint:
                conexion.execute(text(
                    f"ALTER TABLE pago ADD CONSTRAINT ck_pago_estado_escrow "
                    f"CHECK (estado_escrow IN ({estados})) NOT VALID"
                ))
                conexion.execute(text("ALTER TABLE pago VALIDATE CONSTRAINT ck_pago_estado_escrow"))

        db.session.commit()
        print("Migración consolidada completada.")


if __name__ == "__main__":
    main()
