import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.auth.models import Usuario
from app.catalogo.models import OfertaTrabajo, Postulacion, Proyecto
from app.comunicacion.models import Incidencia
from app.contratos.models import Contrato
from sqlalchemy import text


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        TestConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///" + self.db_path
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        # crear índices únicos parciales como en migración (para pruebas de duplicado/carrera)
        db.session.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_contrato_cliente_producto_activo "
            "ON contrato (id_cliente, id_producto) WHERE id_producto IS NOT NULL AND estado <> 'cancelado'"
        ))
        db.session.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_contrato_encargo_activo "
            "ON contrato (id_encargo) WHERE id_encargo IS NOT NULL AND estado <> 'cancelado'"
        ))
        db.session.commit()

        self.admin = Usuario(nombres="Admin", apellido_paterno="A", email="admin@t.com", tipo_usuario="admin")
        self.cliente = Usuario(nombres="Cli", apellido_paterno="Uno", email="cli@t.com", tipo_usuario="cliente")
        self.cliente2 = Usuario(nombres="Cli", apellido_paterno="Dos", email="cli2@t.com", tipo_usuario="cliente")
        self.dev = Usuario(nombres="Dev", apellido_paterno="Uno", email="dev@t.com", tipo_usuario="desarrollador")
        self.dev2 = Usuario(nombres="Dev", apellido_paterno="Dos", email="dev2@t.com", tipo_usuario="desarrollador")
        db.session.add_all([self.admin, self.cliente, self.cliente2, self.dev, self.dev2])
        db.session.commit()

        self.proyecto_activo = Proyecto(id_usuario=self.dev.id, titulo="P Activo", descripcion="d", precio=100.0, estado="activo")
        self.proyecto_inactivo = Proyecto(id_usuario=self.dev.id, titulo="P Inactivo", descripcion="d", precio=100.0, estado="cerrado")
        self.proyecto_propio = Proyecto(id_usuario=self.cliente.id, titulo="P Propio", descripcion="d", precio=50.0, estado="activo")
        db.session.add_all([self.proyecto_activo, self.proyecto_inactivo, self.proyecto_propio])
        db.session.commit()

        # oferta en progreso con postulación aceptada del dev (para contrato válido por postulación)
        self.oferta_prog = OfertaTrabajo(id_cliente=self.cliente.id, titulo="Oferta OK", descripcion_requerimientos="d", estado="en_progreso")
        db.session.add(self.oferta_prog)
        db.session.commit()
        self.post_aceptada = Postulacion(id_oferta=self.oferta_prog.id, id_desarrollador=self.dev.id, estado="aceptada", costo_propuesto=120.0)
        db.session.add(self.post_aceptada)
        db.session.commit()

        # oferta abierta con pendiente/rechazada y oferta ajena
        self.oferta_abierta = OfertaTrabajo(id_cliente=self.cliente.id, titulo="Oferta Abierta", descripcion_requerimientos="d", estado="abierto")
        self.oferta_ajena = OfertaTrabajo(id_cliente=self.cliente2.id, titulo="Oferta Ajena", descripcion_requerimientos="d", estado="en_progreso")
        db.session.add_all([self.oferta_abierta, self.oferta_ajena])
        db.session.commit()
        self.post_pendiente = Postulacion(id_oferta=self.oferta_abierta.id, id_desarrollador=self.dev.id, estado="pendiente", costo_propuesto=90.0)
        self.post_rechazada = Postulacion(id_oferta=self.oferta_abierta.id, id_desarrollador=self.dev2.id, estado="rechazada", costo_propuesto=90.0)
        self.post_ajena = Postulacion(id_oferta=self.oferta_ajena.id, id_desarrollador=self.dev.id, estado="aceptada", costo_propuesto=90.0)
        db.session.add_all([self.post_pendiente, self.post_rechazada, self.post_ajena])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.ctx.pop()
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    def login(self, user):
        c = self.app.test_client()
        with c.session_transaction() as s:
            s["_user_id"] = str(user.id)
            s["_fresh"] = True
        return c

    def crear_contrato_api(self, client, payload):
        return client.post("/contratos/api/crear", json=payload)

    def crear_incidencia_api(self, client, payload):
        return client.post("/api/comunicacion/incidencias", json=payload)


