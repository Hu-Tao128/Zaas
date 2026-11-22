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
   `SUPABASE_URL`, `SUPABASE_KEY` y los puertos.

2. **Configuración de Firebase del frontend**

   ```bash
   cp frontend/.env.example frontend/.env
   ```

   Rellena los valores `VITE_FIREBASE_*` con la configuración web de tu
   proyecto de Firebase. Este archivo se usa **en tiempo de compilación**, así
   que si lo cambias hay que reconstruir la imagen del frontend.

3. **Llave de Firebase Admin**

   Coloca la llave de servicio en:

   ```
   backend/keys/key.json
   ```

   El contenedor la monta en modo de solo lectura. Sin ella, el backend arranca
   pero no puede verificar los inicios de sesión de Firebase.

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
SQLite como con PostgreSQL.

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
