"""
Servicio de autenticación con Firebase Admin SDK.
Inicializa Firebase y provee funciones para verificar tokens y gestionar usuarios.
"""

import json
import os
import firebase_admin
from firebase_admin import auth


_firebase_initialized = False


def init_firebase_app(key_path: str, credentials_json: str | None = None) -> bool:
    """
    Inicializa Firebase Admin SDK con la service account key.

    Acepta el JSON de la service account directamente (útil en plataformas como
    Coolify donde no conviene montar archivos) o la ruta a un archivo local.
    Retorna True si la inicialización fue exitosa.
    """
    global _firebase_initialized

    if _firebase_initialized:
        return True

    try:
        if credentials_json:
            cred = firebase_admin.credentials.Certificate(json.loads(credentials_json))
        elif key_path and os.path.exists(key_path):
            cred = firebase_admin.credentials.Certificate(key_path)
        else:
            return False

        firebase_admin.initialize_app(cred)
        _firebase_initialized = True
        return True
    except Exception:
        return False


def verify_firebase_token(id_token: str) -> dict | None:
    """
    Verifica un ID token de Firebase Auth.
    Retorna los datos del usuario decodificados o None si es inválido.
    """
    if not _firebase_initialized:
        return None

    try:
        decoded_token = auth.verify_id_token(id_token)
        return {
            'uid': decoded_token['uid'],
            'email': decoded_token.get('email'),
            'email_verified': decoded_token.get('email_verified', False),
            'name': decoded_token.get('name'),
            'picture': decoded_token.get('picture'),
        }
    except Exception:
        return None


def get_firebase_user(uid: str):
    """Obtiene un usuario de Firebase por UID."""
    if not _firebase_initialized:
        return None
    try:
        return auth.get_user(uid)
    except Exception:
        return None


def revoke_firebase_sessions(uid: str):
    """Revoca todas las sesiones de un usuario en Firebase (logout completo)."""
    if not _firebase_initialized:
        return False
    try:
        auth.revoke_refresh_tokens(uid)
        return True
    except Exception:
        return False


def is_firebase_ready() -> bool:
    """Verifica si Firebase está inicializado y listo."""
    return _firebase_initialized
