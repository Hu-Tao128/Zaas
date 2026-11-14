import hashlib
import hmac
import os
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("PAGOS_CONFIRM_DELAY", "0")

from app import create_app
from app.extensions import db
from app.auth.models import Usuario
from app.catalogo.models import Proyecto
from app.contratos.models import Contrato, Entregable
from app.pagos.models import Arbitraje, Disputa, Liberacion, Pago, Recibo
from app.pagos import services
from app.pagos.errors import (
    ArbitrajeDuplicadoError,
    ConfirmacionInvalidaError,
    DisputaActivaError,
    IdempotenciaConflictoError,
    PagoPermisoError,
    ReembolsoError,
    TransicionEstadoDisputaInvalidaError,
    TransicionEstadoPagoInvalidaError,
)


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = None
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


def _firma(pago_id, ts, secreto="dev-webhook-secret"):
    mensaje = f"{int(ts)}:{pago_id}".encode()
    return hmac.new(secreto.encode(), mensaje, hashlib.sha256).hexdigest()


class BasePagos(unittest.TestCase):
    def setUp(self):
        os.environ["PAGOS_CONFIRM_DELAY"] = "0"
        os.environ["PAGOS_CONFIRMACION_INMEDIATA"] = "0"
        os.environ["PAGOS_EXPIRACION_MINUTOS"] = "15"
        os.environ.pop("PAGOS_WEBHOOK_SECRET", None)
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)
        TestConfig.SQLALCHEMY_DATABASE_URI = "sqlite:///" + self.db_path
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.cliente = Usuario(nombres="C", apellido_paterno="T", email="c@t.com", tipo_usuario="cliente")
        self.dev = Usuario(nombres="D", apellido_paterno="T", email="d@t.com", tipo_usuario="desarrollador")
        self.admin = Usuario(nombres="A", apellido_paterno="T", email="a@t.com", tipo_usuario="admin")
        self.otro = Usuario(nombres="O", apellido_paterno="T", email="o@t.com", tipo_usuario="cliente")
        db.session.add_all([self.cliente, self.dev, self.admin, self.otro])
        db.session.commit()
        self.proyecto = Proyecto(id_usuario=self.dev.id, titulo="P", descripcion="desc", precio=100, demo_habilitada=False)
        db.session.add(self.proyecto)
        db.session.commit()
        self.contrato = Contrato(id_cliente=self.cliente.id, id_desarrollador=self.dev.id, id_producto=self.proyecto.id, costo_acordado=100.0, estado="aceptado")
        db.session.add(self.contrato)
        db.session.commit()
        self.entregable = Entregable(id_contrato=self.contrato.id, titulo="E", estado="aprobado")
        db.session.add(self.entregable)
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

    def pago_pendiente(self, monto=100.0, contrato=None, key="k1"):
        contrato = contrato or self.contrato
        p = services.registrar_pago(
            contrato, self.cliente, monto=monto,
            tarjeta={"numero": "4000000000003220", "vencimiento": "12/30", "cvc": "123"},
            idempotency_key=key,
        )
        db.session.commit()
        db.session.refresh(p)
        return p


class ConfirmacionTests(BasePagos):
    def test_firma_valida(self):
        p = self.pago_pendiente(key="fv")
        ts = int(time.time())
        r = self.app.test_client().post(f"/pagos/api/pagos/{p.id}/confirmar", json={"firma": _firma(p.id, ts), "timestamp": ts})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        db.session.refresh(p)
        self.assertEqual(p.estado_escrow, "retenido")

    def test_firma_invalida(self):
        p = self.pago_pendiente(key="fi")
        ts = int(time.time())
        r = self.app.test_client().post(f"/pagos/api/pagos/{p.id}/confirmar", json={"firma": "bad", "timestamp": ts})
        self.assertEqual(r.status_code, 400)
        db.session.refresh(p)
        self.assertEqual(p.estado_escrow, "pendiente")

    def test_firma_vencida(self):
        p = self.pago_pendiente(key="fx")
        ts = int(time.time()) - 600
        r = self.app.test_client().post(f"/pagos/api/pagos/{p.id}/confirmar", json={"firma": _firma(p.id, ts), "timestamp": ts})
        self.assertEqual(r.status_code, 400)
        db.session.refresh(p)
        self.assertEqual(p.estado_escrow, "pendiente")

    def test_confirmacion_repetida(self):
        p = self.pago_pendiente(key="fr")
        ts = int(time.time())
        firma = _firma(p.id, ts)
        r1 = self.app.test_client().post(f"/pagos/api/pagos/{p.id}/confirmar", json={"firma": firma, "timestamp": ts})
        r2 = self.app.test_client().post(f"/pagos/api/pagos/{p.id}/confirmar", json={"firma": firma, "timestamp": ts})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(Recibo.query.filter_by(id_pago=p.id).count(), 1)


