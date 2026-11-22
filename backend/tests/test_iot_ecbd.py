"""Pruebas del módulo IoT y del pipeline ECBD con SQLite en memoria."""

import hashlib
import unittest

from app import create_app
from app.auth.models import Usuario
from app.extensions import db, login_manager
from app.models.iot import DispositivoIoT, TelemetriaECBD
from app.services.ecbd_service import (
    ejecutar_etl_saneamiento,
    exportar_dataset_limpio,
    obtener_kpis_dashboard,
)


class TestConfig:
    TESTING = True
    SECRET_KEY = 'iot-ecbd-tests-only'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SUPABASE_URL = ''
    SUPABASE_KEY = ''
    FIREBASE_KEY_PATH = 'no-test-credentials.json'


class IoTEcbdTest(unittest.TestCase):
    API_KEY = 'api-key-de-prueba'

    def setUp(self):
        self.app = create_app(TestConfig)
        login_manager.session_protection = None
        self.client = self.app.test_client()

        key_hash = hashlib.sha256(self.API_KEY.encode('utf-8')).hexdigest()
        with self.app.app_context():
            db.session.add_all([
                Usuario(id=1, nombres='Admin', apellido_paterno='Prueba',
                        email='admin-iot@example.com', tipo_usuario='admin'),
                Usuario(id=2, nombres='Cliente', apellido_paterno='Prueba',
                        email='cliente-iot@example.com', tipo_usuario='cliente'),
                DispositivoIoT(id_dispositivo=1, nombre='Sensor de prueba',
                               modelo_hardware='ESP32-S3', api_key_hash=key_hash),
            ])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def login(self, usuario_id):
        with self.client.session_transaction() as sesion:
            sesion['_user_id'] = str(usuario_id)
            sesion['_fresh'] = True

    def headers(self, api_key=None):
        return {'X-Device-API-Key': api_key or self.API_KEY}

    def test_endpoints_exigen_api_key_valida(self):
        sin_key = self.client.post('/api/v1/iot/telemetria', json={'modulo': 'sensor'})
        self.assertEqual(sin_key.status_code, 401)

        key_invalida = self.client.post(
            '/api/v1/iot/telemetria',
            json={'modulo': 'sensor'},
            headers=self.headers('clave-incorrecta'),
        )
        self.assertEqual(key_invalida.status_code, 403)

    def test_telemetria_y_evento_se_persisten(self):
        respuesta = self.client.post(
            '/api/v1/iot/telemetria',
            json={
                'modulo': 'Sensor',
                'latencia_ms': 18.5,
                'memoria_libre_kb': 420,
                'resumen_agente': 'lectura periódica',
            },
            headers=self.headers(),
        )
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json['status'], 'ok')

        evento = self.client.post(
            '/api/v1/dispositivos/evento',
            json={'modulo': 'Cámara', 'descripcion': 'sin respuesta'},
            headers=self.headers(),
        )
        self.assertEqual(evento.status_code, 201)
        self.assertEqual(evento.json['status'], 'alerta_registrada')

        with self.app.app_context():
            registros = db.session.scalars(
                db.select(TelemetriaECBD).order_by(TelemetriaECBD.id_registro)
            ).all()
            self.assertEqual(len(registros), 2)
            self.assertEqual(registros[0].modulo_evaluado, 'sensor')
            self.assertEqual(registros[0].latencia_ms, 18.5)
            self.assertEqual(registros[1].tipo_evento, 'evento_anomalia')
            self.assertTrue(registros[1].anomalia_detectada)

            dispositivo = db.session.get(DispositivoIoT, 1)
            self.assertIsNotNone(dispositivo.ultimo_ping)

    def test_etl_sanea_normaliza_y_marca_procesados(self):
        with self.app.app_context():
            db.session.add_all([
                TelemetriaECBD(id_dispositivo=1, tipo_evento='telemetria',
                               modulo_evaluado=' SENSOR ', latencia_ms=None,
                               memoria_libre_kb=128, payload_crudo={'ok': True}),
                TelemetriaECBD(id_dispositivo=1, tipo_evento='evento_anomalia',
                               modulo_evaluado='Cámara', latencia_ms=None,
                               memoria_libre_kb=None, payload_crudo={}),
                TelemetriaECBD(id_dispositivo=1, tipo_evento='telemetria',
                               modulo_evaluado='Audio', latencia_ms=10,
                               memoria_libre_kb=64, payload_crudo=[1, 2]),
            ])
            db.session.commit()

            resultado = ejecutar_etl_saneamiento()
            self.assertEqual(resultado['saneados'], 1)
            self.assertEqual(resultado['descartados'], 2)
            self.assertEqual(resultado['total_procesados'], 3)

            registros = db.session.scalars(
                db.select(TelemetriaECBD).order_by(TelemetriaECBD.id_registro)
            ).all()
            self.assertTrue(all(registro.procesado_etl for registro in registros))
            self.assertEqual(registros[0].modulo_evaluado, 'sensor')
            self.assertEqual(registros[0].latencia_ms, 0.0)
            self.assertEqual(registros[1].modulo_evaluado, 'cámara')
            self.assertEqual(registros[1].memoria_libre_kb, 0)

            dataset = exportar_dataset_limpio(limite=10)
            self.assertEqual(len(dataset), 3)
            self.assertIn('latencia_ms', dataset[0])
            self.assertIn('fecha_captura', dataset[0])

            self.assertEqual(ejecutar_etl_saneamiento()['total_procesados'], 0)

    def test_kpis_requiere_admin_y_devuelve_agregados(self):
        with self.app.app_context():
            db.session.add_all([
                TelemetriaECBD(id_dispositivo=1, tipo_evento='telemetria',
                               modulo_evaluado='sensor', latencia_ms=10,
                               memoria_libre_kb=100, payload_crudo={}),
                TelemetriaECBD(id_dispositivo=1, tipo_evento='evento_anomalia',
                               modulo_evaluado='sensor', latencia_ms=30,
                               memoria_libre_kb=80, anomalia_detectada=True,
                               payload_crudo={}),
                TelemetriaECBD(id_dispositivo=1, tipo_evento='telemetria',
                               modulo_evaluado='camera', latencia_ms=20,
                               memoria_libre_kb=60, payload_crudo={}),
            ])
            db.session.commit()
            kpis = obtener_kpis_dashboard()

        self.assertEqual(kpis['total_registros'], 3)
        self.assertEqual(kpis['total_anomalias'], 1)
        self.assertEqual(kpis['latencia_promedio_ms'], 20.0)
        self.assertEqual(kpis['eventos_por_modulo'], {'sensor': 2, 'camera': 1})

        self.assertEqual(self.client.get('/api/v1/admin/ecbd/kpis').status_code, 401)
        self.login(2)
        self.assertEqual(self.client.get('/api/v1/admin/ecbd/kpis').status_code, 403)
        self.login(1)
        respuesta = self.client.get('/api/v1/admin/ecbd/kpis')
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json['total_registros'], 3)


if __name__ == '__main__':
    unittest.main()
