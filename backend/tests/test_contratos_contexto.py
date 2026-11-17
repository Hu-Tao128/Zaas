import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.auth.models import Usuario
from app.catalogo.models import OfertaTrabajo, Postulacion, Proyecto
from app.contratos.models import Contrato
from app.contratos.plantillas import ensure_default_plantilla
from app.extensions import db


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


class ContratoContextoTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        TestConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + self.db_path
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        self.cliente = Usuario(
            nombres='Cliente', apellido_paterno='Uno',
            email='cliente@test.com', tipo_usuario='cliente',
        )
        self.otro_cliente = Usuario(
            nombres='Cliente', apellido_paterno='Dos',
            email='cliente2@test.com', tipo_usuario='cliente',
        )
        self.dev = Usuario(
            nombres='Dev', apellido_paterno='Uno',
            email='dev@test.com', tipo_usuario='desarrollador',
        )
        self.dev2 = Usuario(
            nombres='Dev', apellido_paterno='Dos',
            email='dev2@test.com', tipo_usuario='desarrollador',
        )
        db.session.add_all([self.cliente, self.otro_cliente, self.dev, self.dev2])
        db.session.commit()

        self.producto = Proyecto(
            id_usuario=self.dev.id, titulo='SaaS Uno',
            descripcion='Producto', precio=250.0, estado='activo',
        )
        db.session.add(self.producto)
        db.session.commit()

        self.oferta = OfertaTrabajo(
            id_cliente=self.cliente.id, titulo='Encargo Uno',
            descripcion_requerimientos='Requerimientos', presupuesto=400.0,
            estado='en_progreso',
        )
        db.session.add(self.oferta)
        db.session.commit()
        db.session.add(Postulacion(
            id_oferta=self.oferta.id, id_desarrollador=self.dev2.id,
            estado='aceptada', costo_propuesto=375.0,
        ))
        db.session.commit()

        self.oferta_sin_aceptar = OfertaTrabajo(
            id_cliente=self.cliente.id, titulo='Encargo sin aceptar',
            descripcion_requerimientos='Requerimientos', presupuesto=100.0,
            estado='abierto',
        )
        db.session.add(self.oferta_sin_aceptar)
        db.session.commit()

        self.plantilla = ensure_default_plantilla()
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.ctx.pop()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def login(self, usuario):
        cliente = self.app.test_client()
        with cliente.session_transaction() as sesion:
            sesion['_user_id'] = str(usuario.id)
            sesion['_fresh'] = True
        return cliente

    def crear(self, cliente, **datos):
        return cliente.post('/contratos/api/crear', json={
            'costo_acordado': 250,
            'plantilla_id': self.plantilla.id,
            **datos,
        })

    def test_opciones_sin_contexto_no_expone_catalogos(self):
        respuesta = self.login(self.cliente).get('/contratos/api/opciones')
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))
        data = respuesta.get_json()
        self.assertIsNone(data['contexto'])
        self.assertNotIn('desarrolladores', data)
        self.assertNotIn('productos', data)
        self.assertNotIn('ofertas', data)

    def test_opciones_producto_resuelve_dueno(self):
        respuesta = self.login(self.cliente).get(
            f'/contratos/api/opciones?id_producto={self.producto.id}'
        )
        data = respuesta.get_json()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(data['contexto']['producto']['id'], self.producto.id)
        self.assertEqual(data['contexto']['desarrollador']['id'], self.dev.id)
        self.assertEqual(data['contexto']['costo_sugerido'], 250.0)

    def test_opciones_oferta_resuelve_postulacion_aceptada(self):
        respuesta = self.login(self.cliente).get(
            f'/contratos/api/opciones?id_encargo={self.oferta.id}'
        )
        data = respuesta.get_json()
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(data['contexto']['oferta']['id'], self.oferta.id)
        self.assertEqual(data['contexto']['desarrollador']['id'], self.dev2.id)
        self.assertEqual(data['contexto']['costo_sugerido'], 375.0)

    def test_crear_producto_ignora_desarrollador_enviado(self):
        respuesta = self.crear(
            self.login(self.cliente),
            id_producto=self.producto.id,
            id_desarrollador=self.dev2.id,
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.get_data(as_text=True))
        contrato = db.session.get(Contrato, respuesta.get_json()['contrato']['id'])
        self.assertEqual(contrato.id_cliente, self.cliente.id)
        self.assertEqual(contrato.id_desarrollador, self.dev.id)
        self.assertEqual(contrato.id_producto, self.producto.id)
        self.assertIsNone(contrato.id_encargo)
        self.assertEqual(contrato.id_plantilla, self.plantilla.id)
        self.assertTrue(contrato.terminos_condiciones)

    def test_crear_oferta_usa_postulacion_aceptada(self):
        respuesta = self.crear(
            self.login(self.cliente),
            id_encargo=self.oferta.id,
            id_desarrollador=self.dev.id,
        )
        self.assertEqual(respuesta.status_code, 201, respuesta.get_data(as_text=True))
        contrato = db.session.get(Contrato, respuesta.get_json()['contrato']['id'])
        self.assertEqual(contrato.id_desarrollador, self.dev2.id)
        self.assertEqual(contrato.id_encargo, self.oferta.id)
        self.assertIsNone(contrato.id_producto)

    def test_crear_oferta_sin_postulacion_aceptada_falla(self):
        respuesta = self.crear(
            self.login(self.cliente),
            id_encargo=self.oferta_sin_aceptar.id,
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(respuesta.get_json()['ok'])

    def test_crear_exige_producto_o_oferta_exacto(self):
        cliente = self.login(self.cliente)
        sin_objeto = self.crear(cliente)
        self.assertEqual(sin_objeto.status_code, 400)

        ambos = self.crear(
            cliente,
            id_producto=self.producto.id,
            id_encargo=self.oferta.id,
        )
        self.assertEqual(ambos.status_code, 400)

    def test_crear_solo_clientes(self):
        respuesta = self.crear(self.login(self.dev), id_producto=self.producto.id)
        self.assertEqual(respuesta.status_code, 403)


if __name__ == '__main__':
    unittest.main()
