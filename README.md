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
- **SQLite local** → Datos de usuario (perfil, proyectos, ofertas, contratos)
- **Supabase** → Datos compartidos (notificaciones, métricas, config global)
- **Firebase Analytics** → Tracking de eventos en el frontend

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
python seed.py            # Crear DB y datos de prueba
python run.py             # Servidor en http://localhost:5000
```

## Frontend (React)

```bash
cd frontend
pnpm install              # Instalar dependencias
pnpm dev                  # Dev server en http://localhost:3000
pnpm build                # Build para producción
```

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
