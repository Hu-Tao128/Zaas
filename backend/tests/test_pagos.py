import os
import tempfile
import threading
import unittest

sys_path_inserted = False
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.auth.models import Usuario
from app.catalogo.models import Proyecto
from app.contratos.models import Contrato, Entregable
from app.pagos.models import Pago, Recibo, Liberacion, Disputa, Arbitraje
from app.pagos import services


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


class PagosTestCase(unittest.TestCase):
    def setUp(self):
        os.environ['PAGOS_CONFIRM_DELAY'] = '0'
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        TestConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + self.db_path
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        self.cliente = Usuario(nombres='Cliente', apellido_paterno='Test', email='cliente@test.com', tipo_usuario='cliente')
        self.dev = Usuario(nombres='Dev', apellido_paterno='Test', email='dev@test.com', tipo_usuario='desarrollador')
        self.admin = Usuario(nombres='Admin', apellido_paterno='Test', email='admin@test.com', tipo_usuario='admin')
        self.otro = Usuario(nombres='Otro', apellido_paterno='Test', email='otro@test.com', tipo_usuario='cliente')
        db.session.add_all([self.cliente, self.dev, self.admin, self.otro])
        db.session.commit()

        self.proyecto = Proyecto(id_usuario=self.dev.id, titulo='Proyecto', descripcion='desc', precio=100, demo_habilitada=False)
        db.session.add(self.proyecto)
        db.session.commit()

        self.contrato = Contrato(id_cliente=self.cliente.id, id_desarrollador=self.dev.id, id_producto=self.proyecto.id, costo_acordado=100.0, estado='aceptado')
        db.session.add(self.contrato)
        db.session.commit()

        self.entregable = Entregable(id_contrato=self.contrato.id, titulo='Entregable', estado='pendiente')
        db.session.add(self.entregable)
        db.session.commit()

        # pago base
        self.pago = services.registrar_pago(self.contrato, self.cliente, monto=100.0, tarjeta={'numero':'4242424242424242','vencimiento':'12/30','cvc':'123'})
        db.session.commit()

    def tearDown(self):
        self.app_context.pop()
        try:
            os.remove(self.db_path)
        except OSError:
            pass

    def _login(self, user):
        client = self.app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True
        return client

    # --- monto positivo ---
    def test_monto_no_positivo_rechazado(self):
        with self.assertRaises(ValueError):
            services.registrar_pago(self.contrato, self.cliente, monto=0)
        with self.assertRaises(ValueError):
            services.registrar_pago(self.contrato, self.cliente, monto=-5)

    # --- recibo unico por pago ---
    def test_recibo_unico_por_pago(self):
        r1 = services.generar_recibo(self.pago)
        r2 = services.generar_recibo(self.pago)
        self.assertEqual(r1.id, r2.id)
        self.assertEqual(Recibo.query.filter_by(id_pago=self.pago.id).count(), 1)

    # --- liberacion solo cliente o admin ---
    def test_liberacion_solo_cliente_o_admin(self):
        with self.assertRaises(PermissionError):
            services.crear_liberacion(self.pago, self.dev, 10.0)
        with self.assertRaises(PermissionError):
            services.crear_liberacion(self.pago, self.otro, 10.0)
        # cliente ok
        lib = services.crear_liberacion(self.pago, self.cliente, 10.0)
        db.session.commit()
        self.assertIsNotNone(lib.id)
        # admin ok
        lib2 = services.crear_liberacion(self.pago, self.admin, 10.0)
        db.session.commit()
        self.assertIsNotNone(lib2.id)

    # --- suma liberaciones no supera pago ---
    def test_suma_liberaciones_no_supera_pago(self):
        services.crear_liberacion(self.pago, self.cliente, 60.0)
        db.session.commit()
        with self.assertRaises(ValueError):
            services.crear_liberacion(self.pago, self.cliente, 50.0)

    # --- entregable del mismo contrato ---
    def test_entregable_mismo_contrato(self):
        otro_contrato = Contrato(id_cliente=self.cliente.id, id_desarrollador=self.dev.id, id_producto=self.proyecto.id, costo_acordado=50.0, estado='aceptado')
        db.session.add(otro_contrato)
        db.session.commit()
        otro_ent = Entregable(id_contrato=otro_contrato.id, titulo='Otro', estado='pendiente')
        db.session.add(otro_ent)
        db.session.commit()

        with self.assertRaises(ValueError):
            services.crear_liberacion(self.pago, self.cliente, 10.0, id_entregable=otro_ent.id)

        self.entregable.estado = 'aprobado'
        db.session.commit()
        lib = services.crear_liberacion(self.pago, self.cliente, 10.0, id_entregable=self.entregable.id)
        db.session.commit()
        self.assertEqual(lib.id_entregable, self.entregable.id)

    # --- disputa un solo origen ---
    def test_disputa_un_solo_origen(self):
        with self.assertRaises(ValueError):
            services.abrir_disputa(self.contrato, self.cliente, 'pago', 'desc', id_pago=self.pago.id, id_entregable=self.entregable.id)

    # --- arbitraje solo admin y una vez ---
    def test_arbitraje_solo_admin_y_una_vez(self):
        disputa = services.abrir_disputa(self.contrato, self.cliente, 'pago', 'desc')
        db.session.commit()

        with self.assertRaises(PermissionError):
            services.crear_arbitraje(disputa, self.cliente, 'liberar')

        arb = services.crear_arbitraje(disputa, self.admin, 'liberar')
        db.session.commit()
        self.assertIsNotNone(arb.id)

        with self.assertRaises(ValueError):
            services.crear_arbitraje(disputa, self.admin, 'reembolsar')

    # --- usuarios ajenos no acceden ---
    def test_usuarios_ajenos_no_acceden(self):
        client_otro = self._login(self.otro)
        r = client_otro.get(f'/pagos/api/{self.pago.id}')
        self.assertIn(r.status_code, (403, 404))

        # disputa de otro no visible
        r = client_otro.get('/pagos/api/disputas')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()['total'], 0)

    # --- entregable no aprobado rechaza liberacion ---
    def test_liberacion_entregable_no_aprobado(self):
        self.entregable.estado = 'pendiente'
        db.session.commit()
        with self.assertRaises(ValueError):
            services.crear_liberacion(self.pago, self.cliente, 10.0, id_entregable=self.entregable.id)

    # --- disputa abierta bloquea liberacion ---
    def test_liberacion_con_disputa_abierta(self):
        services.abrir_disputa(self.contrato, self.cliente, 'pago', 'desc', id_pago=self.pago.id)
        db.session.commit()
        with self.assertRaises(ValueError):
            services.crear_liberacion(self.pago, self.cliente, 10.0)

    # --- disputa por origen ---
    def test_disputa_por_origen(self):
        d1 = services.abrir_disputa(self.contrato, self.cliente, 'pago', 'd1', id_pago=self.pago.id)
        db.session.commit()
        with self.assertRaises(ValueError):
            services.abrir_disputa(self.contrato, self.dev, 'pago', 'd2', id_pago=self.pago.id)
        # otro origen permitido
        d2 = services.abrir_disputa(self.contrato, self.dev, 'entregable', 'd3', id_entregable=self.entregable.id)
        db.session.commit()
        self.assertNotEqual(d1.id, d2.id)

    # --- atender disputa ---
    def test_atender_disputa(self):
        disputa = services.abrir_disputa(self.contrato, self.cliente, 'pago', 'desc')
        db.session.commit()
        services.atender_disputa(disputa, self.admin)
        db.session.commit()
        self.assertEqual(disputa.estado, 'en_revision')
        self.assertEqual(disputa.id_admin, self.admin.id)

    # --- arbitraje crea liberacion en liberar ---
    def test_arbitraje_liberar_crea_liberacion(self):
        disputa = services.abrir_disputa(self.contrato, self.cliente, 'pago', 'desc', id_pago=self.pago.id)
        db.session.commit()
        antes = Liberacion.query.filter_by(id_pago=self.pago.id).count()
        services.crear_arbitraje(disputa, self.admin, 'liberar')
        db.session.commit()
        despues = Liberacion.query.filter_by(id_pago=self.pago.id).count()
        self.assertEqual(despues, antes + 1)
        self.assertEqual(self.pago.estado_escrow, 'liberado')

    # --- arbitraje dividir crea liberacion ---
    def test_arbitraje_dividir_crea_liberacion(self):
        disputa = services.abrir_disputa(self.contrato, self.cliente, 'pago', 'desc', id_pago=self.pago.id)
        db.session.commit()
        services.crear_arbitraje(disputa, self.admin, 'dividir', porcentaje=40)
        db.session.commit()
        libs = Liberacion.query.filter_by(id_pago=self.pago.id).all()
        self.assertTrue(any(l.motivo and 'dividir' in l.motivo for l in libs))
        self.assertEqual(self.pago.estado_escrow, 'dividido')

    # --- reembolsar no crea liberacion ---
    def test_arbitraje_reembolsar_sin_liberacion(self):
        # nuevo pago para no chocar con disputa previa
        contrato2 = Contrato(id_cliente=self.cliente.id, id_desarrollador=self.dev.id, id_producto=self.proyecto.id, costo_acordado=50.0, estado='aceptado')
        db.session.add(contrato2)
        db.session.commit()
        pago2 = services.registrar_pago(contrato2, self.cliente, monto=50.0, tarjeta={'numero':'4242424242424242','vencimiento':'12/30','cvc':'123'})
        db.session.commit()
        disputa = services.abrir_disputa(contrato2, self.cliente, 'pago', 'desc', id_pago=pago2.id)
        db.session.commit()
        antes = Liberacion.query.filter_by(id_pago=pago2.id).count()
        services.crear_arbitraje(disputa, self.admin, 'reembolsar')
        db.session.commit()
        despues = Liberacion.query.filter_by(id_pago=pago2.id).count()
        self.assertEqual(antes, despues)
        self.assertEqual(pago2.estado_escrow, 'reembolsado')

    # --- suma de pagos no supera costo ---
    def test_suma_pagos_no_supera_costo(self):
        with self.assertRaises(ValueError):
            services.registrar_pago(self.contrato, self.cliente, monto=1.0)

    # --- concurrencia ---
    def test_concurrencia_liberaciones(self):
        resultados = []
        errores = []

        def worker():
            try:
                # cada hilo usa su propia sesión? usamos la global con lock manual
                with self.app.app_context():
                    pago = db.session.get(Pago, self.pago.id)
                    lib = services.crear_liberacion(pago, self.cliente, 60.0)
                    db.session.commit()
                    resultados.append(lib.id)
            except Exception as e:
                errores.append(str(e))
                try:
                    db.session.rollback()
                except Exception:
                    pass

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Al menos uno debe fallar por superar el monto
        self.assertTrue(len(errores) >= 1 or len(resultados) <= 1)


if __name__ == '__main__':
    unittest.main()
