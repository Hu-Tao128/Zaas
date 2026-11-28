# Ejecutar Zaas con Docker

Guía para levantar el proyecto completo (backend Flask + frontend React) con
Docker Compose. La base de datos es **Supabase/PostgreSQL**; no se usa SQLite en
producción ni en desarrollo.

## Requisitos

- Docker Engine 24 o superior.
- Docker Compose v2 (`docker compose`, con espacio).
- Un proyecto de Supabase y su cadena de conexión **Session Pooler**.

No hace falta Python ni Node en el host.

## Preparación (una sola vez)

1. **Variables del backend**

   ```bash
   cp .env.example .env
   ```

   Edita `.env` y define como mínimo:

   ```env
   DATABASE_URL=postgresql://postgres.<ref>:<clave>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
   SECRET_KEY=<clave larga y aleatoria>
   CORS_ORIGINS=https://tu-dominio.com
   CSRF_TRUSTED_ORIGINS=https://tu-dominio.com
   ```

   Usa el **Session Pooler** (puerto 5432). El Transaction Pooler (6543) también
   se soporta, pero requiere `NullPool` y no es recomendable para migraciones.

2. **Esquema en Supabase**

   Antes de arrancar los contenedores, aplica el esquema:

   ```bash
   cd backend
   DATABASE_URL="postgresql://...:5432/postgres?sslmode=require" python migrate_mr.py
   ```

   El contenedor también ejecuta `migrate_mr.py` en cada arranque (idempotente),
   pero hacerlo antes permite detectar errores de conexión/permisos.

3. **Configuración de Firebase del frontend**

   ```bash
   cp frontend/.env.example frontend/.env
   ```

   Rellena `VITE_FIREBASE_*`. Vite los usa **en tiempo de compilación**, así que
   si los cambias hay que reconstruir la imagen del frontend. También puedes
   pasarlos como build args (`VITE_FIREBASE_*`) sin crear el archivo.

4. **Llave de Firebase Admin**

   - **Coolify (recomendado):** File Mount en el servicio `backend` con destino
     `/app/keys/key.json` y el JSON de la service account como contenido.
   - **Variable de entorno:** define `FIREBASE_CREDENTIALS_JSON` con el JSON
     completo.
   - **Local con carpeta:** copia `docker-compose.override.yml.example` a
     `docker-compose.override.yml` para montar `backend/keys`.

   Sin credenciales el backend arranca, pero no puede verificar los inicios de
   sesión de Firebase.

## Levantar la aplicación

```bash
docker compose up --build
```

- Aplicación: <http://localhost:8080>
- API directa (opcional): <http://localhost:5000>

En segundo plano:

```bash
docker compose up -d --build
```

## Migrar datos desde SQLite

Si tienes un `zaas.db` con datos reales:

```bash
cd backend
# 1. Ver qué se migraría, sin escribir nada
DATABASE_URL="postgresql://...:5432/postgres?sslmode=require" \
  python scripts/migrate_sqlite_to_supabase.py \
  --source sqlite:///instance/zaas.db --dry-run

# 2. Migrar conservando los usuarios existentes de Supabase
DATABASE_URL="postgresql://...:5432/postgres?sslmode=require" \
  python scripts/migrate_sqlite_to_supabase.py \
  --source sqlite:///instance/zaas.db --mode merge
```

Para reemplazar por completo el contenido de Supabase con el del SQLite:

```bash
... --mode replace --yes
```

El script empareja usuarios por `firebase_uid`/`email`, remapea las FKs,
conserva las plantillas existentes y resetea las secuencias/identities.

## Desplegar en Coolify

### Variables de entorno del backend

| Variable | Ejemplo | Notas |
|---|---|---|
| `DATABASE_URL` | `postgresql://postgres.<ref>:<clave>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require` | Obligatoria. Session Pooler. |
| `SECRET_KEY` | valor aleatorio largo | No dejes el valor de desarrollo. |
| `CORS_ORIGINS` | `https://zaas.example.com` | Dominio público del frontend. |
| `CSRF_TRUSTED_ORIGINS` | `https://zaas.example.com` | Igual que CORS. |
| `AUTO_CREATE_SCHEMA` | `false` | El esquema lo aplica `migrate_mr.py`. |
| `FIREBASE_KEY_PATH` | `/app/keys/key.json` | Ruta del File Mount de Firebase. |
| `FIREBASE_CREDENTIALS_JSON` | `{"type":"service_account",...}` | Alternativa al File Mount. |
| `SESSION_COOKIE_DOMAIN` | `example.com` | Solo con subdominios distintos. |
| `SESSION_COOKIE_SECURE` | `true` | Con HTTPS. |
| `DB_POOL_SIZE` | `5` | Ajusta según el límite del pooler. |
| `DB_MAX_OVERFLOW` | `10` | Conexiones extra permitidas. |

### Variables de build del frontend

Vite incrusta la configuración de Firebase en el bundle, por lo que estas
variables deben definirse como **Build Variables** (no solo en runtime):

- `VITE_FIREBASE_API_KEY`
- `VITE_FIREBASE_AUTH_DOMAIN`
- `VITE_FIREBASE_PROJECT_ID`
- `VITE_FIREBASE_STORAGE_BUCKET`
- `VITE_FIREBASE_MESSAGING_SENDER_ID`
- `VITE_FIREBASE_APP_ID`
- `VITE_FIREBASE_MEASUREMENT_ID`

Si despliegas frontend y backend por separado, define en el frontend
`BACKEND_URL` con la URL interna/pública del backend; nginx la usa como destino
del proxy para `/api`, `/auth`, `/contratos/api` y `/pagos/api`.

### Firebase Admin por File Mount

En el recurso Compose, añade un **File Mount** al servicio `backend`:

- **Destination Path:** `/app/keys/key.json`
- **Content:** el JSON completo de la service account.
- **Variable:** `FIREBASE_KEY_PATH=/app/keys/key.json` (valor por defecto).

El bind mount `./backend/keys:/app/keys:ro` está comentado en
`docker-compose.yml` para no chocar con el File Mount.

## Comandos útiles

```bash
docker compose ps                 # estado de los servicios
docker compose logs -f backend    # logs del backend
docker compose logs -f frontend   # logs de nginx
docker compose down               # detener
docker compose up -d --build      # reconstruir tras cambiar código o .env
```

## Notas y solución de problemas

- **`DATABASE_URL` obligatoria:** el compose falla si no está definida. No hay
  fallback a SQLite.
- **Error de conexión a Supabase:** verifica el host/puerto del Session Pooler,
  la contraseña y `?sslmode=require`. Si la red del host no soporta IPv6, no uses
  la conexión directa; usa el pooler.
- **`migrate_mr.py` falla por DDL:** algunos poolers limitan DDL. Ejecútalo con
  la conexión directa o aplica la migración desde el SQL Editor de Supabase.
- **CORS bloqueado:** define `CORS_ORIGINS` y `CSRF_TRUSTED_ORIGINS` con el
  dominio exacto (incluye `https://`).
- **Firebase no inicializa:** revisa el File Mount en `/app/keys/key.json` y
  `FIREBASE_KEY_PATH`, o usa `FIREBASE_CREDENTIALS_JSON`.
- **Cambié `frontend/.env` y no se refleja:** reconstruye con
  `docker compose up -d --build frontend`.
- **Error al generar PDF:** la imagen del backend ya instala Pango, Cairo y
  fuentes DejaVu.
