import os
from dotenv import load_dotenv

# Cargar .env sobrescribiendo variables de entorno existentes
# (necesario porque puede haber keys viejas en el entorno del sistema)
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
