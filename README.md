# Zaas

Plataforma de servicios de desarrollo de software con escrow, contratos y mensajería.

## Estructura del Proyecto

```
Zaas/
├── backend/              # Flask + Firebase Admin + Supabase
│   ├── app/              # Blueprints y lógica de negocio
│   │   ├── auth/         # Aya — usuarios, perfiles, Firebase Auth
│   │   ├── catalogo/     # Jean — proyectos, ofertas, postulaciones
│   │   ├── contratos/    # Sidrac — contratos, entregables, aceptaciones
│   │   ├── pagos/        # Daniel — pagos escrow, disputas, recibos
│   │   └── comunicacion/ # Gael — mensajes, notificaciones, calificaciones
│   ├── config.py         # Configuración por entorno
│   ├── run.py            # Entry point del servidor Flask
│   ├── seed.py           # Datos de prueba
│   ├── requirements.txt
│   └── keys/             # Firebase Service Account Key (NO commitear)
│
├── frontend/             # React + Vite + Firebase Auth + Analytics
│   ├── src/
│   │   ├── components/   # Componentes reutilizables
│   │   ├── pages/        # Páginas (Login, Registro, Home, etc.)
│   │   ├── services/     # Firebase Auth + API calls
│   │   ├── context/      # Auth context (estado global)
│   │   └── firebase.js   # Firebase config + Analytics
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
│
└── README.md
```

## Arquitectura

- **Firebase Auth** → Autenticación (email/password + Google Sign-In)
- **Supabase (Postgres)** → Base de datos principal y única del MR (27 tablas + IoT)
- **SQLAlchemy + psycopg2** → Acceso a Supabase (Session Pooler)
- **Firebase Analytics** → Tracking de eventos en el frontend

### Firebase Auth + Supabase

El frontend autentica con Firebase y el backend valida el ID token en
`POST /auth/firebase-login`. Desde ahí se crea/actualiza `usuario` y `perfil`
directamente en Supabase Postgres mediante SQLAlchemy. No se usa Supabase Auth,
PostgREST ni la `service_role` key.
La guía está en [`backend/docs/FIREBASE_SUPABASE.md`](backend/docs/FIREBASE_SUPABASE.md).

```bash
cd backend
DATABASE_URL="postgresql://...:5432/postgres?sslmode=require" python migrate_mr.py
```

## Contratos (v1.0)

Al crear un contrato el cliente elige al desarrollador, el producto/oferta
relacionados, el costo y la plantilla. El sistema genera una copia de los
términos con los nombres de ambas partes y la guarda en
`contrato.terminos_condiciones`; si la plantilla cambia después, los contratos
ya creados conservan su versión original.

Para formalizar el contrato, cada parte entra a **Revisar y aceptar contrato**,
marca la casilla de aceptación y confirma. Se registra la fecha, la IP y un
folio de firma (hash). El contrato pasa a `aceptado` cuando ambas partes firman.

Flujo de estados:

```
borrador → pendiente → aceptado → en_progreso → entregado → finalizado
```

La plantilla base se crea automáticamente al arrancar el backend
(`backend/app/contratos/plantillas.py`) y también se incluye en `python seed.py`
para bases de datos nuevas.

Guía detallada de cambios y pruebas:
[`backend/docs/CONTRATOS_V1.md`](backend/docs/CONTRATOS_V1.md).

## Backend (Flask)

```bash
cd backend
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # define DATABASE_URL de Supabase
python migrate_mr.py      # Crea/actualiza el esquema en Supabase
python seed.py            # (Opcional) datos de demostración
python run.py             # Servidor en http://localhost:5000
```

La base de datos es Supabase/PostgreSQL; no hay SQLite en desarrollo ni en
producción. SQLite queda únicamente como motor de las pruebas automatizadas.
Las cuentas añadidas por el seed requieren una cuenta en Firebase Auth para
iniciar sesión.

Para el despliegue HTTPS entre subdominios, configura `SESSION_COOKIE_DOMAIN`
con el dominio compartido. En localhost se deja sin configurar.

## Frontend (React)

```bash
cd frontend
pnpm install              # Instalar dependencias
pnpm dev                  # Dev server en http://localhost:3000
pnpm build                # Build para producción
```

## Docker

El proyecto completo se puede levantar con Docker Compose sin instalar Python
ni Node en la máquina:

```bash
cp .env.example .env                    # DATABASE_URL de Supabase, puertos, etc.
cp frontend/.env.example frontend/.env  # configuración web de Firebase
# coloca la llave de Firebase Admin en backend/keys/key.json
docker compose up --build
```

La aplicación queda en <http://localhost:8080>. La guía completa (Supabase,
Session Pooler, File Mount de Firebase y solución de problemas) está en
[DOCKER.md](DOCKER.md).

## Comunicación y administración

Las pantallas de comunicación están en `http://localhost:3000/comunicacion`.
El panel provisional está en `http://localhost:3000/admin` y solo permite el acceso
a usuarios con rol `admin`, validado en el backend. Ambas secciones comparten la
navegación y la paleta roja, negra y gris del catálogo.

Consulta la [referencia de la API](backend/docs/COMUNICACION_API.md) y el
[informe de cambios](CAMBIOS_COMUNICACION.md) para ver permisos, pruebas y pendientes.

## Ramas

- `main` — rama estable
- `develop` — rama de desarrollo (aquí van los commits)
- Una rama por persona para cada feature

## Roles

| Persona | Módulo | Tablas principales |
|---|---|---|
| Aya | auth | usuario, perfil |
| Jean | catalogo | proyecto, oferta_trabajo, postulacion, solicitud_demo |
| Sidrac | contratos | contrato, entregable, aceptacion, plantilla_contrato |
| Daniel | pagos | pago, liberacion, recibo, disputa, arbitraje |
| Gael | comunicacion | conversacion, mensaje, notificacion, calificacion, incidencia |

## Versionamiento

La versión actual vive en [`VERSION`](VERSION) y en `frontend/package.json`.
El historial está en [`CHANGELOG.md`](CHANGELOG.md).

```bash
./scripts/release.sh --bump minor --yes    # 1.x.0
./scripts/release.sh --bump patch --yes    # 1.x.x
./scripts/release.sh --bump major --yes    # cambios incompatibles
```

El script actualiza `VERSION` y `frontend/package.json`, crea el commit
`chore(release): vX.Y.Z`, publica el commit y crea el tag/release en GitHub.
Requiere `gh auth login`.
