import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.auth.models import Usuario
from app.catalogo.models import OfertaTrabajo, Postulacion, Proyecto
from app.contratos.models import Contrato
from app.contratos.plantillas import (
    NOMBRE_CODIGO_FUENTE,
    NOMBRE_DESARROLLO,
    NOMBRE_LICENCIA,
    NOMBRE_SOPORTE,
    ensure_plantillas,
    render_plantilla,
)
from app.extensions import db


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


class ContratoPdfYTiposTests(unittest.TestCase):
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
            email='cliente@pdf.test', tipo_usuario='cliente',
        )
        self.otro_cliente = Usuario(
            nombres='Cliente', apellido_paterno='Dos',
            email='otro@pdf.test', tipo_usuario='cliente',
        )
        self.dev = Usuario(
            nombres='Dev', apellido_paterno='Uno',
            email='dev@pdf.test', tipo_usuario='desarrollador',
        )
        db.session.add_all([self.cliente, self.otro_cliente, self.dev])
        db.session.commit()

        self.producto = Proyecto(
            id_usuario=self.dev.id, titulo='SaaS PDF',
            descripcion='Producto', precio=1200.0, estado='activo',
        )
        db.session.add(self.producto)
        db.session.commit()

        self.oferta = OfertaTrabajo(
            id_cliente=self.cliente.id, titulo='Encargo PDF',
            descripcion_requerimientos='Requerimientos', presupuesto=900.0,
            estado='en_progreso',
        )
        db.session.add(self.oferta)
        db.session.commit()
        db.session.add(Postulacion(
            id_oferta=self.oferta.id, id_desarrollador=self.dev.id,
            estado='aceptada', costo_propuesto=850.0,
        ))
        db.session.commit()

        self.plantillas = {
            p.nombre: p for p in ensure_plantillas()
        }

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

    def crear_contrato(self, plantilla_nombre=NOMBRE_DESARROLLO, estado='borrador'):
        plantilla = self.plantillas[plantilla_nombre]
        contrato = Contrato(
            id_cliente=self.cliente.id,
            id_desarrollador=self.dev.id,
            id_producto=self.producto.id,
            id_plantilla=plantilla.id,
            costo_acordado=1200.0,
            estado=estado,
        )
        db.session.add(contrato)
        db.session.flush()
        contrato.terminos_condiciones = render_plantilla(
            plantilla.contenido_html,
            {
                'contrato_id': contrato.id,
                'fecha': '16/11/2026',
                'cliente_nombre': self.cliente.nombre_completo,
                'cliente_email': self.cliente.email,
                'desarrollador_nombre': self.dev.nombre_completo,
                'desarrollador_email': self.dev.email,
                'objeto': self.producto.titulo,
                'costo': '1,200.00',
                'notas_html': '',
            },
            claves_html={'notas_html'},
        )
        db.session.commit()
        return contrato

    def test_existen_cuatro_tipos_de_contrato(self):
        for nombre in (
            NOMBRE_DESARROLLO,
            NOMBRE_LICENCIA,
            NOMBRE_CODIGO_FUENTE,
            NOMBRE_SOPORTE,
        ):
            self.assertIn(nombre, self.plantillas)

        respuesta = self.login(self.cliente).get(
            f'/contratos/api/opciones?id_producto={self.producto.id}'
        )
        data = respuesta.get_json()
        self.assertEqual(respuesta.status_code, 200)
        tipos = {p['tipo'] for p in data['plantillas']}
        self.assertEqual(
            tipos,
            {'desarrollo', 'licencia_software', 'compra_codigo', 'soporte_mantenimiento'},
        )
        self.assertTrue(all(p['etiqueta'] and p['descripcion'] for p in data['plantillas']))

    def test_crear_con_licencia_guarda_plantilla_correcta(self):
        respuesta = self.login(self.cliente).post('/contratos/api/crear', json={
            'id_producto': self.producto.id,
            'costo_acordado': 1200,
            'plantilla_id': self.plantillas[NOMBRE_LICENCIA].id,
            'notas': 'Licencia anual',
        })
        self.assertEqual(respuesta.status_code, 201, respuesta.get_data(as_text=True))
        data = respuesta.get_json()['contrato']
        self.assertEqual(data['plantilla']['tipo'], 'licencia_software')
        contrato = db.session.get(Contrato, data['id'])
        self.assertIn('Licencia de Uso de Software', contrato.terminos_condiciones)
        self.assertIn('licencia es no exclusiva', contrato.terminos_condiciones)

    def test_pdf_disponible_para_las_partes_en_cualquier_estado(self):
        contrato = self.crear_contrato(NOMBRE_CODIGO_FUENTE)
        for estado in ('pendiente', 'cancelado', 'finalizado', 'borrador'):
            contrato.estado = estado
            db.session.commit()
            for usuario in (self.cliente, self.dev):
                respuesta = self.login(usuario).get(
                    f'/contratos/api/{contrato.id}/pdf'
                )
                self.assertEqual(
                    respuesta.status_code, 200,
                    (estado, usuario.email, respuesta.data[:80]),
                )
                self.assertEqual(respuesta.mimetype, 'application/pdf')
                self.assertTrue(respuesta.data.startswith(b'%PDF-'))
                self.assertIn(
                    f'contrato-{contrato.id}.pdf',
                    respuesta.headers.get('Content-Disposition', ''),
                )

    def test_pdf_genera_documento_si_el_contrato_es_antiguo(self):
        plantilla = self.plantillas[NOMBRE_SOPORTE]
        contrato = Contrato(
            id_cliente=self.cliente.id,
            id_desarrollador=self.dev.id,
            id_producto=self.producto.id,
            id_plantilla=plantilla.id,
            costo_acordado=1200.0,
            estado='aceptado',
        )
        db.session.add(contrato)
        db.session.commit()
        self.assertIsNone(contrato.terminos_condiciones)

        respuesta = self.login(self.cliente).get(
            f'/contratos/api/{contrato.id}/pdf'
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.data[:80])
        self.assertTrue(respuesta.data.startswith(b'%PDF-'))
        db.session.refresh(contrato)
        self.assertIn('Soporte y Mantenimiento', contrato.terminos_condiciones)

    def test_pdf_rechaza_a_terceros(self):
        contrato = self.crear_contrato()
        respuesta = self.login(self.otro_cliente).get(
            f'/contratos/api/{contrato.id}/pdf'
        )
        self.assertEqual(respuesta.status_code, 403)

    def test_pdf_requiere_sesion(self):
        contrato = self.crear_contrato()
        respuesta = self.app.test_client().get(f'/contratos/api/{contrato.id}/pdf')
        self.assertEqual(respuesta.status_code, 401)


if __name__ == '__main__':
    unittest.main()