class ExpiracionTests(BasePagos):
    def test_expiracion(self):
        os.environ["PAGOS_EXPIRACION_MINUTOS"] = "0"
        p = self.pago_pendiente(key="ex")
        p.fecha_pago = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()
        # forzar evaluación de vigencia
        p = services.obtener_pago(p.id, self.cliente)
        self.assertIsNotNone(p)
        self.assertEqual(p.estado_escrow, "fallido")
        self.assertEqual(p.codigo_fallo, "expirado")
        # verificar que no se puede confirmar un pago ya expirado (permanece fallido/expirado)
        ts = int(time.time())
        r = self.app.test_client().post(f"/pagos/api/pagos/{p.id}/confirmar", json={"firma": _firma(p.id, ts), "timestamp": ts})
        self.assertIn(r.status_code, (200, 400, 409))
        db.session.refresh(p)
        self.assertEqual(p.estado_escrow, "fallido")
        self.assertEqual(p.codigo_fallo, "expirado")


class TransicionTests(BasePagos):
    def test_transiciones_invalidas_pago(self):
        # retenido -> pendiente invalida
        p = services.registrar_pago(self.contrato, self.cliente, monto=50.0,
            tarjeta={"numero": "4242424242424242", "vencimiento": "12/30", "cvc": "123"}, idempotency_key="tp1")
        db.session.commit()
        self.assertEqual(p.estado_escrow, "retenido")
        with self.assertRaises(TransicionEstadoPagoInvalidaError):
            services._transicionar_pago(p, "pendiente")
        # liberado final
        services.crear_liberacion(p, self.cliente, 50.0, id_entregable=self.entregable.id)
        db.session.commit()
        with self.assertRaises(TransicionEstadoPagoInvalidaError):
            services._transicionar_pago(p, "retenido")

    def test_transiciones_invalidas_disputa(self):
        p = self.pago_pendiente(key="td")
        d = services.abrir_disputa(self.contrato, self.cliente, "pago", "desc", id_pago=p.id)
        db.session.commit()
        services.atender_disputa(d, self.admin)
        db.session.commit()
        # en_revision no puede volver a abierta
        with self.assertRaises(TransicionEstadoDisputaInvalidaError):
            services._transicionar_disputa(d, "abierta")
        # resuelta final
        services.crear_arbitraje(d, self.admin, "reembolsar")
        db.session.commit()
        with self.assertRaises(TransicionEstadoDisputaInvalidaError):
            services._transicionar_disputa(d, "en_revision")


class ConcurrenciaTests(BasePagos):
    def test_dos_liberaciones_simultaneas_superan_saldo(self):
        # pago retenido de 100
        p = services.registrar_pago(self.contrato, self.cliente, monto=100.0,
            tarjeta={"numero": "4242424242424242", "vencimiento": "12/30", "cvc": "123"}, idempotency_key="conc")
        db.session.commit()
        app = self.app
        pago_id = p.id
        cliente_id = self.cliente.id
        ent_id = self.entregable.id
        ok = []
        err = []
        barrier = threading.Barrier(2)

        def worker():
            try:
                with app.app_context():
                    try:
                        pago = db.session.get(Pago, pago_id)
                        cliente = db.session.get(Usuario, cliente_id)
                        barrier.wait(timeout=5)
                        services.crear_liberacion(pago, cliente, 60.0, id_entregable=ent_id)
                        db.session.commit()
                        ok.append(1)
                    except Exception as e:
                        try:
                            db.session.rollback()
                        except Exception:
                            pass
                        err.append(e)
            except Exception as e:
                err.append(e)

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start(); t2.start()
        t1.join(10); t2.join(10)
        self.assertEqual(len(ok), 1, f"ok={len(ok)} err={[str(e) for e in err]}")
        self.assertEqual(len(err), 1)
        with self.app.app_context():
            total = db.session.query(db.func.coalesce(db.func.sum(Liberacion.monto_liberado), 0)).filter_by(id_pago=pago_id).scalar()
            self.assertLessEqual(float(total), 100.0)


