"""Pruebas con SQLite en memoria; no usan Firebase, Supabase ni datos locales."""

import unittest
from unittest.mock import patch
from app import create_app
from app.extensions import db, login_manager
from app.auth.models import Usuario
from app.catalogo.models import Proyecto, SolicitudDemo
from app.contratos.models import Contrato, Entregable
from app.comunicacion.models import Mensaje, Notificacion, Calificacion, Incidencia
from app.comunicacion.services import crear_notificacion, ErrorComunicacion
from app.pagos.models import Disputa, Pago


class TestConfig:
    TESTING = True
    SECRET_KEY = 'comunicacion-tests-only'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SUPABASE_URL = ''
    SUPABASE_KEY = ''
    FIREBASE_KEY_PATH = 'no-test-credentials.json'


class ComunicacionTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        login_manager.session_protection = None
        self.client = self.app.test_client()
        with self.app.app_context():
            for id, rol in enumerate(['cliente', 'desarrollador', 'cliente', 'admin'], 1):
                db.session.add(Usuario(id=id, nombres=f'Usuario {id}', apellido_paterno='Prueba',
                                       email=f'usuario{id}@example.com', tipo_usuario=rol))
            db.session.add_all([
                Proyecto(id=1, id_usuario=2, titulo='Con demo', precio=100, demo_habilitada=True),
                Proyecto(id=2, id_usuario=2, titulo='Sin demo', precio=100, demo_habilitada=False),
                Contrato(id=1, id_cliente=1, id_desarrollador=2, id_producto=1, costo_acordado=100, estado='aceptado'),
                Contrato(id=2, id_cliente=1, id_desarrollador=2, id_producto=2, costo_acordado=100, estado='finalizado'),
            ])
            db.session.commit()
        self.login(1)

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def login(self, usuario):
        with self.client.session_transaction() as sesion:
            sesion.clear()
            sesion['_user_id'] = str(usuario)
            sesion['_fresh'] = True
        self.csrf = self.client.get('/api/comunicacion/sesion').json['csrf_token']

    def get(self, ruta):
        return self.client.get('/api/comunicacion' + ruta)

    def write(self, ruta, data=None, method='POST'):
        return self.client.open('/api/comunicacion' + ruta, method=method,
                                json=data or {}, headers={'X-CSRFToken': self.csrf})

    def conversation(self):
        response = self.write('/contratos/1/conversacion')
        self.assertEqual(response.status_code, 200)
        return response.json['data']['id']

    def test_requires_session_and_csrf(self):
        self.assertEqual(self.client.post('/api/comunicacion/incidencias', json={}).status_code, 400)
        with self.client.session_transaction() as sesion:
            sesion.clear()
        response = self.get('/notificaciones')
        self.assertEqual(response.status_code, 401)
        self.assertIn('error', response.json)

    def test_admin_panel_requires_server_role_and_session(self):
        rutas = ['/admin/resumen', '/admin/contratos', '/admin/pagos', '/admin/disputas', '/admin/usuarios']
        for user in (1, 2, 3):
            self.login(user)
            for ruta in rutas:
                with self.subTest(usuario=user, ruta=ruta):
                    response = self.get(f'{ruta}?tipo_usuario=admin')
                    self.assertEqual(response.status_code, 403)
                    self.assertNotIn('data', response.json)
        with self.client.session_transaction() as sesion:
            sesion.clear()
        for ruta in rutas:
            self.assertEqual(self.get(ruta).status_code, 401)

    def test_admin_can_filter_contracts_deliverables_and_user_roles(self):
        with self.app.app_context():
            db.session.add_all([
                Entregable(id_contrato=1, titulo='Prototipo', estado='aprobado'),
                Entregable(id_contrato=1, titulo='Versión final', estado='pendiente'),
            ])
            db.session.commit()
        self.login(4)
        contratos = self.get('/admin/contratos?per_page=1').json
        self.assertEqual(contratos['meta']['total'], 2)
        self.assertTrue(contratos['meta']['has_next'])
        contrato = self.get('/admin/contratos?estado=aceptado').json['data'][0]
        self.assertEqual((contrato['objeto'], contrato['aprobados'], contrato['entregables']), ('Con demo', 1, 2))
        usuarios = self.get('/admin/usuarios?rol=cliente').json
        self.assertEqual([u['id'] for u in usuarios['data']], [3, 1])
        self.assertNotIn('firebase_uid', usuarios['data'][0])
        self.assertEqual(self.get('/admin/usuarios?rol=invalido').status_code, 400)

    def test_admin_payment_and_dispute_lists_reflect_contract_arbitration(self):
        with self.app.app_context():
            db.session.add(Pago(id=1, id_contrato=1, monto=100, estado_escrow='retenido', metodo_pago='simulado'))
            db.session.add(Disputa(id=1, id_contrato=1, id_pago=1, id_reportante=1, tipo='pago'))
            db.session.commit()
        self.login(4)
        pago = self.get('/admin/pagos?estado=retenido').json['data'][0]
        self.assertEqual((pago['id_contrato'], pago['metodo']), (1, 'simulado'))
        disputa = self.get('/admin/disputas?estado=abierta').json['data'][0]
        self.assertEqual((disputa['id_contrato'], disputa['reportante']), (1, 'Usuario 1 Prueba'))

        detalle = self.client.get('/contratos/api/1').json['contrato']
        self.assertTrue(detalle['acciones']['es_admin'])
        self.assertFalse(detalle['acciones']['puede_liberar'])
        resultado = self.client.post('/contratos/api/disputas/1/resolver',
                                     json={'decision': 'reembolsar', 'notas': 'Prueba local'},
                                     headers={'X-CSRFToken': self.csrf})
        self.assertEqual(resultado.status_code, 200)
        self.assertEqual(self.get('/admin/disputas?estado=abierta').json['data'], [])
        self.assertEqual(self.get('/admin/pagos?estado=reembolsado').json['data'][0]['id'], 1)

    def test_admin_summary_contains_real_counts_and_only_five_recent_reports(self):
        with self.app.app_context():
            for id, state in enumerate(['abierta', 'en_proceso', 'resuelta', 'cerrada', 'abierta', 'abierta'], 1):
                db.session.add(Incidencia(id=id, id_usuario=1, tipo='bug', descripcion=f'Reporte {id}', estado=state))
            db.session.commit()
        self.login(4)
        response = self.get('/admin/resumen')
        self.assertEqual(response.status_code, 200)
        summary = response.json['data']
        self.assertEqual(summary['usuario']['tipo_usuario'], 'admin')
        self.assertEqual(summary['incidencias'], {'total': 6, 'pendientes': 4, 'resueltas': 2})
        self.assertEqual([r['id'] for r in summary['recientes']], [6, 5, 4, 3, 2])
        incidencias = self.get('/incidencias?todas=true&estado=abierta&per_page=1&page=2').json
        self.assertEqual(incidencias['meta']['total'], 3)
        self.assertEqual(incidencias['data'][0]['id'], 5)

    def test_public_registration_cannot_assign_admin_or_unknown_role(self):
        for role in ['admin', 'superadmin', None, ['admin']]:
            response = self.client.post('/auth/registro/callback', json={
                'id_token': 'no-validado', 'tipo_usuario': role})
            self.assertEqual(response.status_code, 403)
        with self.app.app_context():
            self.assertEqual(db.session.query(Usuario).count(), 4)

    def test_unverified_tokens_cannot_create_an_admin_session(self):
        import jwt
        with self.client.session_transaction() as sesion:
            sesion.clear()
        token = jwt.encode({'sub': 'forged', 'email': 'usuario4@example.com'}, key='', algorithm='none')
        with patch('app.auth.routes.verify_firebase_token', return_value=None), \
             patch('app.auth.routes.is_firebase_ready', return_value=False):
            response = self.client.post('/auth/callback', json={'id_token': token})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get('/admin/resumen').status_code, 401)

    def test_verified_admin_can_access_and_verified_client_cannot_choose_role(self):
        with patch('app.auth.routes.verify_firebase_token', return_value={
            'uid': 'firebase-admin-test', 'email': 'usuario4@example.com', 'name': 'Admin Test'}):
            self.assertEqual(self.client.post('/auth/callback', json={'id_token': 'verificado'}).status_code, 200)
        self.assertEqual(self.get('/admin/resumen').status_code, 200)
        with patch('app.auth.routes.verify_firebase_token', return_value={
            'uid': 'firebase-client-test', 'email': 'usuario1@example.com', 'name': 'Cliente Test'}):
            self.assertEqual(self.client.post('/auth/callback', json={
                'id_token': 'verificado', 'tipo_usuario': 'admin'}).status_code, 200)
        self.assertEqual(self.get('/admin/resumen').status_code, 403)

    def test_invalid_json_and_pagination(self):
        response = self.client.post('/api/comunicacion/incidencias', json=[],
                                    headers={'X-CSRFToken': self.csrf})
        self.assertEqual(response.status_code, 400)
        for query in ['page=0', 'page=no', 'per_page=101', 'per_page=0']:
            self.assertEqual(self.get('/notificaciones?' + query).status_code, 400)
        self.assertEqual(self.get('/notificaciones?page=999').json['data'], [])

    def test_contracts_and_conversations_are_private(self):
        id = self.conversation()
        self.assertEqual(self.conversation(), id)
        self.login(3)
        self.assertEqual(self.get('/contratos').json['data'], [])
        self.assertEqual(self.get('/conversaciones').json['data'], [])
        for ruta in [f'/conversaciones/{id}/mensajes']:
            self.assertEqual(self.get(ruta).status_code, 403)
            self.assertEqual(self.write(ruta, {'contenido': 'No permitido'}).status_code, 403)
        self.assertEqual(self.write(f'/conversaciones/{id}/leer').status_code, 403)
        self.assertEqual(self.write('/contratos/1/conversacion').status_code, 403)
        self.assertEqual(self.write('/contratos/999/conversacion').status_code, 404)
        self.assertEqual(self.get('/contratos/1/mensajes').status_code, 403)
        self.login(4)
        self.assertEqual(self.get('/contratos/1/mensajes').status_code, 403)

    def test_messages_notification_and_read_receipts(self):
        id = self.conversation()
        sent = self.write(f'/conversaciones/{id}/mensajes', {'contenido': ' Hola ', 'id_receptor': 3})
        self.assertEqual(sent.status_code, 201)
        self.assertEqual(sent.json['data']['contenido'], 'Hola')
        self.assertEqual(sent.json['data']['id_receptor'], 2)
        historial = self.get('/contratos/1/mensajes').json['data']
        self.assertEqual(historial[0]['contenido'], 'Hola')
        self.assertEqual(historial[0]['emisor']['nombre_completo'], 'Usuario 1 Prueba')
        self.assertEqual(self.get('/notificaciones').json['meta']['total'], 0)
        self.write(f'/conversaciones/{id}/leer')
        self.assertFalse(self.get(f'/conversaciones/{id}/mensajes').json['data'][0]['leido'])
        self.login(2)
        self.assertEqual(self.get('/conversaciones').json['data'][0]['no_leidos'], 1)
        self.assertEqual(self.get('/notificaciones').json['no_leidas'], 1)
        # Leer el historial no altera el estado; la escritura es explícita y protegida.
        self.get(f'/conversaciones/{id}/mensajes')
        self.assertEqual(self.write(f'/conversaciones/{id}/leer').json['data']['actualizados'], 1)
        self.assertTrue(self.get(f'/conversaciones/{id}/mensajes').json['data'][0]['leido'])

    def test_incidencia_admite_solo_contratos_del_reportante(self):
        datos = {'tipo': 'bug', 'descripcion': 'Prueba con contrato', 'id_contrato': 1}
        respuesta = self.write('/incidencias', datos)
        self.assertEqual(respuesta.status_code, 201)
        self.assertEqual(respuesta.json['data']['id_contrato'], 1)
        self.login(3)
        self.assertEqual(self.write('/incidencias', datos).status_code, 403)

    def test_message_validation_and_pagination(self):
        id = self.conversation()
        for contenido in ['', '   ', None, 123, 'x' * 5001]:
            self.assertEqual(self.write(f'/conversaciones/{id}/mensajes', {'contenido': contenido}).status_code, 400)
        for contenido in ['primero', 'segundo', 'tercero']:
            self.write(f'/conversaciones/{id}/mensajes', {'contenido': contenido})
        response = self.get(f'/conversaciones/{id}/mensajes?per_page=2')
        self.assertEqual([m['contenido'] for m in response.json['data']], ['tercero', 'segundo'])
        self.assertTrue(response.json['meta']['has_next'])
        self.assertEqual(self.get(f'/conversaciones/{id}/mensajes?per_page=2&page=2').json['data'][0]['contenido'], 'primero')

    def test_notification_helper_does_not_commit(self):
        with self.app.app_context():
            crear_notificacion(db.session.get(Usuario, 1), 'Nuevo contrato', '/comunicacion')
            db.session.flush()
            db.session.rollback()
            self.assertEqual(db.session.query(Notificacion).count(), 0)
            with self.assertRaises(ErrorComunicacion):
                crear_notificacion(999, 'Aviso')
            with self.assertRaises(ErrorComunicacion):
                crear_notificacion(1, 'Aviso', '//otro-sitio.com')

    def test_notification_ownership_and_mark_all(self):
        with self.app.app_context():
            crear_notificacion(1, 'Uno')
            crear_notificacion(2, 'Ajeno')
            db.session.commit()
        items = self.get('/notificaciones').json['data']
        self.assertEqual(len(items), 1)
        id = items[0]['id']
        self.login(2)
        self.assertEqual(self.write(f'/notificaciones/{id}/leer', method='PATCH').status_code, 403)
        self.write('/notificaciones/leer')
        self.assertEqual(self.get('/notificaciones?solo_no_leidas=true').json['data'], [])
        self.login(1)
        self.assertEqual(self.get('/notificaciones').json['no_leidas'], 1)
        self.assertEqual(self.write(f'/notificaciones/{id}/leer', method='PATCH').status_code, 200)
        self.assertEqual(self.get('/notificaciones').json['no_leidas'], 0)

    def test_demo_request_visibility_notification_and_duplicates(self):
        payload = {'nombre_contacto': 'Cliente', 'correo_contacto': 'cliente@example.com'}
        self.assertEqual(self.write('/proyectos/1/solicitudes-demo', payload).status_code, 201)
        self.assertEqual(self.write('/proyectos/1/solicitudes-demo', payload).status_code, 409)
        self.assertEqual(self.get('/solicitudes-demo').json['meta']['total'], 1)
        self.login(2)
        self.assertEqual(self.get('/solicitudes-demo').json['data'][0]['correo_contacto'], payload['correo_contacto'])
        self.assertEqual(self.get('/notificaciones').json['no_leidas'], 1)
        self.assertEqual(self.write('/proyectos/1/solicitudes-demo', payload).status_code, 403)
        self.login(3)
        self.assertEqual(self.get('/solicitudes-demo').json['data'], [])

    def test_demo_requires_availability_and_valid_contact(self):
        payload = {'nombre_contacto': 'Cliente', 'correo_contacto': 'cliente@example.com'}
        self.assertEqual(self.write('/proyectos/2/solicitudes-demo', payload).status_code, 409)
        for correo in ['invalido', '', None, 25]:
            self.assertEqual(self.write('/proyectos/1/solicitudes-demo', payload | {'correo_contacto': correo}).status_code, 400)
        with self.app.app_context():
            db.session.get(Proyecto, 1).estado = 'cerrado'
            db.session.commit()
        self.assertEqual(self.write('/proyectos/1/solicitudes-demo', payload).status_code, 409)

    def test_ratings_require_finalized_contract_and_participation(self):
        self.assertEqual(self.write('/contratos/1/calificaciones', {'puntaje': 5}).status_code, 409)
        self.login(3)
        self.assertEqual(self.write('/contratos/2/calificaciones', {'puntaje': 5}).status_code, 403)
        self.assertEqual(self.client.get('/comunicacion/contrato/2/calificar').status_code, 403)

    def test_rating_validation_duplicates_and_counterpart(self):
        for puntaje in [0, 6, 3.5, True, '5', None]:
            self.assertEqual(self.write('/contratos/2/calificaciones', {'puntaje': puntaje}).status_code, 400)
        self.assertEqual(self.write('/contratos/2/calificaciones', {'puntaje': 5, 'comentarios': 'x' * 2001}).status_code, 400)
        result = self.write('/contratos/2/calificaciones', {'puntaje': 4, 'id_evaluado': 3})
        self.assertEqual(result.status_code, 201)
        self.assertEqual(result.json['data']['id_evaluado'], 2)
        self.assertEqual(self.write('/contratos/2/calificaciones', {'puntaje': 5}).status_code, 409)
        self.login(2)
        self.assertEqual(self.get('/calificaciones').json['meta']['total'], 1)
        self.assertEqual(self.get('/notificaciones').json['no_leidas'], 1)
        self.assertEqual(self.write('/contratos/2/calificaciones', {'puntaje': 5}).status_code, 201)
        self.login(3)
        self.assertEqual(self.get('/calificaciones').json['data'], [])

    def test_incident_lifecycle_and_admin_services(self):
        response = self.write('/incidencias', {'tipo': 'bug', 'descripcion': 'No carga el historial'})
        self.assertEqual(response.status_code, 201)
        id = response.json['data']['id']
        self.assertEqual(self.get('/incidencias').json['meta']['total'], 1)
        self.assertEqual(self.get('/incidencias?todas=true').status_code, 403)
        self.assertEqual(self.write(f'/incidencias/{id}/resolver', {'resolucion': 'Listo'}, 'PATCH').status_code, 403)
        self.login(3)
        self.assertEqual(self.get('/incidencias').json['data'], [])
        self.assertEqual(self.get(f'/incidencias/{id}').status_code, 403)
        self.login(4)
        self.assertEqual(self.get('/incidencias?todas=true').json['meta']['total'], 1)
        notificaciones_admin = self.get('/notificaciones').json
        self.assertEqual(notificaciones_admin['no_leidas'], 1)
        self.assertEqual(notificaciones_admin['data'][0]['link'], '/incidencias')
        # El GET heredado ya no debe resolver el reporte.
        self.client.get(f'/comunicacion/incidencia/{id}/resolver')
        self.assertEqual(self.get(f'/incidencias/{id}').json['data']['estado'], 'abierta')
        self.assertEqual(self.write(f'/incidencias/{id}/resolver', {'resolucion': ' '}, 'PATCH').status_code, 400)
        response = self.write(f'/incidencias/{id}/resolver', {'resolucion': 'Corregido'}, 'PATCH')
        self.assertEqual(response.json['data']['estado'], 'resuelta')
        self.assertEqual(response.json['data']['id_admin'], 4)
        self.assertEqual(self.write(f'/incidencias/{id}/resolver', {'resolucion': 'Otra vez'}, 'PATCH').status_code, 409)
        self.login(1)
        notificaciones_cliente = self.get('/notificaciones').json
        self.assertEqual(notificaciones_cliente['no_leidas'], 1)
        self.assertEqual(notificaciones_cliente['data'][0]['link'], '/incidencias')

    def test_incident_validation_leaves_no_partial_records(self):
        for payload in [{'tipo': 'invalido', 'descripcion': 'Prueba'}, {'tipo': 'bug', 'descripcion': ' '},
                        {'tipo': 'bug', 'descripcion': 'x' * 5001}]:
            self.assertEqual(self.write('/incidencias', payload).status_code, 400)
        with self.app.app_context():
            self.assertEqual(db.session.query(Incidencia).count(), 0)
            self.assertEqual(db.session.query(Notificacion).count(), 0)


if __name__ == '__main__':
    unittest.main()
