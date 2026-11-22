import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv

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


def _lista_env(nombre, default=None):
    valor = _env(nombre)
    if not valor:
        return list(default or [])
    return [item.strip() for item in valor.split(',') if item.strip()]


def _normalizar_database_url(url):
    """Adapta URLs de Postgres de Coolify/Supabase/Heroku para SQLAlchemy.

    - ``postgres://`` (Heroku/Coolify) y ``postgresql://`` se fuerzan a usar el
      driver ``psycopg2`` que ya está instalado en la imagen.
    - Se eliminan parámetros propios de Prisma (``pgbouncer``,
      ``connection_limit``, ``schema``) que ``psycopg2``/libpq rechazan.
    """
    if url.startswith('postgres://'):
        url = 'postgresql+psycopg2://' + url[len('postgres://'):]
    elif url.startswith('postgresql://'):
        url = 'postgresql+psycopg2://' + url[len('postgresql://'):]

    partes = urlsplit(url)
    if partes.scheme.startswith('postgresql'):
        excluir = {'pgbouncer', 'connection_limit', 'schema'}
        query = [
            (clave, valor)
            for clave, valor in parse_qsl(partes.query)
            if clave.lower() not in excluir
        ]
        url = urlunsplit(partes._replace(query=urlencode(query)))
    return url


def _database_url():
    return _normalizar_database_url(_env('DATABASE_URL', 'sqlite:///zaas.db'))


# Orígenes por defecto para desarrollo local y el dominio actual. En Coolify
# deben sobreescribirse con CORS_ORIGINS y CSRF_TRUSTED_ORIGINS.
_ORIGENES_POR_DEFECTO = [
    'http://localhost:3000',
    'http://localhost:8080',
    'https://zaas.shellycornet.com',
]


class Config:
    SECRET_KEY = _env('SECRET_KEY', 'dev-secret-key-cambiar-en-produccion')
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')

    # Supabase
    SUPABASE_URL = _env('SUPABASE_URL', '')
    SUPABASE_KEY = _env('SUPABASE_KEY', '')

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
