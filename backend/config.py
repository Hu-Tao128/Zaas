import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-cambiar-en-produccion')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///zaas.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')

    # Supabase
    SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
    SUPABASE_KEY = os.environ.get('SUPABASE_KEY', '')

    # Firebase Auth
    FIREBASE_KEY_PATH = os.path.join(
        os.path.abspath(os.path.dirname(__file__)),
        os.environ.get('FIREBASE_KEY_PATH', 'keys/key.json')
    )

    # --- CONFIGURACIÓN PARA CLOUDFLARE TUNNEL Y SUBDOMINIOS ---
    # Necesario para que las cookies viajen entre zaas. y backend. sobre HTTPS
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'None'
    SESSION_COOKIE_DOMAIN = '.shellycornet.com'

    # Necesario porque tienes WTF_CSRF_ENABLED = True
    WTF_CSRF_SSL_STRICT = False
    WTF_CSRF_TRUSTED_ORIGINS = [
        'https://shellycornet.com',
        'http://localhost:3000'
    ]

