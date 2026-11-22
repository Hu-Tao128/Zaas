# Firebase Auth + Supabase Postgres

ZaaS usa **Firebase Auth** para autenticar y **Supabase/PostgreSQL** como base
relacional principal. El backend valida el ID token de Firebase y escribe
`usuario`/`perfil` con **SQLAlchemy**, no con el cliente `supabase-py` ni la
`service_role` key.

## Flujo de login

```
React (Firebase Auth)
  └─ POST /auth/firebase-login { id_token, tipo_usuario?, nombres?, ... }
       ├─ verifica el ID token con Firebase Admin
       ├─ busca/crea Usuario y Perfil con SQLAlchemy en Supabase Postgres
       └─ devuelve { usuario: { id, firebase_uid, email, tipo_usuario } }
```

El endpoint es idempotente y sirve tanto para login como para registro:

```json
{
  "id_token": "eyJ...",
  "tipo_usuario": "desarrollador",
  "nombres": "Ana",
  "apellido_paterno": "García",
  "apellido_materno": "López"
}
```

`firebase_uid` se toma siempre del token verificado, no del cuerpo.

## Configuración

```env
DATABASE_URL=postgresql://postgres.<ref>:<clave>@aws-0-<region>.pooler.supabase.com:5432/postgres?sslmode=require
FIREBASE_KEY_PATH=/app/keys/key.json
# o bien:
FIREBASE_CREDENTIALS_JSON={"type":"service_account",...}
```

No se necesitan `SUPABASE_URL` ni `SUPABASE_KEY`.

## Esquema

El backend crea/actualiza las tablas con `migrate_mr.py`. Las sesiones Flask se
guardan con cookies; el usuario autenticado se carga desde `usuario` por id.

## RLS

Las tablas del MR tienen RLS habilitado sin políticas para `anon`/`authenticated`.
El backend usa el rol `postgres` del Session Pooler, que omite RLS. El frontend
solo consume la API Flask.

## Notas

- El correo se busca como respaldo para no duplicar cuentas.
- Si el email ya pertenece a otra cuenta de Firebase, no se reasigna el
  `firebase_uid`.
- Si falla la escritura en Supabase, el login responde con error y no se crea
  una sesión a medias.
