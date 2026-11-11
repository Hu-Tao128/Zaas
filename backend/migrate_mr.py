"""Migra una base SQLite local existente al Modelo Relacional corregido.

Uso:
    python migrate_mr.py

El script es idempotente:
- crea las tablas nuevas (habilidad, perfil_habilidad, perfil_tecnologia),
- agrega las columnas nuevas del MR a las tablas existentes,
- migra las antiguas cadenas `perfil.habilidades` y `perfil.stack_tecnologico`
  a las tablas intermedias,
- crea los índices únicos que el MR exige.

Para una base nueva no es necesario: basta con `python seed.py`.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text

from app import create_app
from app.auth.models import Perfil
from app.auth.perfil_utils import sincronizar_habilidades, sincronizar_tecnologias
from app.extensions import db


COLUMNAS_NUEVAS = {
    'contrato': [
        ('id_plantilla', 'INTEGER'),
    ],
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
    'incidencia': [
        ('id_contrato', 'INTEGER'),
    ],
}

INDICES_UNICOS = [
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_perfil_id_usuario ON perfil (id_usuario)',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_postulacion_oferta_dev ON postulacion (id_oferta, id_desarrollador)',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_perfil_habilidad ON perfil_habilidad (id_perfil, id_habilidad)',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_perfil_tecnologia ON perfil_tecnologia (id_perfil, id_tecnologia)',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_categoria_proyecto ON categoria_proyecto (id_proyecto, id_categoria)',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_tecnologia_proyecto ON tecnologia_proyecto (id_proyecto, id_tecnologia)',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_recibo_id_pago ON recibo (id_pago)',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_pago_transaccion ON pago (transaccion_id) WHERE transaccion_id IS NOT NULL',
    'CREATE UNIQUE INDEX IF NOT EXISTS uq_disputa_incidencia ON disputa (id_incidencia) WHERE id_incidencia IS NOT NULL',
]


def _columnas(conexion, tabla):
    filas = conexion.execute(text(f'PRAGMA table_info({tabla})')).mappings().all()
    return {fila['name'] for fila in filas}


def main():
    app = create_app()
    with app.app_context():
        # Crea las tablas nuevas que aún no existen.
        db.create_all()

        conexion = db.session.connection()
        for tabla, columnas in COLUMNAS_NUEVAS.items():
            existentes = _columnas(conexion, tabla)
            for nombre, tipo in columnas:
                if nombre in existentes:
                    continue
                conexion.execute(text(f'ALTER TABLE {tabla} ADD COLUMN {nombre} {tipo}'))
                print(f'  + {tabla}.{nombre}')

        # Migrar habilidades/tecnologías antiguas antes de que el ORM las ignore.
        filas = conexion.execute(text(
            'SELECT id, habilidades, stack_tecnologico FROM perfil'
        )).mappings().all()

        for fila in filas:
            perfil = db.session.get(Perfil, fila['id'])
            if perfil is None:
                continue
            if fila['habilidades']:
                sincronizar_habilidades(perfil, fila['habilidades'])
            if fila['stack_tecnologico']:
                sincronizar_tecnologias(perfil, fila['stack_tecnologico'])

        for sentencia in INDICES_UNICOS:
            try:
                conexion.execute(text(sentencia))
            except Exception as error:
                print(f'  ! No se pudo crear índice ({error}). Revisa datos duplicados.')

        db.session.commit()
        print('Migración MR completada.')


if __name__ == '__main__':
    main()
