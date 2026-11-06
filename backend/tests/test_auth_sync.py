"""Regresiones para altas simultáneas y reintentos de sincronización."""

import unittest
from unittest.mock import patch
from app import create_app
from app.extensions import db, login_manager
from app.auth.models import Usuario, Perfil
from test_comunicacion import TestConfig


class AuthSyncTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        login_manager.session_protection = None
        self.client = self.app.test_client()
        self.identity = {'uid': 'firebase-client', 'email': 'cliente@example.com', 'name': 'Cliente Prueba'}
        self.verifier = patch('app.auth.routes.verify_firebase_token', side_effect=lambda token: self.identity)
        self.verifier.start()

    def tearDown(self):
        self.verifier.stop()
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def login(self):
        return self.client.post('/auth/callback', json={'id_token': 'token-verificado'})

    def register(self, role='cliente'):
        return self.client.post('/auth/registro/callback', json={
            'id_token': 'token-verificado', 'tipo_usuario': role})

    def assert_one_account(self, role='cliente'):
        with self.app.app_context():
            self.assertEqual(db.session.query(Usuario).count(), 1)
            self.assertEqual(db.session.query(Perfil).count(), 1)
            self.assertEqual(db.session.scalar(db.select(Usuario)).tipo_usuario, role)

    def test_repeated_login_is_idempotent_and_client_cannot_open_admin(self):
        first = self.login()
        second = self.login()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json['user']['id'], second.json['user']['id'])
        self.assert_one_account()
        self.assertEqual(self.client.get('/api/comunicacion/admin/resumen').status_code, 403)

    def test_actual_unique_constraint_after_stale_read_recovers_existing_user(self):
        first = self.login()
        # Simula el SELECT anterior a la confirmación del otro request. El INSERT
        # sí llega a SQLite y dispara su restricción UNIQUE real.
        with patch('app.auth.routes._buscar_usuario', return_value=None):
            second = self.login()
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json['user']['id'], second.json['user']['id'])
        self.assert_one_account()
        self.assertEqual(self.login().status_code, 200)  # sesión SQL recuperada tras rollback

    def test_registration_after_observer_login_and_retries_do_not_duplicate(self):
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.register().status_code, 200)
        self.assertEqual(self.register().status_code, 200)
        self.assert_one_account()

    def test_existing_admin_role_is_not_overwritten_by_registration(self):
        self.assertEqual(self.login().status_code, 200)
        with self.app.app_context():
            db.session.scalar(db.select(Usuario)).tipo_usuario = 'admin'
            db.session.commit()
        self.assertEqual(self.register('cliente').status_code, 200)
        self.assert_one_account('admin')
        self.assertEqual(self.client.get('/api/comunicacion/admin/resumen').status_code, 200)

    def test_new_developer_role_survives_later_client_requests(self):
        self.assertEqual(self.register('desarrollador').status_code, 200)
        self.assertEqual(self.login().status_code, 200)
        self.assertEqual(self.register('cliente').status_code, 200)
        self.assert_one_account('desarrollador')

    def test_email_collision_with_different_identity_does_not_return_another_user(self):
        self.assertEqual(self.login().status_code, 200)
        self.identity = self.identity | {'uid': 'different-uid'}
        with patch('app.auth.routes._buscar_usuario', return_value=None):
            result = self.login()
        self.assertEqual(result.status_code, 409)
        self.assertIn('error', result.json)
        self.assertNotIn('user', result.json)
        self.assert_one_account()
