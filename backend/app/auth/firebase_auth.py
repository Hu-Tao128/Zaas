"""
Servicio de autenticación con Firebase.
Maneja la verificación de tokens, creación de usuarios y linkage con Supabase.
"""

import os
from functools import lru_cache
import firebase_admin
from firebase_admin import auth, credentials
from supabase import create_client, Client
from app.extensions import get_supabase


def init_firebase(app):
    """Inicializa Firebase Admin SDK con la service account key."""
    key_path = app.config.get('FIREBASE_KEY_PATH', './keys/key.json')
    
    if not os.path.exists(key_path):
        app.logger.warning(
            f'Firebase key no encontrado en {key_path}. '
            'La autenticación con Firebase no estará disponible.'
        )
        return False
    
    try:
        # Evitar re-inicialización si ya está inicializado
        if not firebase_admin._apps:
            cred = credentials.Certificate(key_path)
            firebase_admin.initialize_app(cred)
            app.logger.info(f'Firebase inicializado con key: {key_path}')
        return True
    except Exception as e:
        app.logger.error(f'Error al inicializar Firebase: {e}')
        return False


def verify_firebase_token(id_token: str) -> dict | None:
    """
    Verifica un ID token de Firebase y devuelve los datos del usuario.
    Retorna None si el token es inválido.
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        return {
            'uid': decoded_token['uid'],
            'email': decoded_token.get('email'),
            'name': decoded_token.get('name'),
            'email_verified': decoded_token.get('email_verified', False),
        }
    except Exception as e:
        return None


def get_or_create_user_in_supabase(firebase_user: dict) -> dict:
    """
    Busca o crea un usuario en Supabase usando el UID de Firebase.
    Retorna el registro de usuario de Supabase.
    """
    supabase = get_supabase()
    uid = firebase_user['uid']
    
    # Buscar usuario existente
    response = supabase.table('usuarios_auth').select('*').eq('firebase_uid', uid).execute()
    
    if response.data:
        return response.data[0]
    
    # Crear nuevo registro
    response = supabase.table('usuarios_auth').insert({
        'firebase_uid': uid,
        'email': firebase_user.get('email'),
        'nombre': firebase_user.get('name'),
        'email_verificado': firebase_user.get('email_verified', False),
    }).execute()
    
    return response.data[0] if response.data else None


def create_custom_token(uid: str, additional_claims: dict = None) -> str:
    """
    Crea un custom token de Firebase para sign-in programático.
    Útil para migración de usuarios existentes.
    """
    return auth.create_custom_token(uid, additional_claims or {}).decode('utf-8')
