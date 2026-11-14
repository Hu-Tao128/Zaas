"""Migración aditiva para el módulo de Pagos.

Uso:
    python migrate_pagos.py

Crea las tablas del módulo (pago, liberacion, recibo, disputa, arbitraje)
si no existen y agrega las columnas faltantes a tablas ya creadas.
Idempotente y reversible a nivel de datos (no borra ni modifica filas).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from app import create_app
from app.extensions import db


COLUMNAS_NUEVAS = {
    'pago': [
        ('metodo_pago', 'VARCHAR(50)'),
        ('transaccion_id', 'VARCHAR(100)'),
    ],
    'liberacion': [
        ('id_entregable', 'INTEGER'),
    ],
    'recibo': [
        ('total', 'FLOAT'),
    ],
    'disputa': [
        ('id_pago', 'INTEGER'),
        ('id_entregable', 'INTEGER'),
        ('id_incidencia', 'INTEGER'),
    ],
    'incidencia': [],
}

INDICES_UNICOS = [
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_transaccion ON pago (transaccion_id) WHERE transaccion_id IS NOT NULL',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_recibo_id_pago ON recibo (id_pago)',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_incidencia ON disputa (id_incidencia) WHERE id_incidencia IS NOT NULL',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_arbitraje_disputa ON arbitraje (id_disputa)',
]


def _columnas(conexion, tabla):
    try:
        filas = conexion.execute(text(f'PRAGMA table_info({tabla})')).mappings().all()
    except Exception:
        return set()
    return {fila['name'] for fila in filas}


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        conexion = db.session.connection()
        for tabla, columnas in COLUMNAS_NUEVAS.items():
            existentes = _columnas(conexion, tabla)
            if not existentes:
                continue
            for nombre, tipo in columnas:
                if nombre in existentes:
                    continue
                conexion.execute(text(f'ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}'))
                print(f'  + {tabla}.{nombre}')

        # Validar que los datos existentes cumplan las restricciones del módulo.
        errores = []
        # pagos con monto inválido
        filas = conexion.execute(text(
            "SELECT id, monto FROM pago WHERE monto IS NULL OR monto <= 0"
        )).mappings().all()
        for f in filas:
            errores.append(f"pago.id={f['id']}: monto inválido ({f['monto']})")
        # liberaciones con monto inválido
        filas = conexion.execute(text(
            "SELECT id, monto_liberado FROM liberacion WHERE monto_liberado IS NULL OR monto_liberado <= 0"
        )).mappings().all()
        for f in filas:
            errores.append(f"liberacion.id={f['id']}: monto_liberado inválido ({f['monto_liberado']})")
        # disputas con campos obligatorios vacíos
        filas = conexion.execute(text(
            "SELECT id FROM disputa WHERE tipo IS NULL OR TRIM(tipo)='' OR descripcion IS NULL OR TRIM(descripcion)=''"
        )).mappings().all()
        for f in filas:
            errores.append(f"disputa.id={f['id']}: tipo o descripción vacíos")
        # arbitrajes con decisión inválida
        filas = conexion.execute(text(
            "SELECT id FROM arbitraje WHERE decision IS NULL OR TRIM(decision)='' "
            "OR decision NOT IN ('liberar','reembolsar','dividir')"
        )).mappings().all()
        for f in filas:
            errores.append(f"arbitraje.id={f['id']}: decisión inválida")
        # porcentaje fuera de rango
        filas = conexion.execute(text(
            "SELECT id FROM arbitraje WHERE porcentaje_desarrollador IS NOT NULL "
            "AND (porcentaje_desarrollador < 0 OR porcentaje_desarrollador > 100)"
        )).mappings().all()
        for f in filas:
            errores.append(f"arbitraje.id={f['id']}: porcentaje fuera de rango")

        if errores:
            db.session.rollback()
            print('ERROR: datos existentes incumplen las restricciones del módulo de Pagos:')
            for e in errores:
                print('  - ' + e)
            raise SystemExit(1)

        for sentencia in INDICES_UNICOS:
            try:
                conexion.execute(text(sentencia))
            except Exception as error:
                print(f'  ! No se pudo crear índice ({error}). Revisa datos duplicados.')
                raise SystemExit(1)

        db.session.commit()
        print('Migración de Pagos completada.')


def downgrade():
    """Reversión: elimina las tablas creadas por el módulo de Pagos."""
    app = create_app()
    with app.app_context():
        from app.extensions import db
        from sqlalchemy import text

        conexion = db.session.connection()
        for tabla in ('arbitraje', 'disputa', 'recibo', 'liberacion', 'pago'):
            try:
                conexion.execute(text(f'DROP TABLE IF EXISTS {tabla}'))
                print(f'  - {tabla} eliminada')
            except Exception as error:
                print(f'  ! No se pudo eliminar {tabla}: {error}')
        db.session.commit()
        print('Downgrade de Pagos completado.')


if __name__ == '__main__':
    main()
