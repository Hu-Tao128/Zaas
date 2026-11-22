import os
from urllib.parse import urlsplit

from dotenv import load_dotenv
from sqlalchemy.pool import NullPool

from app.db_url import normalizar_database_url

# Carga .env solo en local. En contenedores (Coolify, Docker, etc.) las variables
# ya vienen definidas por el entorno y no deben ser sobrescritas por un archivo.
load_dotenv(override=False)


def _env(nombre, default=None):
    """Lee una variable de entorno y trata los valores vacíos como ausentes."""
    valor = os.environ.get(nombre)
    if valor is None:
        return default
    valor = valor.strip()
    return valor if valor else default


def _bool_env(nombre, default=False):
    valor = _env(nombre)
    if valor is None:
        return default
    return valor.lower() in {'1', 'true', 't', 'yes', 'y', 'on'}


def _int_env(nombre, default):
    valor = _env(nombre)
    if valor is None:
        return default
    try:
        return int(valor)
    except (TypeError, ValueError):
        return default


def _lista_env(nombre, default=None):
    valor = _env(nombre)
    if not valor:
        return list(default or [])
    return [item.strip() for item in valor.split(',') if item.strip()]


def _database_url():
    url = _env('DATABASE_URL')
    if not url:
        raise RuntimeError(
            'DATABASE_URL es obligatoria. Configura la cadena de conexión de '
            'Supabase (Session Pooler, puerto 5432) con ?sslmode=require.'
        )
    return normalizar_database_url(url)


def _engine_options(url):
    """Opciones de pool adecuadas para Supabase/Postgres."""
    opciones = {
        'pool_pre_ping': True,
        'pool_recycle': _int_env('DB_POOL_RECYCLE', 300),
        'pool_timeout': _int_env('DB_POOL_TIMEOUT', 30),
    }
    partes = urlsplit(url)
    # El Transaction Pooler (puerto 6543) no soporta reutilizar conexiones con
    # estado; con él se recomienda NullPool. El Session Pooler (5432) sí puede
    # usar el pool normal.
    if partes.port == 6543:
        opciones['poolclass'] = NullPool
    else:
        opciones['pool_size'] = _int_env('DB_POOL_SIZE', 5)
        opciones['max_overflow'] = _int_env('DB_MAX_OVERFLOW', 10)
    return opciones


DATABASE_URL = _database_url()

# Orígenes por defecto para desarrollo local y el dominio actual. En Coolify
# deben sobreescribirse con CORS_ORIGINS y CSRF_TRUSTED_ORIGINS.
_ORIGENES_POR_DEFECTO = [
    'http://localhost:3000',
    'http://localhost:8080',
    'https://zaas.shellycornet.com',
]


class Config:
    SECRET_KEY = _env('SECRET_KEY', 'dev-secret-key-cambiar-en-produccion')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = _engine_options(DATABASE_URL)
    WTF_CSRF_ENABLED = True
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')

    # En producción el esquema se crea/actualiza con migrate_mr.py antes de
    # arrancar Gunicorn. En local y pruebas se permite crear tablas al vuelo.
    AUTO_CREATE_SCHEMA = _bool_env('AUTO_CREATE_SCHEMA', True)

    # Firebase Auth. Se puede usar un archivo (FIREBASE_KEY_PATH) o inyectar el
    # JSON de la service account directamente en una variable de entorno
    # (FIREBASE_CREDENTIALS_JSON), más cómodo en Coolify.
    FIREBASE_KEY_PATH = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        _env('FIREBASE_KEY_PATH', 'keys/key.json')
    )
    FIREBASE_CREDENTIALS_JSON = _env('FIREBASE_CREDENTIALS_JSON')

    # --- CONFIGURACIÓN PARA CLOUDFLARE TUNNEL, COOLIFY Y SUBDOMINIOS ---
    # Orígenes permitidos por CORS. En producción define, por ejemplo:
    #   CORS_ORIGINS=https://zaas.example.com,https://www.zaas.example.com
    CORS_ORIGINS = _lista_env('CORS_ORIGINS', _ORIGENES_POR_DEFECTO)
    WTF_CSRF_TRUSTED_ORIGINS = _lista_env('CSRF_TRUSTED_ORIGINS', _ORIGENES_POR_DEFECTO)

    # Necesario para que las cookies viajen entre subdominios sobre HTTPS.
    SESSION_COOKIE_DOMAIN = _env('SESSION_COOKIE_DOMAIN') or None
    SESSION_COOKIE_SECURE = _bool_env(
        'SESSION_COOKIE_SECURE', bool(SESSION_COOKIE_DOMAIN)
    )
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = _env(
        'SESSION_COOKIE_SAMESITE', 'None' if SESSION_COOKIE_DOMAIN else 'Lax'
    )

    # Necesario porque WTF_CSRF_ENABLED = True y la app corre detrás de un proxy.
    WTF_CSRF_SSL_STRICT = False
