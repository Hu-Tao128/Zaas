# Migración de SQLite a Supabase Postgres

Runbook para pasar de la base SQLite a Supabase como base principal.

## 1. Preparación

- Define `DATABASE_URL` con el **Session Pooler** de Supabase:

  ```env
  DATABASE_URL=postgresql://postgres.<ref>:<clave>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
  ```

- Haz backup del SQLite (`cp zaas.db zaas.db.bak-YYYYMMDD`).
- Haz backup de Supabase (`pg_dump "$DATABASE_URL" -Fc -f antes.dump`).
- Avisa la ventana de mantenimiento y detén el backend en Coolify.

## 2. Esquema

```bash
cd backend
DATABASE_URL="postgresql://..." python migrate_mr.py
```

Esto añade columnas, crea tablas IoT, alinea checks/FKs e índices. Es
idempotente.

## 3. Datos

```bash
# Revisión sin escribir
DATABASE_URL="postgresql://..." \
  python scripts/migrate_sqlite_to_supabase.py \
  --source sqlite:///instance/zaas.db --dry-run

# Migración conservando usuarios de Supabase
DATABASE_URL="postgresql://..." \
  python scripts/migrate_sqlite_to_supabase.py \
  --source sqlite:///instance/zaas.db --mode merge
```

- `merge` empareja usuarios por `firebase_uid`/`email`, remapea FKs y conserva
  los usuarios que solo existen en Supabase.
- `replace --yes` trunca el destino e importa los IDs originales del SQLite.

## 4. Verificación

```sql
SELECT 'usuario', count(*) FROM usuario
UNION ALL SELECT 'perfil', count(*) FROM perfil
UNION ALL SELECT 'contrato', count(*) FROM contrato
UNION ALL SELECT 'pago', count(*) FROM pago;
```

Comprueba también secuencias y FKs huérfanas. El script de migración ya hace
una validación básica.

## 5. Corte

1. Despliega el código nuevo con `DATABASE_URL` de Supabase.
2. Mantén `AUTO_CREATE_SCHEMA=false`.
3. Haz humo: login Firebase, catálogo, contrato, pago, mensajería e IoT.
4. Conserva el backup del SQLite y la imagen anterior para rollback.

## Rollback

- Restaura `DATABASE_URL` anterior y redeploy de la versión previa.
- Como hubo ventana de mantenimiento, no deberían existir escrituras nuevas que
  reconciliar.
