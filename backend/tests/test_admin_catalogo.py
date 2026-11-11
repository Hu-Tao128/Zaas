"""Permisos y visibilidad del catálogo administrativo en SQLite temporal."""

import unittest

from app import create_app
from app.auth.models import Usuario
from app.catalogo.models import OfertaTrabajo, Proyecto
from app.extensions import db, login_manager
from test_auth_sync import TestConfig


class AdminCatalogoTest(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.addCleanup(setattr, login_manager, 'session_protection', login_manager.session_protection)
        login_manager.session_protection = None
        self.client = self.app.test_client()
        with self.app.app_context():
            db.session.add_all([
                Usuario(id=1, nombres='Admin', apellido_paterno='Prueba',
                        email='admin@example.com', tipo_usuario='admin'),
                Usuario(id=2, nombres='Cliente', apellido_paterno='Prueba',
                        email='cliente@example.com', tipo_usuario='cliente'),
                Proyecto(id=1, id_usuario=2, titulo='Proyecto activo', precio=0, estado='activo'),
                Proyecto(id=2, id_usuario=2, titulo='Proyecto cerrado', precio=50, estado='cerrado'),
                OfertaTrabajo(id=1, id_cliente=2, titulo='Oferta cerrada', estado='cerrado'),
                OfertaTrabajo(id=2, id_cliente=2, titulo='Oferta en curso', estado='en_progreso'),
            ])
            db.session.commit()

    def login(self, usuario_id):
        with self.client.session_transaction() as session:
            session['_user_id'] = str(usuario_id)
            session['_fresh'] = True

    def test_solo_administradores_pueden_consultar_el_listado_global(self):
        url = '/api/comunicacion/admin/catalogo'
        self.assertEqual(self.client.get(url).status_code, 401)
        self.login(2)
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_incluye_cerrados_y_conserva_totales_con_filtro_y_paginacion(self):
        self.login(1)
        url = '/api/comunicacion/admin/catalogo'
        proyectos = self.client.get(f'{url}?per_page=1').json
        self.assertEqual(proyectos['meta']['total'], 2)
        self.assertTrue(proyectos['meta']['has_next'])
        self.assertEqual(proyectos['data'][0]['titulo'], 'Proyecto cerrado')
        self.assertEqual(self.client.get(f'{url}?per_page=1&page=2').json['data'][0]['monto'], 0)

        ofertas = self.client.get(f'{url}?tipo=ofertas&estado=cerrado').json
        self.assertEqual(ofertas['meta']['total'], 1)
        self.assertEqual(ofertas['conteos']['ofertas']['total'], 2)
        self.assertEqual(ofertas['conteos']['ofertas']['estados']['en_progreso'], 1)
        self.assertEqual(ofertas['data'][0]['titulo'], 'Oferta cerrada')
        self.assertIsNone(ofertas['data'][0]['monto'])
        self.assertEqual(self.client.get(f'{url}?tipo=ofertas&estado=activo').status_code, 400)
