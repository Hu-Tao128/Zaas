import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import g

from app import create_app
from app.auth.models import Usuario
from app.catalogo.models import OfertaTrabajo, Postulacion, Proyecto
from app.comunicacion.models import Notificacion
from app.contratos.models import Contrato
from app.contratos.plantillas import ensure_default_plantilla
from app.extensions import db
from app.pagos.models import Disputa


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


class ContratoRechazoNegociacionTests(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)
        TestConfig.SQLALCHEMY_DATABASE_URI = 'sqlite:///' + self.db_path
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # El contexto de app se mantiene durante toda la prueba, por lo que
        # Flask-Login podría reutilizar el usuario cacheado entre peticiones de
        # distintos test_client. Se limpia al inicio de cada petición.
        @self.app.before_request
        def _limpiar_cache_login():
            g.pop('_login_user', None)

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
        self.otro_dev = Usuario(
            nombres='Dev', apellido_paterno='Dos',
            email='dev2@test.com', tipo_usuario='desarrollador',
        )
        db.session.add_all([self.cliente, self.otro_cliente, self.dev, self.otro_dev])
        db.session.commit()

        self.producto_fijo = Proyecto(
            id_usuario=self.dev.id, titulo='Producto fijo',
            descripcion='Producto', precio=250.0,
            precio_negociable=False, estado='activo',
        )
        self.producto_negociable = Proyecto(
            id_usuario=self.dev.id, titulo='Producto negociable',
            descripcion='Producto', precio=300.0,
            precio_negociable=True, estado='activo',
        )
        db.session.add_all([self.producto_fijo, self.producto_negociable])
        db.session.commit()

        self.oferta_negociable = OfertaTrabajo(
            id_cliente=self.cliente.id, titulo='Encargo negociable',
            descripcion_requerimientos='Requerimientos', presupuesto=400.0,
            estado='en_progreso',
        )
        db.session.add(self.oferta_negociable)
        db.session.commit()
        db.session.add(Postulacion(
            id_oferta=self.oferta_negociable.id,
            id_desarrollador=self.otro_dev.id,
            estado='aceptada', costo_propuesto=375.0,
            costo_negociable=True,
        ))
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

    # ------------------------------------------------------------- helpers

    def login(self, usuario):
        cliente = self.app.test_client()
        with cliente.session_transaction() as sesion:
            sesion['_user_id'] = str(usuario.id)
            sesion['_fresh'] = True
        return cliente

    def crear(self, cliente=None, **datos):
        cliente = cliente or self.login(self.cliente)
        return cliente.post('/contratos/api/crear', json={
            'costo_acordado': 250,
            'plantilla_id': self.plantilla.id,
            **datos,
        })

    def crear_contrato(self, **datos):
        respuesta = self.crear(**datos)
        self.assertEqual(respuesta.status_code, 201, respuesta.get_data(as_text=True))
        return db.session.get(Contrato, respuesta.get_json()['contrato']['id'])

    def notificaciones(self, usuario):
        return db.session.execute(
            db.select(Notificacion).filter_by(id_usuario=usuario.id)
        ).scalars().all()

    # ------------------------------------------------------ negociación

    def test_producto_no_negociable_fuerza_costo_sugerido(self):
        contrato = self.crear_contrato(
            id_producto=self.producto_fijo.id, costo_acordado=1.0,
        )
        self.assertAlmostEqual(contrato.costo_acordado, 250.0)
        self.assertFalse(contrato.monto_negociable)

    def test_producto_negociable_permite_costo_del_cliente(self):
        contrato = self.crear_contrato(
            id_producto=self.producto_negociable.id, costo_acordado=199.5,
        )
        self.assertAlmostEqual(contrato.costo_acordado, 199.5)
        self.assertTrue(contrato.monto_negociable)

    def test_opciones_expone_negociabilidad(self):
        fijo = self.login(self.cliente).get(
            f'/contratos/api/opciones?id_producto={self.producto_fijo.id}'
        ).get_json()['contexto']
        negociable = self.login(self.cliente).get(
            f'/contratos/api/opciones?id_producto={self.producto_negociable.id}'
        ).get_json()['contexto']
        self.assertFalse(fijo['negociable'])
        self.assertTrue(negociable['negociable'])

    def test_oferta_negociable_permite_costo_del_cliente(self):
        contrato = self.crear_contrato(
            id_encargo=self.oferta_negociable.id, costo_acordado=320.0,
        )
        self.assertAlmostEqual(contrato.costo_acordado, 320.0)
        self.assertTrue(contrato.monto_negociable)
        self.assertEqual(contrato.id_desarrollador, self.otro_dev.id)

    def test_contrato_duplicado_devuelve_409_no_500(self):
        primero = self.crear_contrato(id_producto=self.producto_fijo.id)
        respuesta = self.crear(id_producto=self.producto_fijo.id)
        self.assertEqual(respuesta.status_code, 409, respuesta.get_data(as_text=True))
        self.assertIn('contrato activo', respuesta.get_json()['mensaje'].lower())
        total = db.session.execute(
            db.select(Contrato).filter_by(
                id_cliente=self.cliente.id,
                id_producto=self.producto_fijo.id,
                estado='borrador',
            )
        ).scalars().all()
        self.assertEqual(len(total), 1)
        self.assertEqual(total[0].id, primero.id)

    def test_contrato_duplicado_tras_cancelar_funciona(self):
        primero = self.crear_contrato(id_producto=self.producto_fijo.id)
        cancelado = self.login(self.cliente).post(
            f'/contratos/api/{primero.id}/cancelar',
            json={'confirmar': True},
        )
        self.assertEqual(cancelado.status_code, 200, cancelado.get_data(as_text=True))
        segundo = self.crear(id_producto=self.producto_fijo.id)
        self.assertEqual(segundo.status_code, 201, segundo.get_data(as_text=True))

    def test_detalle_proyecto_informa_contrato_activo(self):
        detalle = self.login(self.cliente).get(
            f'/api/catalogo/proyectos/{self.producto_fijo.id}'
        )
        self.assertIsNone(detalle.get_json()['contrato_activo'])

        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        detalle = self.login(self.cliente).get(
            f'/api/catalogo/proyectos/{self.producto_fijo.id}'
        )
        activo = detalle.get_json()['contrato_activo']
        self.assertIsNotNone(activo)
        self.assertEqual(activo['id'], contrato.id)
        self.assertEqual(activo['estado'], 'borrador')

    # ---------------------------------------------------------- rechazo

    def test_rechazo_oculta_contrato_y_notifica_cliente(self):
        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        dev = self.login(self.dev)

        respuesta = dev.post(
            f'/contratos/api/{contrato.id}/rechazar',
            json={'motivo': 'No tengo disponibilidad para este proyecto.'},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))

        contrato = db.session.get(Contrato, contrato.id)
        self.assertTrue(contrato.rechazado)
        self.assertEqual(contrato.estado, 'cancelado')
        self.assertEqual(contrato.estado_visible, 'rechazado')
        self.assertEqual(contrato.id_rechazado_por, self.dev.id)
        self.assertIn('disponibilidad', contrato.motivo_rechazo)

        # Ya no aparece en el menú de ninguna de las partes.
        for usuario in (self.cliente, self.dev):
            lista = self.login(usuario).get('/contratos/api/')
            ids = [item['id'] for item in lista.get_json()['items']]
            self.assertNotIn(contrato.id, ids)

        # El cliente recibe la notificación con el motivo.
        avisos = self.notificaciones(self.cliente)
        self.assertTrue(
            any('rechaz' in (aviso.asunto or '').lower() for aviso in avisos),
            [aviso.asunto for aviso in avisos],
        )

        # El detalle sigue disponible para ambas partes por auditoría.
        for usuario in (self.cliente, self.dev):
            detalle = self.login(usuario).get(f'/contratos/api/{contrato.id}')
            self.assertEqual(detalle.status_code, 200)
            self.assertEqual(
                detalle.get_json()['contrato']['estado_visible'], 'rechazado'
            )

    def test_rechazo_exige_motivo(self):
        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        respuesta = self.login(self.dev).post(
            f'/contratos/api/{contrato.id}/rechazar', json={'motivo': 'corto'},
        )
        self.assertEqual(respuesta.status_code, 422)
        contrato = db.session.get(Contrato, contrato.id)
        self.assertFalse(contrato.rechazado)
        self.assertNotEqual(contrato.estado, 'cancelado')

    def test_solo_desarrollador_puede_rechazar(self):
        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        respuesta = self.login(self.cliente).post(
            f'/contratos/api/{contrato.id}/rechazar',
            json={'motivo': 'Quiero cancelar este contrato por mi cuenta.'},
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(db.session.get(Contrato, contrato.id).rechazado)

    def test_rechazo_permite_nuevo_contrato_del_mismo_producto(self):
        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        self.login(self.dev).post(
            f'/contratos/api/{contrato.id}/rechazar',
            json={'motivo': 'No puedo atender este proyecto por ahora.'},
        )
        segundo = self.crear(id_producto=self.producto_fijo.id)
        self.assertEqual(segundo.status_code, 201, segundo.get_data(as_text=True))

    # -------------------------------------------------------- oferta cliente

    def test_cliente_no_puede_ofertar_si_no_es_negociable(self):
        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        respuesta = self.login(self.cliente).post(
            f'/contratos/api/{contrato.id}/oferta',
            json={'costo_acordado': 10},
        )
        self.assertEqual(respuesta.status_code, 409)
        self.assertAlmostEqual(db.session.get(Contrato, contrato.id).costo_acordado, 250.0)

    def test_cliente_oferta_cuando_es_negociable(self):
        contrato = self.crear_contrato(id_producto=self.producto_negociable.id)
        respuesta = self.login(self.cliente).post(
            f'/contratos/api/{contrato.id}/oferta',
            json={'costo_acordado': 275.55},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))

        contrato = db.session.get(Contrato, contrato.id)
        self.assertAlmostEqual(contrato.costo_acordado, 275.55)
        self.assertIn('275.55', contrato.terminos_condiciones)

        avisos = self.notificaciones(self.dev)
        self.assertTrue(
            any('oferta' in (aviso.asunto or '').lower() for aviso in avisos),
            [aviso.asunto for aviso in avisos],
        )

    def test_cliente_no_puede_ofertar_tras_firma(self):
        contrato = self.crear_contrato(id_producto=self.producto_negociable.id)
        contrato.firma_cliente = 'firma-demo'
        db.session.commit()

        respuesta = self.login(self.cliente).post(
            f'/contratos/api/{contrato.id}/oferta',
            json={'costo_acordado': 100},
        )
        self.assertEqual(respuesta.status_code, 409)

    # ---------------------------------------------- negociación desde detalle

    def test_desarrollador_cambia_negociacion_y_notifica(self):
        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        respuesta = self.login(self.dev).post(
            f'/contratos/api/{contrato.id}/negociacion',
            json={'negociable': True},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))
        self.assertTrue(db.session.get(Contrato, contrato.id).monto_negociable)

        avisos = self.notificaciones(self.cliente)
        self.assertTrue(
            any('negociable' in (aviso.mensaje or '').lower() for aviso in avisos),
            [aviso.mensaje for aviso in avisos],
        )

    def test_cliente_no_puede_cambiar_negociacion(self):
        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        respuesta = self.login(self.cliente).post(
            f'/contratos/api/{contrato.id}/negociacion',
            json={'negociable': True},
        )
        self.assertEqual(respuesta.status_code, 403)
        self.assertFalse(db.session.get(Contrato, contrato.id).monto_negociable)

    # ---------------------------------------------------- detalle disputas

    def test_detalle_disputa_accesible_para_las_partes(self):
        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        disputa = Disputa(
            id_contrato=contrato.id,
            id_reportante=self.cliente.id,
            tipo='otro',
            descripcion='No se cumplió lo acordado en la entrega.',
            estado='abierta',
        )
        db.session.add(disputa)
        db.session.commit()

        for usuario in (self.cliente, self.dev):
            respuesta = self.login(usuario).get(f'/pagos/api/disputas/{disputa.id}')
            self.assertEqual(respuesta.status_code, 200, respuesta.get_data(as_text=True))
            self.assertEqual(respuesta.get_json()['disputa']['id'], disputa.id)

    def test_detalle_disputa_privado_para_terceros(self):
        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        disputa = Disputa(
            id_contrato=contrato.id,
            id_reportante=self.cliente.id,
            tipo='otro',
            descripcion='No se cumplió lo acordado en la entrega.',
            estado='abierta',
        )
        db.session.add(disputa)
        db.session.commit()

        respuesta = self.login(self.otro_cliente).get(
            f'/pagos/api/disputas/{disputa.id}'
        )
        self.assertEqual(respuesta.status_code, 404)

    def test_listado_disputas_incluye_las_propias(self):
        contrato = self.crear_contrato(id_producto=self.producto_fijo.id)
        disputa = Disputa(
            id_contrato=contrato.id,
            id_reportante=self.cliente.id,
            tipo='otro',
            descripcion='No se cumplió lo acordado en la entrega.',
            estado='abierta',
        )
        db.session.add(disputa)
        db.session.commit()

        for usuario in (self.cliente, self.dev):
            respuesta = self.login(usuario).get('/pagos/api/disputas')
            ids = [item['id'] for item in respuesta.get_json()['items']]
            self.assertIn(disputa.id, ids)


if __name__ == '__main__':
    unittest.main()
