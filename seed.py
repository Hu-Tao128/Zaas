"""
Script para poblar la base de datos con datos de prueba.
Ejecutar: python seed.py

Nota: Con Firebase Auth, los usuarios se crean desde Firebase Console
o desde el frontend. Este script solo crea datos de prueba locales.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.extensions import db
from app.auth.models import Usuario, Perfil
from app.catalogo.models import Proyecto, OfertaTrabajo, Categoria, Tecnologia
from app.contratos.models import Contrato, PlantillaContrato
from app.comunicacion.models import Notificacion


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ── Usuarios (sin password — Firebase maneja auth) ──
        admin = Usuario(
            nombres='Admin', apellido_paterno='Zaas', email='admin@zaas.com',
            tipo_usuario='admin', firebase_uid='firebase_admin_uid'
        )
        cliente1 = Usuario(
            nombres='Carlos', apellido_paterno='Lopez', email='carlos@mail.com',
            tipo_usuario='cliente', firebase_uid='firebase_cliente1_uid'
        )
        dev1 = Usuario(
            nombres='Ana', apellido_paterno='Garcia', email='ana@mail.com',
            tipo_usuario='desarrollador', firebase_uid='firebase_dev1_uid'
        )
        dev2 = Usuario(
            nombres='Luis', apellido_paterno='Martinez', email='luis@mail.com',
            tipo_usuario='desarrollador', firebase_uid='firebase_dev2_uid'
        )

        db.session.add_all([admin, cliente1, dev1, dev2])
        db.session.flush()

        # ── Perfiles ──
        for u in [cliente1, dev1, dev2]:
            perfil = Perfil(
                id_usuario=u.id,
                descripcion=f'Perfil de {u.nombres}',
                habilidades='Python, Flask, JavaScript' if u.tipo_usuario == 'desarrollador' else 'Gestión de proyectos',
                empresa='Tech Corp' if u.tipo_usuario == 'desarrollador' else None,
                stack_tecnologico='Flask, SQLAlchemy, HTML/CSS' if u.tipo_usuario == 'desarrollador' else None,
                enlaces='https://github.com' if u.tipo_usuario == 'desarrollador' else None
            )
            db.session.add(perfil)

        # ── Categorías y Tecnologías ──
        cat_web = Categoria(nombre='Desarrollo Web')
        cat_mobile = Categoria(nombre='Aplicaciones Móviles')
        cat_data = Categoria(nombre='Data Science')
        db.session.add_all([cat_web, cat_mobile, cat_data])

        tech_python = Tecnologia(nombre='Python')
        tech_js = Tecnologia(nombre='JavaScript')
        tech_react = Tecnologia(nombre='React')
        tech_flask = Tecnologia(nombre='Flask')
        db.session.add_all([tech_python, tech_js, tech_react, tech_flask])
        db.session.flush()

        # ── Proyectos ──
        p1 = Proyecto(id_usuario=dev1.id, titulo='Sistema de Inventarios', descripcion='Aplicación web para gestión de inventarios con reportes.', precio=5000, demo_habilitada=True)
        p2 = Proyecto(id_usuario=dev1.id, titulo='API REST de Pagos', descripcion='API para procesamiento de pagos con Stripe.', precio=8000, demo_habilitada=False)
        p3 = Proyecto(id_usuario=dev2.id, titulo='Dashboard Analytics', descripcion='Panel de análisis de datos con gráficos interactivos.', precio=3500, demo_habilitada=True)
        db.session.add_all([p1, p2, p3])
        db.session.flush()

        # ── Ofertas de trabajo ──
        o1 = OfertaTrabajo(id_cliente=cliente1.id, titulo='Desarrollo de E-commerce', descripcion_requerimientos='Necesito una tienda en línea con carrito de compras y pasarela de pago.', presupuesto=15000, estado='abierto')
        o2 = OfertaTrabajo(id_cliente=cliente1.id, titulo='App de Tareas', descripcion_requerimientos='Aplicación de gestión de tareas con notificaciones.', presupuesto=5000, estado='abierto')
        db.session.add_all([o1, o2])

        # ── Plantilla de contrato ──
        plantilla = PlantillaContrato(
            nombre='Contrato Estándar',
            contenido_html='<h1>Contrato de Servicios</h1><p>Términos estándar...</p>'
        )
        db.session.add(plantilla)

        db.session.commit()

        print("✅ Base de datos poblada con datos de prueba.")
        print(f"\nUsuarios de prueba (crear en Firebase Auth con estos emails):")
        print(f"  Admin:     admin@zaas.com")
        print(f"  Cliente:   carlos@mail.com")
        print(f"  Dev 1:     ana@mail.com")
        print(f"  Dev 2:     luis@mail.com")


if __name__ == '__main__':
    seed()
