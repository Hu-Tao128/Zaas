# Ejecutar Zaas con Docker

Guía para levantar el proyecto completo (backend Flask + frontend React) con
Docker Compose en cualquier máquina.

## Requisitos

- Docker Engine 24 o superior.
- Docker Compose v2 (`docker compose`, con espacio).

No hace falta Python, Node ni instalar dependencias en el host.

## Preparación (una sola vez)

1. **Variables del backend y puertos**

   ```bash
   cp .env.example .env
   ```

   Edita `.env` y como mínimo cambia `SECRET_KEY`. Opcionalmente configura
   `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_KEY`, los dominios permitidos
   (`CORS_ORIGINS`, `CSRF_TRUSTED_ORIGINS`) y los puertos.

2. **Configuración de Firebase del frontend**

   ```bash
   cp frontend/.env.example frontend/.env
   ```

   Rellena los valores `VITE_FIREBASE_*` con la configuración web de tu
   proyecto de Firebase. Vite los usa **en tiempo de compilación**, así que si
   los cambias hay que reconstruir la imagen del frontend. También puedes
   pasarlos como build args (`VITE_FIREBASE_*`) sin crear el archivo.

3. **Llave de Firebase Admin**

   El backend puede obtener la service account de tres formas:

   - **Coolify (recomendado):** crea un **File Mount** en el servicio `backend`
     con destino `/app/keys/key.json` y pega el contenido del JSON. Deja
     `FIREBASE_KEY_PATH=/app/keys/key.json` (valor por defecto del compose).
   - **Variable de entorno:** define `FIREBASE_CREDENTIALS_JSON` con el JSON
     completo de la service account.
   - **Desarrollo local con carpeta:** copia
     `docker-compose.override.yml.example` a `docker-compose.override.yml`
     para montar `backend/keys` en `/app/keys` y coloca la llave en
     `backend/keys/key.json`.

   Sin credenciales el backend arranca, pero no puede verificar los inicios de
   sesión de Firebase.

## Levantar la aplicación

```bash
docker compose up --build
```

- Aplicación: <http://localhost:8080>
- API directa (opcional): <http://localhost:5000>

Para ejecutarlo en segundo plano:

```bash
docker compose up -d --build
```

## Datos de demostración

Una base nueva empieza sin usuarios ni proyectos. Al iniciar sesión con Firebase
se crea automáticamente el usuario local con el rol que se elija en el registro.
A partir de ahí puedes publicar proyectos y crear contratos desde la aplicación.

El `seed.py` del repositorio no se ejecuta en Docker porque en esta versión del
código depende de datos de ejemplo antiguos que ya no están definidos.

## Comandos útiles

```bash
docker compose ps                 # estado de los servicios
docker compose logs -f backend    # logs del backend
docker compose logs -f frontend   # logs de nginx
docker compose down               # detener
docker compose down -v            # detener y borrar la base de datos
docker compose up -d --build      # reconstruir tras cambiar código o .env
```

## Persistencia de la base de datos

Por defecto SQLite vive en el volumen nombrado `zaas_db`, así que sobrevive a
`docker compose down`. Solo se borra con `docker compose down -v`.

Para usar el archivo local `backend/instance/zaas.db` en lugar del volumen,
edita `docker-compose.yml` y sustituye:

```yaml
    volumes:
      - zaas_db:/app/instance
```

por:

```yaml
    volumes:
      - ./backend/instance:/app/instance
```

## Desplegar en Coolify

El proyecto se puede desplegar como un recurso de Docker Compose o como dos
aplicaciones separadas (backend y frontend).

### Variables de entorno del backend

Define como mínimo:

