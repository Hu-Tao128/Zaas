import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from supabase import create_client, Client

db = SQLAlchemy()
login_manager = LoginManager()

# Supabase client — se inicializa en create_app()
supabase: Client | None = None


def init_supabase(app):
    """Inicializa el cliente de Supabase con las variables de entorno del app."""
    global supabase
    url = app.config.get('SUPABASE_URL', '').strip()
    key = app.config.get('SUPABASE_KEY', '').strip()

    # Validar que las credenciales no estén vacías o sean placeholders
    if not url or not key or 'tu-proyecto' in url or 'tu-api-key' in key:
        app.logger.warning(
            'Supabase no configurado: faltan SUPABASE_URL o SUPABASE_KEY válidas. '
            'Las operaciones con Supabase no estarán disponibles. '
            'Consulta docs/SUPABASE_USAGE.md'
        )
        supabase = None
        return

    try:
        supabase = create_client(url, key)
        app.logger.info(f'Supabase inicializado: {url}')
    except Exception as e:
        app.logger.error(f'Error al inicializar Supabase: {e}')
        supabase = None


def get_supabase() -> Client:
    """Obtiene el cliente de Supabase. Lanza RuntimeError si no está inicializado."""
    if supabase is None:
        raise RuntimeError(
            'Supabase no está inicializado. Verifica que SUPABASE_URL y '
            'SUPABASE_KEY estén configuradas en el entorno o .env'
        )
    return supabase
