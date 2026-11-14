"""Migración aditiva: pagos realistas (columnas nuevas + CHECK ampliado).

Uso:
    python migrate_pagos_realista.py
    python migrate_pagos_realista.py downgrade
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from app import create_app
from app.extensions import db

COLUMNAS_NUEVAS = [
    ('moneda', "VARCHAR(3) NOT NULL DEFAULT 'MXN'"),
    ('proveedor', 'VARCHAR(30)'),
    ('marca_tarjeta', 'VARCHAR(20)'),
    ('ultimos4', 'VARCHAR(4)'),
    ('codigo_fallo', 'VARCHAR(50)'),
    ('mensaje_fallo', 'VARCHAR(200)'),
    ('idempotency_key', 'VARCHAR(64)'),
    ('fecha_confirmacion', 'DATETIME'),
    ('reembolso_id', 'VARCHAR(100)'),
    ('fecha_reembolso', 'DATETIME'),
]


def _columnas(conexion, tabla):
    try:
        filas = conexion.execute(text(f'PRAGMA table_info({tabla})')).mappings().all()
    except Exception:
        return set()
    return {f['name'] for f in filas}

def _check_estado_escrow_actualizado(conexion):
    """True si la tabla pago ya tiene CHECK de estado_escrow con estados pendiente/fallido."""
    try:
        fila = conexion.execute(
            text("SELECT sql FROM sqlite_master WHERE type='table' AND name='pago'")
        ).mappings().first()
    except Exception:
        return False
    if not fila or not fila.get('sql'):
        return False
    sql = fila['sql'].lower()
    return "'pendiente'" in sql and "'fallido'" in sql and "estado_escrow" in sql



def main():
    app = create_app()
    with app.app_context():
        db.create_all()
        conexion = db.session.connection()
        existentes = _columnas(conexion, 'pago')
        for nombre, tipo in COLUMNAS_NUEVAS:
            if nombre in existentes:
                continue
            conexion.execute(text(f'ALTER TABLE pago ADD COLUMN {nombre} {tipo}'))
            print(f'  + pago.{nombre}')

        # Recrear la tabla para actualizar el CHECK de estado_escrow SOLO si no está actualizado.
        if not _check_estado_escrow_actualizado(conexion):
            conexion.execute(text('PRAGMA foreign_keys=OFF'))
            conexion.execute(text(\'\'\'
                CREATE TABLE IF NOT EXISTS pago_new (
                    id INTEGER PRIMARY KEY,
                    id_contrato INTEGER NOT NULL,
                    monto REAL NOT NULL CHECK (monto > 0),
                    estado_escrow TEXT NOT NULL CHECK (estado_escrow IN ('pendiente','fallido','retenido','liberado','reembolsado','dividido')),
                    fecha_pago DATETIME,
                    fecha_liberacion DATETIME,
                    metodo_pago VARCHAR(50),
                    transaccion_id VARCHAR(100) UNIQUE,
                    moneda VARCHAR(3) NOT NULL DEFAULT 'MXN',
                    proveedor VARCHAR(30),
                    marca_tarjeta VARCHAR(20),
                    ultimos4 VARCHAR(4),
                    codigo_fallo VARCHAR(50),
                    mensaje_fallo VARCHAR(200),
                    idempotency_key VARCHAR(64) UNIQUE,
                    fecha_confirmacion DATETIME,
                    reembolso_id VARCHAR(100),
                    fecha_reembolso DATETIME
                )
            \'\'\'))
            conexion.execute(text(\'\'\'
                INSERT INTO pago_new (id, id_contrato, monto, estado_escrow, fecha_pago, fecha_liberacion, metodo_pago, transaccion_id, moneda, proveedor, marca_tarjeta, ultimos4, codigo_fallo, mensaje_fallo, idempotency_key, fecha_confirmacion, reembolso_id, fecha_reembolso)
                SELECT id, id_contrato, monto, estado_escrow, fecha_pago, fecha_liberacion, metodo_pago, transaccion_id,
                       COALESCE(moneda, 'MXN'), proveedor, marca_tarjeta, ultimos4, codigo_fallo, mensaje_fallo, idempotency_key, fecha_confirmacion, reembolso_id, fecha_reembolso
                FROM pago
            \'\'\'))
            conexion.execute(text('DROP TABLE pago'))
            conexion.execute(text('ALTER TABLE pago_new RENAME TO pago'))
            print('  ~ tabla pago recreada para actualizar CHECK de estado_escrow')
        else:
            print('  = CHECK de estado_escrow ya actualizado; se omite recreación de tabla pago')

        # Índices idempotentes
        conexion.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_transaccion ON pago (transaccion_id) WHERE transaccion_id IS NOT NULL'))
        conexion.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_idempotency ON pago (idempotency_key) WHERE idempotency_key IS NOT NULL'))
        conexion.execute(text('PRAGMA foreign_keys=ON'))
        db.session.commit()
        print('Migración de pagos realista completada.')


def downgrade():
    app = create_app()
    with app.app_context():
        conexion = db.session.connection()
        # Fallar si hay filas incompatibles.
        filas = conexion.execute(text(
            "SELECT COUNT(*) AS n FROM pago WHERE estado_escrow IN ('pendiente','fallido')"
        )).mappings().first()
        if filas and filas['n'] > 0:
            print('ERROR: existen pagos pendientes o fallidos; no se puede revertir sin perder datos.')
            raise SystemExit(1)

        conexion.execute(text('PRAGMA foreign_keys=OFF'))
        conexion.execute(text('''
            CREATE TABLE IF NOT EXISTS pago_old (
                id INTEGER PRIMARY KEY,
                id_contrato INTEGER NOT NULL,
                monto REAL NOT NULL CHECK (monto > 0),
                estado_escrow TEXT NOT NULL CHECK (estado_escrow IN ('retenido','liberado','reembolsado','dividido')),
                fecha_pago DATETIME,
                fecha_liberacion DATETIME,
                metodo_pago VARCHAR(50),
                transaccion_id VARCHAR(100) UNIQUE
            )
        '''))
        conexion.execute(text('''
            INSERT INTO pago_old (id, id_contrato, monto, estado_escrow, fecha_pago, fecha_liberacion, metodo_pago, transaccion_id)
            SELECT id, id_contrato, monto, estado_escrow, fecha_pago, fecha_liberacion, metodo_pago, transaccion_id
            FROM pago
        '''))
        conexion.execute(text('DROP TABLE pago'))
        conexion.execute(text('ALTER TABLE pago_old RENAME TO pago'))
        conexion.execute(text('PRAGMA foreign_keys=ON'))
        db.session.commit()
        print('Downgrade de pagos realista completado.')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        main()