class IncidenciasTests(BaseCase):
    def contrato_propio(self):
        c = Contrato(id_cliente=self.cliente.id, id_desarrollador=self.dev.id, id_producto=self.proyecto_activo.id, costo_acordado=100.0, estado="borrador")
        db.session.add(c); db.session.commit(); return c

    def contrato_ajeno(self):
        p = Proyecto(id_usuario=self.dev.id, titulo="P Ajeno", descripcion="d", precio=80.0, estado="activo")
        db.session.add(p); db.session.commit()
        c = Contrato(id_cliente=self.cliente2.id, id_desarrollador=self.dev.id, id_producto=p.id, costo_acordado=80.0, estado="borrador")
        db.session.add(c); db.session.commit(); return c

    def assert_contrato_ajeno_error(self, resp):
        self.assertEqual(resp.status_code, 422)
        data = resp.get_json()
        self.assertEqual(data.get("codigo"), "incidencia_contrato_ajeno")
        self.assertEqual(data.get("mensaje"), "No tienes acceso al contrato seleccionado.")
        self.assertEqual((data.get("errores") or {}).get("id_contrato"), "No tienes acceso al contrato seleccionado.")

    def test_contrato_propio_ajeno_inexistente_mismo_codigo_mensaje(self):
        c = self.login(self.cliente)
        propio = self.contrato_propio()
        ok = self.crear_incidencia_api(c, {"tipo": "fraude", "descripcion": "Descripcion valida 12345", "id_contrato": propio.id})
        self.assertEqual(ok.status_code, 201, ok.get_data(as_text=True))
        ajeno = self.contrato_ajeno()
        self.assert_contrato_ajeno_error(self.crear_incidencia_api(c, {"tipo": "fraude", "descripcion": "Descripcion valida 12345", "id_contrato": ajeno.id}))
        self.assert_contrato_ajeno_error(self.crear_incidencia_api(c, {"tipo": "fraude", "descripcion": "Descripcion valida 12345", "id_contrato": 999999}))

    def test_contrato_obligatorio_fraude_e_incumplimiento(self):
        c = self.login(self.cliente)
        for tipo in ("fraude", "incumplimiento"):
            r = self.crear_incidencia_api(c, {"tipo": tipo, "descripcion": "Descripcion valida 12345"})
            self.assertEqual(r.status_code, 422, (tipo, r.get_data(as_text=True)))
            self.assertEqual(r.get_json().get("codigo"), "incidencia_contrato_requerido")

    def test_otro_con_y_sin_detalle_y_detalle_en_otro_tipo(self):
        c = self.login(self.cliente)
        # otro sin detalle
        r = self.crear_incidencia_api(c, {"tipo": "otro", "descripcion": "Descripcion valida 12345"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(r.get_json().get("codigo"), "incidencia_detalle_requerido")
        # otro con detalle ok
        r2 = self.crear_incidencia_api(c, {"tipo": "otro", "descripcion": "Descripcion valida 12345", "tipo_detalle": "Soporte"})
        self.assertEqual(r2.status_code, 201, r2.get_data(as_text=True))
        inc = Incidencia.query.get(r2.get_json()["incidencia"]["id"])
        self.assertEqual(inc.tipo_detalle, "Soporte")
        # detalle enviado en tipo distinto a otro -> se ignora/fuerza nulo
        r3 = self.crear_incidencia_api(c, {"tipo": "bug", "descripcion": "Descripcion valida 12345", "tipo_detalle": "No aplica"})
        self.assertEqual(r3.status_code, 201, r3.get_data(as_text=True))
        inc3 = Incidencia.query.get(r3.get_json()["incidencia"]["id"])
        self.assertIsNone(inc3.tipo_detalle)

    def test_tipo_vacio_o_invalido(self):
        c = self.login(self.cliente)
        for tipo in ("", "   ", "inventado", None):
            payload = {"descripcion": "Descripcion valida 12345"}
            if tipo is not None:
                payload["tipo"] = tipo
            r = self.crear_incidencia_api(c, payload)
            self.assertEqual(r.status_code, 422, (tipo, r.get_data(as_text=True)))
            self.assertEqual(r.get_json().get("codigo"), "incidencia_tipo_invalido")

    def test_descripcion_corta_y_larga(self):
        c = self.login(self.cliente)
        corta = self.crear_incidencia_api(c, {"tipo": "bug", "descripcion": "corta"})
        self.assertEqual(corta.status_code, 422)
        self.assertEqual(corta.get_json().get("codigo"), "incidencia_descripcion_invalida")
        larga = self.crear_incidencia_api(c, {"tipo": "bug", "descripcion": "x" * 1001})
        self.assertEqual(larga.status_code, 422)
        self.assertEqual(larga.get_json().get("codigo"), "incidencia_descripcion_invalida")
        ok_min = self.crear_incidencia_api(c, {"tipo": "bug", "descripcion": "1234567890"})
        self.assertEqual(ok_min.status_code, 201, ok_min.get_data(as_text=True))

    def test_incidente_antiguo_otro_sin_detalle_se_muestra_como_otro(self):
        # simula fila antigua
        inc = Incidencia(id_usuario=self.cliente.id, tipo="otro", descripcion="Descripcion antigua valida", estado="abierta", tipo_detalle=None)
        db.session.add(inc); db.session.commit()
        c = self.login(self.cliente)
        r = c.get("/api/comunicacion/incidencias")
        self.assertEqual(r.status_code, 200)
        items = r.get_json()["items"]
        it = next(x for x in items if x["id"] == inc.id)
        self.assertEqual(it.get("tipo_etiqueta"), "Otro")
        self.assertIsNone(it.get("tipo_detalle"))


if __name__ == "__main__":
    unittest.main()
