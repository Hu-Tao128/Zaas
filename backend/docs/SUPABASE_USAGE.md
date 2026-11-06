# Supabase en Zaas

## Configuración

1. Copia `.env.example` a `.env` y completa las credenciales:
   ```bash
   cp .env.example .env
   ```
2. Obtén `SUPABASE_URL` y `SUPABASE_KEY` desde tu proyecto en [Supabase Dashboard](https://app.supabase.com).

## Cómo usar el cliente en cualquier blueprint

```python
from app.extensions import get_supabase

def mi_funcion():
    client = get_supabase()
    
    # SELECT
    response = client.table('mi_tabla').select('*').eq('estado', 'activo').execute()
    datos = response.data
    
    # INSERT
    response = client.table('mi_tabla').insert({'nombre': 'ejemplo'}).execute()
    
    # UPDATE
    response = client.table('mi_tabla').update({'nombre': 'nuevo'}).eq('id', 1).execute()
    
    # DELETE
    response = client.table('mi_tabla').delete().eq('id', 1).execute()
```

## Endpoints de ejemplo

El blueprint `supabase_api` incluye endpoints CRUD para la tabla `todos`:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/supabase/health` | Verifica conexión a Supabase |
| `GET` | `/api/supabase/todos` | Lista todos los todos |
| `POST` | `/api/supabase/todos` | Crea un nuevo todo |
| `PATCH` | `/api/supabase/todos/<id>` | Actualiza un todo |
| `DELETE` | `/api/supabase/todos/<id>` | Elimina un todo |

## Notas importantes

- El cliente se inicializa **una sola vez** al arrancar la app (`init_supabase`).
- Si faltan las credenciales, la app arranca pero `get_supabase()` lanza `RuntimeError`.
- **No mezcles** SQLAlchemy y Supabase para la misma tabla — elige una fuente de verdad.
- Para queries complejas, usa Supabase; para relaciones y transacciones, usa SQLAlchemy.
