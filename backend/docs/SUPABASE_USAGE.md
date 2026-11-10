# Supabase en ZaaS

## Configuración

1. Copia `.env.example` a `.env` y completa:
   ```bash
   cp .env.example .env
   ```
2. Obtén `SUPABASE_URL` y `SUPABASE_KEY` (service_role) en
   [Supabase Dashboard](https://app.supabase.com/project/_/settings/api).

No se usa Supabase Auth ni Third-Party Auth. Firebase autentica y el backend
guarda los usuarios en Supabase con la `service_role` key.

## Login Firebase -> Supabase

El frontend envía el ID token de Firebase a:

```
POST /auth/firebase-login
```

El backend:

1. verifica el token con Firebase Admin,
2. crea/actualiza el usuario local (sesión Flask),
3. hace upsert en `public.usuario` por `firebase_uid`/`email`,
4. crea `public.perfil` si falta,
5. devuelve `id`, `firebase_uid`, `email`, `tipo_usuario` y `supabase_id`.

Guía completa: [`FIREBASE_SUPABASE.md`](FIREBASE_SUPABASE.md).

## Sincronización masiva

```bash
cd backend
source .venv/bin/activate

python supabase_setup.py --verify           # 27 tablas del MR
python supabase_setup.py --sync-firebase    # usuarios de Firebase -> Supabase
```

## Cliente en el backend

```python
from app.extensions import get_supabase

client = get_supabase()
respuesta = client.table('usuario').select('*').eq('firebase_uid', uid).execute()
```

## RLS

Las tablas tienen RLS habilitado y sin políticas para `anon`/`authenticated`.
El backend usa `service_role`, que omite RLS. El frontend no se conecta directo
a Supabase; consume la API Flask.

## Notas

- El cliente se inicializa una sola vez al arrancar la app (`init_supabase`).
- No mezcles SQLAlchemy y Supabase para la misma tabla: elige una fuente de
  verdad. SQLite es el entorno local y Supabase el MR compartido.
- Para queries complejas, usa Supabase; para relaciones y transacciones, SQLAlchemy.
