#!/usr/bin/env python3
import argparse
import hashlib
import secrets
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import create_app
from app.extensions import db
from app.models.iot import DispositivoIoT


def main():
    parser = argparse.ArgumentParser(
        description='Registra un dispositivo IoT y genera su API Key.',
    )
    parser.add_argument('--nombre', default='Dispositivo de prueba')
    parser.add_argument('--modelo', default='ESP32-S3')
    args = parser.parse_args()

    api_key = secrets.token_urlsafe(32)
    api_key_hash = hashlib.sha256(api_key.encode('utf-8')).hexdigest()

    app = create_app()
    with app.app_context():
        dispositivo = DispositivoIoT(
            nombre=args.nombre,
            modelo_hardware=args.modelo,
            api_key_hash=api_key_hash,
        )
        db.session.add(dispositivo)
        db.session.commit()

        print('Dispositivo registrado correctamente.')
        print(f'ID dispositivo: {dispositivo.id_dispositivo}')
        print(f'API Key (guárdala, no se volverá a mostrar): {api_key}')


if __name__ == '__main__':
    main()
