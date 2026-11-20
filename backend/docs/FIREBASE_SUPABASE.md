# Firebase Auth + Supabase (sin Third-Party Auth)

ZaaS usa **Firebase Auth** para autenticar y **Supabase/Postgres** como base
relacional del MR. No se usa Supabase Third-Party Auth ni funciones/triggers
nativos de Supabase: el backend valida el token de Firebase y escribe
directamente en Supabase con la `service_role` key.

## Flujo de login

```
React (Firebase Auth)
  └─ POST /auth/firebase-login { id_token, tipo_usuario?, nombres?, ... }
       ├─ verifica el ID token con Firebase Admin
       ├─ crea/actualiza usuario en SQLite (sesión Flask)
       ├─ upsert en Supabase: public.usuario (por firebase_uid/email)
       ├─ crea public.perfil si no existe (1:1)
       └─ devuelve { usuario: { id, firebase_uid, email, tipo_usuario, supabase_id } }
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
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_KEY=<service_role_key>          # solo servidor
```

La `service_role` key **nunca** debe llegar al navegador. El frontend solo usa
la API Flask; no se conecta directo a Supabase.

## Sincronización masiva

```bash
cd backend
source .venv/bin/activate

python supabase_setup.py --verify           # comprueba las 27 tablas del MR
python supabase_setup.py --sync-firebase    # Firebase usuarios -> usuario/perfil
```

`--sync-firebase` recorre los usuarios de Firebase con el Admin SDK y reutiliza
la misma función que el endpoint de login.

## RLS

Las tablas del MR tienen RLS habilitado sin políticas para `anon`/`authenticated`.
El backend usa la `service_role` key, que omite RLS. No se requieren políticas
de Firebase JWT ni la integración Third-Party Auth.

## Notas

- El correo se busca como respaldo para no duplicar cuentas creadas antes del puente.
- Si el email ya pertenece a otra cuenta de Firebase, no se reasigna el `firebase_uid`.
- Si Supabase falla, `/auth/firebase-login` responde `502` para que el frontend
  muestre el error; no se crea una sesión a medias.