class ArbitrajeTests(BasePagos):
    def test_reembolso_fallido_revierte_todo(self):
        # usar transaccion_id con FAILRF para forzar fallo de reembolso simulado
        p = services.registrar_pago(self.contrato, self.cliente, monto=50.0,
            tarjeta={"numero": "4242424242424242", "vencimiento": "12/30", "cvc": "123"}, idempotency_key="arb-fail")
        db.session.commit()
        p.transaccion_id = "TX-FAILRF-TEST"
        db.session.commit()
        d = services.abrir_disputa(self.contrato, self.cliente, "pago", "desc", id_pago=p.id)
        db.session.commit()
        with self.assertRaises(ReembolsoError):
            services.crear_arbitraje(d, self.admin, "reembolsar")
        db.session.rollback()
        db.session.refresh(d)
        db.session.refresh(p)
        self.assertEqual(d.estado, "abierta")
        self.assertIsNone(d.fecha_hora_resolucion)
        self.assertEqual(p.estado_escrow, "retenido")
        self.assertEqual(Arbitraje.query.filter_by(id_disputa=d.id).count(), 0)

    def test_dividir_partes_suman_saldo(self):
        p = services.registrar_pago(self.contrato, self.cliente, monto=100.0,
            tarjeta={"numero": "4242424242424242", "vencimiento": "12/30", "cvc": "123"}, idempotency_key="div")
        db.session.commit()
        d = services.abrir_disputa(self.contrato, self.cliente, "pago", "desc", id_pago=p.id)
        db.session.commit()
        arb = services.crear_arbitraje(d, self.admin, "dividir", porcentaje=33.33)
        db.session.commit()
        db.session.refresh(p)
        # saldo liberado al dev + reembolso al cliente deben sumar monto
        libs = Liberacion.query.filter_by(id_pago=p.id).all()
        total_lib = sum(Decimal(str(l.monto_liberado)) for l in libs)
        # en dividir, se libera parte dev y se reembolsa parte cliente (reembolso se registra en pago)
        # verificar consistencia: estado dividido y partes coherentes
        self.assertEqual(p.estado_escrow, "dividido")
        self.assertIsNotNone(p.reembolso_id)
        # total dev liberado + (monto - dev) debe ser monto
        dev_share = (Decimal("100.00") * Decimal("33.33") / Decimal("100")).quantize(Decimal("0.01"))
        client_share = Decimal("100.00") - dev_share
        self.assertEqual(total_lib, dev_share)
        # suma exacta
        self.assertEqual(dev_share + client_share, Decimal("100.00"))


class AccesoTests(BasePagos):
    def test_usuarios_ajenos_todos_endpoints(self):
        p = services.registrar_pago(self.contrato, self.cliente, monto=50.0,
            tarjeta={"numero": "4242424242424242", "vencimiento": "12/30", "cvc": "123"}, idempotency_key="acc")
        db.session.commit()
        d = services.abrir_disputa(self.contrato, self.cliente, "pago", "desc", id_pago=p.id)
        db.session.commit()
        c = self.login(self.otro)
        checks = [
            ("GET", f"/pagos/api/{p.id}", None),
            ("GET", "/pagos/api/disputas", None),
            ("GET", f"/pagos/api/disputas/{d.id}", None),
            ("GET", f"/pagos/api/contrato/{self.contrato.id}", None),
            ("POST", "/pagos/api/liberaciones", {"id_pago": p.id, "monto_liberado": 1}),
            ("POST", "/pagos/api/disputas", {"id_contrato": self.contrato.id, "tipo": "x", "descripcion": "y"}),
            ("GET", f"/pagos/api/{p.id}/recibo", None),
        ]
        for method, url, payload in checks:
            if method == "GET":
                r = c.get(url)
            else:
                r = c.post(url, json=payload or {})
            # listado de disputas devuelve 200 con resultados filtrados (vacío), sin exponer ajenas
            if method == "GET" and url == "/pagos/api/disputas":
                self.assertEqual(r.status_code, 200)
                data = r.get_json() or {}
                self.assertEqual(data.get("total", 0), 0)
                continue
            self.assertIn(r.status_code, (403, 404), f"{method} {url} -> {r.status_code} {r.get_data(as_text=True)[:200]}")