| Variable | Ejemplo | Notas |
|---|---|---|
| `DATABASE_URL` | `postgresql://usuario:clave@db:5432/zaas` | Acepta `postgres://`, `postgresql://` y `postgresql+psycopg2://`. |
| `SECRET_KEY` | valor aleatorio largo | No dejes el valor de desarrollo. |
| `CORS_ORIGINS` | `https://zaas.example.com` | Dominio público del frontend. |
| `CSRF_TRUSTED_ORIGINS` | `https://zaas.example.com` | Igual que CORS. |
| `FIREBASE_KEY_PATH` | `/app/keys/key.json` | Ruta del File Mount de Firebase. |
| `FIREBASE_CREDENTIALS_JSON` | `{"type":"service_account",...}` | Alternativa al File Mount. |
| `SESSION_COOKIE_DOMAIN` | `example.com` | Solo si frontend y backend están en subdominios distintos. |
| `SESSION_COOKIE_SECURE` | `true` | Con HTTPS. |

Si usas el PostgreSQL administrado por Coolify, copia su URL interna en
`DATABASE_URL`. Para Supabase utiliza la cadena de conexión con
`?sslmode=require` (se eliminan automáticamente parámetros de Prisma como
`pgbouncer` o `connection_limit`).

### Firebase Admin por File Mount en Coolify

En el recurso Compose, añade un **File Mount** al servicio `backend`:

- **Destination Path:** `/app/keys/key.json`
- **Content:** el JSON completo de la service account.
- **Variable:** `FIREBASE_KEY_PATH=/app/keys/key.json` (ya es el valor por
  defecto del compose).

El bind mount `./backend/keys:/app/keys:ro` está comentado en
`docker-compose.yml` para no chocar con el File Mount. No necesitas volúmenes
persistentes para la llave.

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

### Volumen de datos

En un recurso Compose, el volumen `zaas_db` solo aplica si sigues usando
SQLite. Con PostgreSQL los datos viven en la base de datos gestionada.

## Usar PostgreSQL en lugar de SQLite

Añade un servicio de base de datos a `docker-compose.yml`:

```yaml
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: zaas
      POSTGRES_USER: zaas
      POSTGRES_PASSWORD: cambia-esta-clave
    volumes:
      - zaas_pg:/var/lib/postgresql/data
```

Agrega `zaas_pg` a `volumes` y en `backend` define:

```yaml
    environment:
      DATABASE_URL: postgresql+psycopg2://zaas:cambia-esta-clave@db:5432/zaas
    depends_on:
      db:
        condition: service_healthy
```

El backend ya incluye `psycopg2-binary` y `migrate_mr.py` funciona tanto con
SQLite como con PostgreSQL. También puedes usar una URL sin driver
(`postgresql://...` o `postgres://...`): `config.py` la normaliza a
`postgresql+psycopg2://` automáticamente.

## Notas y solución de problemas

- **Puerto ocupado:** cambia `FRONTEND_PORT` o `BACKEND_PORT` en `.env`.
- **No puedo iniciar sesión:** revisa que `frontend/.env` tenga la config de
  Firebase, que `backend/keys/key.json` exista y que las credenciales
  correspondan al mismo proyecto de Firebase.
- **Cambié `frontend/.env` y no se refleja:** reconstruye con
  `docker compose up -d --build frontend`.
- **Error al generar PDF:** la imagen del backend ya instala Pango, Cairo y
  fuentes DejaVu. Si usas otra imagen base, instala esas bibliotecas.
- **La base no se actualiza:** el backend ejecuta `migrate_mr.py` en cada
  arranque; revisa `docker compose logs backend`.
- **Error de conexión a PostgreSQL:** verifica `DATABASE_URL`, que el servicio
  `db` esté saludable y, en Supabase, que la URL incluya `?sslmode=require`.
  Los parámetros `pgbouncer`, `connection_limit` y `schema` se eliminan solos.
- **CORS bloqueado en el navegador:** define `CORS_ORIGINS` y
  `CSRF_TRUSTED_ORIGINS` con el dominio público exacto (incluye `https://`).
- **Firebase no inicializa en Coolify:** revisa el File Mount en
  `/app/keys/key.json` y que `FIREBASE_KEY_PATH` apunte a esa ruta, o define
  `FIREBASE_CREDENTIALS_JSON` con el JSON completo de la service account.
