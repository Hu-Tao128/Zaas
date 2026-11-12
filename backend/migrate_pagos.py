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

        for sentencia in INDICES_UNICOS:
            try:
                conexion.execute(text(sentencia))
            except Exception as error:
                print(f'  ! No se pudo crear índice ({error}). Revisa datos duplicados.')

        db.session.commit()
        print('Migración de Pagos completada.')


if __name__ == '__main__':
    main()
