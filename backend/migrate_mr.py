"""Consolida el esquema del Modelo Relacional sobre Supabase/PostgreSQL.

Ejecutar desde ``backend`` después de configurar ``DATABASE_URL``:

    python migrate_mr.py

El script es idempotente: crea tablas faltantes (incluidas las de IoT), agrega
columnas, alinea restricciones/FKs conocidas y crea índices únicos después de
validar duplicados. SQLite ya no es un destino soportado en producción; solo se
usa como motor de pruebas.
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


# Columnas agregadas en migraciones previas. Tipos alineados con el esquema
# bigint/timestamptz de Supabase.
COLUMNAS_NUEVAS = {
    "contrato": {
        "id_plantilla": "BIGINT",
        "notas": "TEXT",
        "monto_negociable": "BOOLEAN NOT NULL DEFAULT FALSE",
        "rechazado": "BOOLEAN NOT NULL DEFAULT FALSE",
        "motivo_rechazo": "TEXT",
        "fecha_rechazo": "TIMESTAMPTZ",
        "id_rechazado_por": "BIGINT",
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
        "fecha_confirmacion": "TIMESTAMPTZ",
        "reembolso_id": "VARCHAR(100)",
        "fecha_reembolso": "TIMESTAMPTZ",
        "intentos_verificacion": "INTEGER NOT NULL DEFAULT 0",
    },
    "liberacion": {"id_entregable": "BIGINT"},
    "recibo": {"total": "DOUBLE PRECISION"},
    "disputa": {
        "id_pago": "BIGINT",
        "id_entregable": "BIGINT",
        "id_incidencia": "BIGINT",
    },
    "incidencia": {"id_contrato": "BIGINT", "tipo_detalle": "VARCHAR(100)"},
}

# Índices únicos que no están cubiertos por restricciones UNIQUE del esquema
# original. Los que ya existen como constraint se omiten para no duplicarlos.
INDICES_UNICOS = [
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_idempotency ON pago (idempotency_key) WHERE idempotency_key IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_contrato_cliente_producto_activo ON contrato (id_cliente, id_producto) WHERE id_producto IS NOT NULL AND (estado IS NULL OR estado <> 'cancelado')",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_contrato_encargo_activo ON contrato (id_encargo) WHERE id_encargo IS NOT NULL AND (estado IS NULL OR estado <> 'cancelado')",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_abierta_contrato ON disputa (id_contrato) WHERE estado IN ('abierta','en_revision') AND id_pago IS NULL AND id_entregable IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_abierta_pago ON disputa (id_pago) WHERE estado IN ('abierta','en_revision') AND id_pago IS NOT NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_abierta_entregable ON disputa (id_entregable) WHERE estado IN ('abierta','en_revision') AND id_entregable IS NOT NULL",
]

INDICES_ADICIONALES = [
    "CREATE INDEX IF NOT EXISTS idx_contrato_id_rechazado_por ON contrato (id_rechazado_por)",
]

# FKs que el esquema original de Supabase no tenía para columnas nuevas.
FOREIGN_KEYS = [
    (
        "contrato",
        "contrato_id_rechazado_por_fkey",
        "FOREIGN KEY (id_rechazado_por) REFERENCES usuario(id)",
    ),
    (
        "liberacion",
        "liberacion_id_entregable_fkey",
        "FOREIGN KEY (id_entregable) REFERENCES entregable(id)",
    ),
]


def _columnas(conexion, tabla):
    try:
        return {columna["name"] for columna in inspect(conexion).get_columns(tabla)}
    except Exception:
        return set()


def _definicion_constraint(conexion, tabla, nombre):
    fila = conexion.execute(
        text(
            """
            SELECT pg_get_constraintdef(oid) AS definicion
            FROM pg_constraint
            WHERE conrelid = CAST(:tabla AS regclass) AND conname = :nombre
            """
        ),
        {"tabla": tabla, "nombre": nombre},
    ).scalar()
    return fila


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
                conexion.execute(
                    text(f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {nombre} {tipo}")
                )
                print(f"  + {tabla}.{nombre}")
        if tabla == "pago" and "intentos_verificacion" in columnas:
            conexion.execute(
                text("UPDATE pago SET intentos_verificacion = 0 WHERE intentos_verificacion IS NULL")
            )


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


def _alinear_pago(conexion):
    """Alinea default y CHECKs de pago con los modelos de la aplicación."""
    conexion.execute(
        text("ALTER TABLE pago ALTER COLUMN estado_escrow SET DEFAULT 'pendiente'")
    )

    definicion = _definicion_constraint(conexion, "pago", "ck_pago_estado_escrow")
    if not definicion or "pendiente" not in definicion:
        conexion.execute(text("ALTER TABLE pago DROP CONSTRAINT IF EXISTS pago_estado_escrow_check"))
        conexion.execute(text("ALTER TABLE pago DROP CONSTRAINT IF EXISTS ck_pago_estado_escrow"))
        conexion.execute(
            text(
                "ALTER TABLE pago ADD CONSTRAINT ck_pago_estado_escrow "
                "CHECK (estado_escrow IN "
                "('pendiente','fallido','retenido','liberado','reembolsado','dividido')) NOT VALID"
            )
        )
        conexion.execute(text("ALTER TABLE pago VALIDATE CONSTRAINT ck_pago_estado_escrow"))

    definicion_monto = _definicion_constraint(conexion, "pago", "pago_monto_check")
    if not definicion_monto or ">=" in definicion_monto:
        conexion.execute(text("ALTER TABLE pago DROP CONSTRAINT IF EXISTS pago_monto_check"))
        conexion.execute(
            text("ALTER TABLE pago ADD CONSTRAINT pago_monto_check CHECK (monto > 0) NOT VALID")
        )
        conexion.execute(text("ALTER TABLE pago VALIDATE CONSTRAINT pago_monto_check"))

    definicion_liberacion = _definicion_constraint(
        conexion, "liberacion", "liberacion_monto_liberado_check"
    )
    if not definicion_liberacion or ">=" in definicion_liberacion:
        conexion.execute(
            text("ALTER TABLE liberacion DROP CONSTRAINT IF EXISTS liberacion_monto_liberado_check")
        )
        conexion.execute(
            text(
                "ALTER TABLE liberacion ADD CONSTRAINT liberacion_monto_liberado_check "
                "CHECK (monto_liberado > 0) NOT VALID"
            )
        )
        conexion.execute(
            text("ALTER TABLE liberacion VALIDATE CONSTRAINT liberacion_monto_liberado_check")
        )


def _asegurar_foreign_keys(conexion):
    for tabla, nombre, definicion in FOREIGN_KEYS:
        if _definicion_constraint(conexion, tabla, nombre):
            continue
        conexion.execute(
            text(f"ALTER TABLE {tabla} ADD CONSTRAINT {nombre} {definicion} NOT VALID")
        )
        conexion.execute(text(f"ALTER TABLE {tabla} VALIDATE CONSTRAINT {nombre}"))


def main():
    app = create_app(init_db=False)
    with app.app_context():
        if db.engine.dialect.name != "postgresql":
            raise SystemExit(
                "migrate_mr.py requiere PostgreSQL/Supabase. SQLite solo se usa en pruebas."
            )

        # Esquema base + tablas IoT y plantillas iniciales.
        db.create_all()
        from app.contratos.plantillas import ensure_plantillas
        ensure_plantillas()

        conexion = db.session.connection()
        _migrar_columnas(conexion)
        _migrar_perfiles(conexion)
        _alinear_pago(conexion)
        _asegurar_foreign_keys(conexion)

        errores = _validar_datos(conexion)
        if errores:
            db.session.rollback()
            print("ERROR: los datos existentes impiden aplicar los índices:")
            for error in errores:
                print(f"  - {error}")
            raise SystemExit(1)

        for sentencia in INDICES_UNICOS + INDICES_ADICIONALES:
            try:
                conexion.execute(text(sentencia))
            except Exception as error:
                db.session.rollback()
                print(f"ERROR al crear índice: {error}\nSQL: {sentencia}")
                raise SystemExit(1)

        db.session.commit()
        print("Migración consolidada completada.")


if __name__ == "__main__":
    main()