class HeredadoContratoTests(BasePagos):
    def test_endpoint_heredado_liberar(self):
        # contrato debe tener fondos retenidos y cliente puede liberar -> contrato finalizado
        p = services.registrar_pago(self.contrato, self.cliente, monto=100.0,
            tarjeta={"numero": "4242424242424242", "vencimiento": "12/30", "cvc": "123"}, idempotency_key="her")
        db.session.commit()
        c = self.login(self.cliente)
        r = c.post(f"/contratos/api/{self.contrato.id}/liberar", json={})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        data = r.get_json()
        self.assertTrue(data.get("ok"))
        db.session.refresh(self.contrato)
        db.session.refresh(p)
        self.assertEqual(self.contrato.estado, "finalizado")
        self.assertEqual(p.estado_escrow, "liberado")


class DatosTarjetaTests(BasePagos):
    def test_sin_datos_tarjeta_en_respuestas_y_logs(self):
        buf = StringIO()
        import logging
        handler = logging.StreamHandler(buf)
        handler.setLevel(logging.DEBUG)
        root = logging.getLogger()
        root.addHandler(handler)
        try:
            c = self.login(self.cliente)
            r = c.post("/pagos/api/crear", json={
                "id_contrato": self.contrato.id,
                "monto": 50,
                "metodo_pago": "tarjeta",
                "idempotency_key": "notarjeta",
                "tarjeta": {"numero": "4242424242424242", "vencimiento": "12/30", "cvc": "123"}
            })
            self.assertIn(r.status_code, (200, 201), r.get_data(as_text=True))
            body = r.get_data(as_text=True)
            self.assertNotIn("4242424242424242", body)
            self.assertNotIn("4242", body.replace(" ", ""))  # ultimos4 no expuesto
            self.assertNotIn('"cvc"', body.lower())
            self.assertNotIn('"cvc": "123"', body)
            self.assertNotIn("marca_tarjeta", body)
            self.assertNotIn("ultimos4", body)
            logs = buf.getvalue()
            self.assertNotIn("4242424242424242", logs)
        finally:
            root.removeHandler(handler)


class IdempotenciaComportamientoTests(BasePagos):
    def test_misma_clave_mismo_usuario_mismos_datos(self):
        p1 = services.registrar_pago(self.contrato, self.cliente, monto=50.0,
            tarjeta={"numero": "4242424242424242", "vencimiento": "12/30", "cvc": "123"}, idempotency_key="idem1")
        db.session.commit()
        p2 = services.registrar_pago(self.contrato, self.cliente, monto=50.0,
            tarjeta={"numero": "4242424242424242", "vencimiento": "12/30", "cvc": "123"}, idempotency_key="idem1")
        self.assertEqual(p1.id, p2.id)


if __name__ == "__main__":
    unittest.main()


