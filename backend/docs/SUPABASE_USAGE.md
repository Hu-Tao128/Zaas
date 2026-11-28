# Supabase en ZaaS

## Arquitectura

Supabase/PostgreSQL es la **base de datos principal y única** del backend. El
acceso se hace con **SQLAlchemy + psycopg2** a través de `DATABASE_URL`; ya no
se usa el cliente `supabase-py`, PostgREST, Supabase Auth ni la `service_role`
key.

```
React → Flask (SQLAlchemy/psycopg2) → Supabase Postgres (Session Pooler)
             │
             └── Firebase Admin (solo verificación de ID tokens)
```

## Configuración

```env
DATABASE_URL=postgresql://postgres.<ref>:<clave>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
SECRET_KEY=<clave larga y aleatoria>
```

Usa el **Session Pooler** (puerto 5432). `config.py` normaliza `postgres://` y
`postgresql://` al driver `psycopg2`, elimina parámetros de Prisma
(`pgbouncer`, `connection_limit`, `schema`) y añade `sslmode=require` en hosts
de Supabase si falta.

Para el Transaction Pooler (puerto 6543) el backend usa `NullPool`
automáticamente, pero no es recomendable para ejecutar DDL.

## Esquema y migraciones

El esquema se crea/actualiza con:

```bash
cd backend
DATABASE_URL="postgresql://...:5432/postgres?sslmode=require" python migrate_mr.py
```

`migrate_mr.py` es idempotente: crea tablas faltantes (incluidas las de IoT),
añade columnas, alinea checks/FKs conocidas y crea índices únicos. El entrypoint
de Docker lo ejecuta antes de arrancar Gunicorn.

En producción `AUTO_CREATE_SCHEMA=false` evita que cada worker ejecute DDL al
importar la aplicación.

## Acceso a datos

```python
from app.extensions import db

usuarios = db.session.execute(db.select(Usuario)).scalars().all()
```

Todas las consultas, relaciones y transacciones usan SQLAlchemy. No hay una
segunda fuente de verdad.

## RLS

Las tablas del MR tienen RLS habilitado sin políticas para `anon`/`authenticated`.
El backend se conecta con el rol `postgres` del Session Pooler, que omite RLS.
El frontend no se conecta directo a Supabase; solo consume la API Flask.

Si usas un rol restringido en lugar de `postgres`, deberás otorgarle privilegios
sobre las tablas o deshabilitar RLS.

## Migración de datos desde SQLite

```bash
cd backend
DATABASE_URL="postgresql://..." \
  python scripts/migrate_sqlite_to_supabase.py \
  --source sqlite:///instance/zaas.db --mode merge
```

El script empareja usuarios por `firebase_uid`/`email`, remapea FKs, conserva
las plantillas y resetea las secuencias. Usa `--dry-run` para revisar antes.

## Notas

- SQLite solo se usa como motor de las pruebas automatizadas.
- No configure `SUPABASE_URL`/`SUPABASE_KEY`: ya no son necesarias.
- Para migraciones DDL que el pooler rechace, usa la conexión directa o el SQL
  Editor de Supabase.
