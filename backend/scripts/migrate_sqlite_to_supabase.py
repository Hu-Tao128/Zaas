#!/usr/bin/env python3
"""Migra datos de una base SQLite a Supabase/PostgreSQL.

Uso típico:

    cd backend
    DATABASE_URL="postgresql://...:5432/postgres?sslmode=require" \
      python scripts/migrate_sqlite_to_supabase.py \
      --source sqlite:///instance/zaas.db --dry-run

    DATABASE_URL="..." \
      python scripts/migrate_sqlite_to_supabase.py \
      --source sqlite:///instance/zaas.db --mode merge

El esquema destino debe existir antes de ejecutar el script:

    DATABASE_URL="..." python migrate_mr.py

Modos:
- ``merge`` (por defecto): conserva los usuarios existentes de Supabase,
  empareja por ``firebase_uid``/``email`` y remapea las FKs de usuario/perfil.
- ``replace``: trunca el destino e importa el SQLite con sus IDs originales.

El script es idempotente para ``plantilla_contrato`` (no duplica plantillas) y
aborta si el destino tiene datos en tablas que deberían estar vacías.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import JSON, Boolean, MetaData, create_engine, inspect, select, text

# Registra todos los modelos en db.metadata.
import app.auth.models  # noqa: F401
import app.catalogo.models  # noqa: F401
import app.comunicacion.models  # noqa: F401
import app.contratos.models  # noqa: F401
import app.models.iot  # noqa: F401
import app.pagos.models  # noqa: F401
from app.db_url import normalizar_database_url
from app.extensions import db

TABLAS_REFERENCIA = {"plantilla_contrato"}
TABLAS_USUARIO = {"usuario", "perfil"}


def _engine(url):
    if url.startswith("sqlite:///"):
        # Permite rutas relativas a backend/.
        return create_engine(url, future=True)
    return create_engine(normalizar_database_url(url), future=True, pool_pre_ping=True)


def _tablas_origen(source_engine):
    meta = MetaData()
    meta.reflect(bind=source_engine)
    return meta


def _contar(engine, tabla):
    with engine.connect() as conexion:
        return conexion.execute(text(f'SELECT COUNT(*) FROM "{tabla}"')).scalar_one()


def _columnas(engine, tabla):
    return {c["name"] for c in inspect(engine).get_columns(tabla)}


def _preflight(source_engine, target_engine, mode):
    print("== Preflight ==")
    inspeccion = inspect(target_engine)
    tablas_destino = set(inspeccion.get_table_names())
    faltantes = [t.name for t in db.metadata.sorted_tables if t.name not in tablas_destino]
    if faltantes:
        raise SystemExit(
            "Faltan tablas en Supabase: " + ", ".join(faltantes) +
            "\nEjecuta primero: DATABASE_URL=... python migrate_mr.py"
        )

    for tabla in db.metadata.sorted_tables:
        destino_columnas = _columnas(target_engine, tabla.name)
        faltan_columnas = {c.name for c in tabla.columns} - destino_columnas
        if faltan_columnas:
            raise SystemExit(
                f"La tabla {tabla.name} no tiene las columnas: "
                + ", ".join(sorted(faltan_columnas))
                + "\nEjecuta primero migrate_mr.py"
            )

    for tabla in db.metadata.sorted_tables:
        try:
            origen = _contar(source_engine, tabla.name)
        except Exception:
            origen = 0
        destino = _contar(target_engine, tabla.name)
        print(f"  {tabla.name:24} origen={origen:6} destino={destino:6}")
        if mode == "merge" and tabla.name not in TABLAS_USUARIO | TABLAS_REFERENCIA:
            if destino:
                raise SystemExit(
                    f"La tabla destino {tabla.name} tiene {destino} filas. "
                    "Usa --mode replace o vacíala antes de migrar."
                )
    print()


def _normalizar_valor(columna, valor):
    if valor is None:
        return None
    if isinstance(columna.type, JSON) and isinstance(valor, str):
        try:
            return json.loads(valor)
        except json.JSONDecodeError:
            return valor
    if isinstance(columna.type, Boolean) and isinstance(valor, int):
        return bool(valor)
    if isinstance(valor, str) and columna.type.__class__.__name__ in {"DateTime", "UTCDateTime"}:
        try:
            return datetime.fromisoformat(valor)
        except ValueError:
            return valor
    return valor


def _valores(row, origen_tabla, destino_tabla, remapeos):
    valores = {}
    for columna in destino_tabla.columns:
        if columna.name not in origen_tabla.columns:
            continue
        valor = row._mapping.get(columna.name)
        if columna.name in remapeos and valor is not None:
            valor = remapeos[columna.name].get(valor, valor)
        valores[columna.name] = _normalizar_valor(columna, valor)
    return valores


def _remapeos_usuario(destino_tabla):
    """Columnas de la tabla que apuntan a usuario.id."""
    return {
        fk.parent.name
        for fk in destino_tabla.foreign_keys
        if fk.column.table.name == "usuario"
    }


def _remapeos_perfil(destino_tabla):
    return {
        fk.parent.name
        for fk in destino_tabla.foreign_keys
        if fk.column.table.name == "perfil"
    }


def _merge_usuarios(source_conn, conexion, origen_meta):
    usuario_destino = db.metadata.tables["usuario"]
    perfil_destino = db.metadata.tables["perfil"]
    usuario_origen = origen_meta.tables.get("usuario")
    perfil_origen = origen_meta.tables.get("perfil")
    mapa_usuarios = {}
    mapa_perfiles = {}

    if usuario_origen is None:
        return mapa_usuarios, mapa_perfiles

    filas = source_conn.execute(select(usuario_origen)).all()
    print(f"Usuarios en origen: {len(filas)}")
    for row in filas:
        datos = row._mapping
        uid = datos.get("firebase_uid")
        email = datos.get("email")
        filtro = None
        if uid:
            filtro = usuario_destino.c.firebase_uid == uid
        elif email:
            filtro = usuario_destino.c.email == email

        destino = None
        if filtro is not None:
            destino = conexion.execute(
                select(usuario_destino.c.id, usuario_destino.c.firebase_uid)
                .where(filtro).limit(1)
            ).first()
        if destino is None and email:
            destino = conexion.execute(
                select(usuario_destino.c.id, usuario_destino.c.firebase_uid)
                .where(usuario_destino.c.email == email).limit(1)
            ).first()

        valores = _valores(row, usuario_origen, usuario_destino, {})
        valores.pop("id", None)

        if destino is not None:
            destino_id, destino_uid = destino
            if destino_uid and uid and destino_uid != uid:
                # El email ya pertenece a otra cuenta de Firebase: no la robamos.
                valores.pop("firebase_uid", None)
            conexion.execute(
                usuario_destino.update()
                .where(usuario_destino.c.id == destino_id)
                .values(**valores)
            )
            mapa_usuarios[datos["id"]] = destino_id
        else:
            resultado = conexion.execute(
                usuario_destino.insert().values(**valores).returning(usuario_destino.c.id)
            )
            mapa_usuarios[datos["id"]] = resultado.scalar_one()

    if perfil_origen is None:
        return mapa_usuarios, mapa_perfiles

    filas_perfil = source_conn.execute(select(perfil_origen)).all()
    print(f"Perfiles en origen: {len(filas_perfil)}")
    for row in filas_perfil:
        datos = row._mapping
        id_usuario = mapa_usuarios.get(datos.get("id_usuario"))
        if id_usuario is None:
            print(f"  ! perfil {datos.get('id')} sin usuario mapeado; se omite")
            continue
        existente = conexion.execute(
            select(perfil_destino.c.id)
            .where(perfil_destino.c.id_usuario == id_usuario).limit(1)
        ).scalar()
        valores = _valores(row, perfil_origen, perfil_destino, {"id_usuario": mapa_usuarios})
        valores.pop("id", None)
        valores["id_usuario"] = id_usuario
        if existente is not None:
            conexion.execute(
                perfil_destino.update()
                .where(perfil_destino.c.id == existente)
                .values(**valores)
            )
            mapa_perfiles[datos["id"]] = existente
        else:
            resultado = conexion.execute(
                perfil_destino.insert().values(**valores).returning(perfil_destino.c.id)
            )
            mapa_perfiles[datos["id"]] = resultado.scalar_one()

    return mapa_usuarios, mapa_perfiles


def _truncar(conexion):
    tablas = ", ".join(f'public."{t.name}"' for t in reversed(db.metadata.sorted_tables))
    conexion.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))


def _insertar_tabla(source_conn, conexion, tabla, origen_tabla, modo, mapa_usuarios, mapa_perfiles, batch_size):
    filas = source_conn.execute(select(origen_tabla)).all()
    if not filas:
        return 0

    if tabla.name == "plantilla_contrato" and modo == "merge":
        # No duplicar plantillas ya existentes.
        filas = [
            f for f in filas if not conexion.execute(
                select(tabla.c.id).where(tabla.c.id == f._mapping.get("id")).limit(1)
            ).first()
        ]
        if not filas:
            print(f"  {tabla.name:24} ya existe en destino; se omite")
            return 0

    remapeos = {}
    for columna in _remapeos_usuario(tabla):
        remapeos[columna] = mapa_usuarios
    for columna in _remapeos_perfil(tabla):
        remapeos[columna] = mapa_perfiles

    insertados = 0
    for row in filas:
        valores = _valores(row, origen_tabla, tabla, remapeos)
        if modo == "merge" and tabla.name in TABLAS_USUARIO:
            valores.pop("id", None)
        conexion.execute(tabla.insert().values(**valores))
        insertados += 1
    return insertados


def _resetear_secuencias(conexion):
    for tabla in db.metadata.sorted_tables:
        columnas_pk = list(tabla.primary_key.columns)
        if len(columnas_pk) != 1:
            continue
        pk = columnas_pk[0]
        secuencia = conexion.execute(
            text("SELECT pg_get_serial_sequence(:tabla, :columna)"),
            {"tabla": f"public.{tabla.name}", "columna": pk.name},
        ).scalar()
        if not secuencia:
            continue
        maximo = conexion.execute(
            text(f'SELECT COALESCE(MAX("{pk.name}"), 0) FROM public."{tabla.name}"')
        ).scalar_one()
        conexion.execute(
            text("SELECT setval(:secuencia, :valor, false)"),
            {"secuencia": secuencia, "valor": maximo + 1},
        )


def _validar(conexion, source_engine):
    print("\n== Validación ==")
    errores = []
    for tabla in db.metadata.sorted_tables:
        try:
            origen = _contar(source_engine, tabla.name)
        except Exception:
            origen = 0
        destino = conexion.execute(
            text(f'SELECT COUNT(*) FROM public."{tabla.name}"')
        ).scalar_one()
        print(f"  {tabla.name:24} origen={origen:6} destino={destino:6}")
        if tabla.name not in TABLAS_USUARIO and tabla.name not in TABLAS_REFERENCIA and origen != destino:
            errores.append(f"{tabla.name}: origen={origen} destino={destino}")

    for tabla in db.metadata.sorted_tables:
        for fk in tabla.foreign_keys:
            padre = fk.column.table.name
            col = fk.parent.name
            sql = text(
                f'SELECT COUNT(*) FROM public."{tabla.name}" c '
                f'LEFT JOIN public."{padre}" p ON p."{fk.column.name}" = c."{col}" '
                f'WHERE c."{col}" IS NOT NULL AND p."{fk.column.name}" IS NULL'
            )
            huerfanos = conexion.execute(sql).scalar_one()
            if huerfanos:
                errores.append(f"{tabla.name}.{col}: {huerfanos} FKs huérfanas")

    if errores:
        raise SystemExit("Errores de validación:\n  - " + "\n  - ".join(errores))
    print("Validación OK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="sqlite:///instance/zaas.db")
    parser.add_argument("--target", default=os.environ.get("DATABASE_URL"))
    parser.add_argument("--mode", choices=["merge", "replace"], default="merge")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    if not args.target:
        raise SystemExit("Define --target o la variable DATABASE_URL.")
    if args.mode == "replace" and not args.yes and not args.dry_run:
        raise SystemExit("El modo replace borra el destino. Repite con --yes.")

    source_engine = _engine(args.source)
    target_engine = _engine(args.target)
    origen_meta = _tablas_origen(source_engine)
    _preflight(source_engine, target_engine, args.mode)

    if args.dry_run:
        print("Dry-run: no se escribió nada.")
        return

    with source_engine.connect() as source_conn, target_engine.begin() as conexion:
        if args.mode == "replace":
            _truncar(conexion)

        mapa_usuarios, mapa_perfiles = _merge_usuarios(
            source_conn, conexion, origen_meta
        )

        omitidas = TABLAS_USUARIO | {"plantilla_contrato"}
        for tabla in db.metadata.sorted_tables:
            if tabla.name in omitidas:
                continue
            origen_tabla = origen_meta.tables.get(tabla.name)
            if origen_tabla is None:
                continue
            n = _insertar_tabla(
                source_conn, conexion, tabla, origen_tabla, args.mode,
                mapa_usuarios, mapa_perfiles, args.batch_size,
            )
            print(f"  {tabla.name:24} {n} filas")

        # Plantillas al final, sin duplicar.
        plantilla_origen = origen_meta.tables.get("plantilla_contrato")
        if plantilla_origen is not None:
            n = _insertar_tabla(
                source_conn, conexion, db.metadata.tables["plantilla_contrato"],
                plantilla_origen, args.mode, mapa_usuarios, mapa_perfiles,
                args.batch_size,
            )
            print(f"  {'plantilla_contrato':24} {n} filas")

        _resetear_secuencias(conexion)
        _validar(conexion, source_engine)

    print("\nMigración completada.")


if __name__ == "__main__":
    main()