class DisputaResolucionAtomicaTests(BasePagos):
    def _pago_retenido(self, key='dr'):
        p = services.registrar_pago(self.contrato, self.cliente, monto=100.0,
            tarjeta={'numero':'4242424242424242','vencimiento':'12/30','cvc':'123'}, idempotency_key=key)
        db.session.commit()
        return p

    def test_no_existe_transicion_abierta_a_resuelta(self):
        p = self._pago_retenido('dr1')
        d = services.abrir_disputa(self.contrato, self.cliente, 'pago', 'desc', id_pago=p.id)
        db.session.commit()
        with self.assertRaises(TransicionEstadoDisputaInvalidaError):
            services._transicionar_disputa(d, 'resuelta')

    def test_crear_arbitraje_desde_abierta_atiende_y_resuelve_en_misma_transaccion(self):
        p = self._pago_retenido('dr2')
        d = services.abrir_disputa(self.contrato, self.cliente, 'pago', 'desc', id_pago=p.id)
        db.session.commit()
        self.assertEqual(d.estado, 'abierta')
        self.assertIsNone(d.id_admin)
        arb = services.crear_arbitraje(d, self.admin, 'liberar')
        db.session.commit()
        db.session.refresh(d)
        self.assertIsNotNone(arb.id)
        self.assertEqual(d.estado, 'resuelta')
        self.assertEqual(d.id_admin, self.admin.id)
        self.assertIsNotNone(d.fecha_hora_resolucion)
        self.assertEqual(Arbitraje.query.filter_by(id_disputa=d.id).count(), 1)

    def test_fallo_durante_resolucion_revierte_todo_incluido_atencion(self):
        # provocar fallo de reembolso simulado (FAILRF) tras atención interna desde abierta
        p = services.registrar_pago(self.contrato, self.cliente, monto=50.0,
            tarjeta={'numero':'4242424242424242','vencimiento':'12/30','cvc':'123'}, idempotency_key='dr3')
        db.session.commit()
        p.transaccion_id = 'TX-FAILRF-ATOMICA'
        db.session.commit()
        d = services.abrir_disputa(self.contrato, self.cliente, 'pago', 'desc', id_pago=p.id)
        db.session.commit()
        with self.assertRaises(ReembolsoError):
            services.crear_arbitraje(d, self.admin, 'reembolsar')
        db.session.rollback()
        db.session.refresh(d)
        db.session.refresh(p)
        self.assertEqual(d.estado, 'abierta')
        self.assertIsNone(d.id_admin)
        self.assertIsNone(d.fecha_hora_resolucion)
        self.assertEqual(p.estado_escrow, 'retenido')
        self.assertEqual(Arbitraje.query.filter_by(id_disputa=d.id).count(), 0)


class HeredadoLiberarComportamientoTests(BasePagos):
    def test_finaliza_si_no_queda_custodia_y_liberado_alcanza_costo(self):
        # pago retenido por total del contrato
        p = services.registrar_pago(self.contrato, self.cliente, monto=100.0,
            tarjeta={'numero':'4242424242424242','vencimiento':'12/30','cvc':'123'}, idempotency_key='hl1')
        db.session.commit()
        c = self.login(self.cliente)
        r = c.post(f'/contratos/api/{self.contrato.id}/liberar', json={})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        data = r.get_json()
        self.assertTrue(data.get('ok'))
        self.assertIn('finalizado', (data.get('mensaje') or '').lower())
        db.session.refresh(self.contrato)
        db.session.refresh(p)
        self.assertEqual(self.contrato.estado, 'finalizado')
        self.assertEqual(p.estado_escrow, 'liberado')

    def test_no_finaliza_si_queda_dinero_en_custodia(self):
        # dos pagos retenidos que cubren el costo; liberar uno deja al otro en custodia
        contrato = Contrato(id_cliente=self.cliente.id, id_desarrollador=self.dev.id, id_producto=self.proyecto.id, costo_acordado=100.0, estado='aceptado')
        db.session.add(contrato)
        db.session.commit()
        p1 = services.registrar_pago(contrato, self.cliente, monto=50.0,
            tarjeta={'numero':'4242424242424242','vencimiento':'12/30','cvc':'123'}, idempotency_key='hl2a')
        db.session.commit()
        p2 = services.registrar_pago(contrato, self.cliente, monto=50.0,
            tarjeta={'numero':'4242424242424242','vencimiento':'12/30','cvc':'123'}, idempotency_key='hl2b')
        db.session.commit()
        c = self.login(self.cliente)
        r = c.post(f'/contratos/api/{contrato.id}/liberar', json={})
        self.assertEqual(r.status_code, 200, r.get_data(as_text=True))
        data = r.get_json()
        self.assertTrue(data.get('ok'))
        self.assertIn('no se finalizó', (data.get('mensaje') or '').lower())
        db.session.refresh(contrato)
        self.assertNotEqual(contrato.estado, 'finalizado')
        # al menos un pago debe seguir retenido con custodia
        retenidos = [p for p in contrato.pagos if p.estado_escrow == 'retenido']
        self.assertTrue(len(retenidos) >= 1)
