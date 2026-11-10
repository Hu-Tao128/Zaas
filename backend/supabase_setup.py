"""Sincronización Firebase Auth -> Supabase (sin Third-Party Auth).

El login real lo hace el backend en ``POST /auth/firebase-login``:
1. verifica el ID token de Firebase,
2. obtiene firebase_uid, email y datos del usuario,
3. escribe/actualiza ``public.usuario`` y ``public.perfil`` con la
   service_role key de Supabase.

Este script sirve para operaciones masivas y verificación:

    python supabase_setup.py --verify
    python supabase_setup.py --sync-firebase
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import get_supabase

TABLAS_MR = [
    'usuario', 'perfil', 'habilidad', 'perfil_habilidad', 'tecnologia',
    'perfil_tecnologia', 'categoria', 'proyecto', 'categoria_proyecto',
    'tecnologia_proyecto', 'solicitud_demo', 'oferta_trabajo', 'postulacion',
    'plantilla_contrato', 'contrato', 'entregable', 'aceptacion', 'pago',
    'liberacion', 'recibo', 'incidencia', 'disputa', 'arbitraje',
    'conversacion', 'mensaje', 'notificacion', 'calificacion',
]


def verificar_tablas():
    client = get_supabase()
    ok = True
    print('Verificando tablas del MR en Supabase...')
    for tabla in TABLAS_MR:
        try:
            client.table(tabla).select('id').limit(1).execute()
            print(f'  OK  {tabla}')
        except Exception as error:  # noqa: BLE001
            ok = False
            print(f'  ERR {tabla}: {str(error)[:120]}')
    return ok


def sincronizar_firebase():
    from app.auth.firebase_supabase import sync_all_firebase_users
    resultado = sync_all_firebase_users()
    print(
        'Sincronización Firebase -> Supabase: '
        f"{resultado['sincronizados']}/{resultado['total']} usuarios "
        f"(omitidos: {resultado['omitidos']}, errores: {resultado['errores']})"
    )
    return resultado['errores'] == 0


def main():
    parser = argparse.ArgumentParser(
        description='Sincroniza Firebase Auth con Supabase (backend, sin Third-Party Auth)'
    )
    parser.add_argument('--verify', action='store_true',
                        help='Verifica las 27 tablas del MR en Supabase')
    parser.add_argument('--sync-firebase', action='store_true',
                        help='Copia/actualiza todos los usuarios de Firebase en Supabase')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if not args.verify and not args.sync_firebase:
            args.verify = True

        if args.sync_firebase:
            sincronizar_firebase()
        if args.verify:
            verificar_tablas()


if __name__ == '__main__':
    main()
