"""Agrega datos de demostración a la base principal sin borrar registros."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256

from app import create_app
from app.auth.models import Usuario, Perfil, Habilidad, PerfilHabilidad, PerfilTecnologia
from app.catalogo.models import Categoria, CategoriaProyecto, OfertaTrabajo, Proyecto, Tecnologia
from app.comunicacion.models import Incidencia, Mensaje
from app.comunicacion.services import crear_notificacion, enviar_mensaje, obtener_conversacion
from app.contratos.api import _depositar_escrow
from app.contratos.models import Aceptacion, Contrato, Entregable, PlantillaContrato
from app.contratos.plantillas import NOMBRE_PLANTILLA_BASE
from app.extensions import db
from app.auth.models import (
    Usuario, Perfil, Habilidad, PerfilHabilidad, PerfilTecnologia,
)
from app.catalogo.models import Proyecto, OfertaTrabajo, Categoria, Tecnologia
from app.contratos.plantillas import ensure_plantillas
from app.comunicacion.models import Notificacion


def obtener_o_crear(modelo, *, datos=None, **filtros):
    registro = db.session.scalars(db.select(modelo).filter_by(**filtros)).first()
    if registro is not None:
        return registro
    registro = modelo(**filtros, **(datos or {}))
    db.session.add(registro)
    db.session.flush()
    return registro


def cuenta(email, nombre, apellido, rol):
    return obtener_o_crear(
        Usuario, email=email,
        datos={'nombres': nombre, 'apellido_paterno': apellido, 'tipo_usuario': rol},
    )


def agregar_catalogo_base(cliente, ana, luis):
    web = obtener_o_crear(Categoria, nombre='Desarrollo Web')
    movil = obtener_o_crear(Categoria, nombre='Aplicaciones Móviles')
    datos = obtener_o_crear(Categoria, nombre='Data Science')
    habilidades = [obtener_o_crear(Habilidad, nombre=nombre) for nombre in ('Python', 'Flask', 'JavaScript')]
    gestion = obtener_o_crear(Habilidad, nombre='Gestión de proyectos')
    tecnologias = [obtener_o_crear(Tecnologia, nombre=nombre)
                   for nombre in ('Python', 'Flask', 'JavaScript', 'React')]

    for usuario in (cliente, ana, luis):
        if usuario.perfil is not None:
            continue
        perfil = Perfil(usuario=usuario, descripcion=f'Perfil de {usuario.nombres}')
        if usuario.tipo_usuario == 'desarrollador':
            perfil.empresa = 'Tech Corp'
            perfil.habilidades = [PerfilHabilidad(habilidad=item) for item in habilidades]
            perfil.tecnologias = [PerfilTecnologia(tecnologia=item) for item in tecnologias]
        else:
            perfil.habilidades = [PerfilHabilidad(habilidad=gestion)]
        db.session.add(perfil)

    for autor, titulo, descripcion, precio, demo, categoria in (
        (ana, 'Sistema de Inventarios', 'Gestión de inventarios con reportes.', 5000, True, web),
        (ana, 'API REST de Pagos', 'API de procesamiento de pagos.', 8000, False, web),
        (luis, 'Dashboard Analytics', 'Análisis de datos con gráficos interactivos.', 3500, True, datos),
    ):
        obtener_o_crear(
            Proyecto, id_usuario=autor.id, titulo=titulo,
            datos={'descripcion': descripcion, 'precio': precio, 'demo_habilitada': demo,
                   'categorias': [CategoriaProyecto(categoria=categoria)]},
        )
    for titulo, descripcion, presupuesto in (
        ('Desarrollo de E-commerce', 'Tienda con carrito y pasarela de pago.', 15000),
        ('App de Tareas', 'Aplicación de gestión de tareas con notificaciones.', 5000),
    ):
        obtener_o_crear(OfertaTrabajo, id_cliente=cliente.id, titulo=titulo,
                        datos={'descripcion_requerimientos': descripcion, 'presupuesto': presupuesto})
    return web, movil


def agregar_contrato(cliente, desarrollador, plantilla, publicacion, fecha, estado,
                     entregables, escrow=None, disputa=None, *, metodo_pago=None):
    es_proyecto = isinstance(publicacion, Proyecto)
    origen = {'id_producto' if es_proyecto else 'id_encargo': publicacion.id}
    existente = db.session.scalar(db.select(Contrato.id).filter_by(**origen).limit(1))
    if existente is not None:
        return

    contrato = Contrato(
        cliente=cliente, desarrollador=desarrollador, plantilla=plantilla, **origen,
        costo_acordado=publicacion.precio if es_proyecto else publicacion.presupuesto,
        estado=estado, fecha_creacion=fecha,
        terminos_condiciones='<p>Contrato de demostración de ZaaS para pruebas locales.</p>',
    )
    db.session.add(contrato)
    db.session.flush()

    firmantes = (cliente, desarrollador) if escrow else ()
    for usuario in firmantes:
        firma = sha256(f'demo:{usuario.id}:{contrato.id}'.encode()).hexdigest()[:16]
        if usuario is cliente:
            contrato.firma_cliente = firma
        else:
            contrato.firma_desarrollador = firma
        db.session.add(Aceptacion(contrato=contrato, usuario=usuario, fecha_hora=fecha))

    for titulo, estado_entrega in entregables:
        contrato.entregables.append(Entregable(
            titulo=titulo, estado=estado_entrega, fecha_subida=fecha + timedelta(days=2),
            fecha_revision=fecha + timedelta(days=3) if estado_entrega != 'pendiente' else None,
        ))

    if escrow is None:
        return
    pago = _depositar_escrow(contrato)
    if metodo_pago is not None:
        pago.metodo_pago = metodo_pago
    pago.fecha_pago = fecha + timedelta(days=1)
    pago.recibos[0].fecha_emision = pago.fecha_pago
    pago.estado_escrow = escrow
    if escrow != 'retenido':
        pago.fecha_liberacion = fecha + timedelta(days=4)
    if escrow == 'liberado':
        db.session.add(Liberacion(
            pago=pago, usuario=cliente, entregable=contrato.entregables[-1],
            monto_liberado=pago.monto, motivo='Entrega aprobada', fecha_hora=pago.fecha_liberacion,
        ))

    if disputa:
        estado_disputa, motivo, arbitro = disputa
        caso = Disputa(
            contrato=contrato, pago=pago, reportante=cliente, admin=arbitro,
            tipo='pago', estado=estado_disputa, descripcion=motivo,
            fecha_hora_publicacion=fecha + timedelta(days=3),
        )
        db.session.add(caso)
        if arbitro is not None:
            caso.resolucion = 'Se autorizó el reembolso simulado al cliente.'
            caso.fecha_hora_resolucion = pago.fecha_liberacion
            db.session.add(Arbitraje(
                disputa=caso, arbitro=arbitro, decision='reembolsar',
                notas=caso.resolucion, fecha_hora=caso.fecha_hora_resolucion,
            ))


def agregar_ejemplos(admin, cliente, desarrolladora, web, movil):
    hoy = datetime.now(timezone.utc).replace(tzinfo=None)
    plantilla = db.session.scalars(db.select(PlantillaContrato).filter_by(nombre=NOMBRE_PLANTILLA_BASE)).first()
    for titulo, descripcion, precio, estado, categoria in (
        ('Agenda de citas', 'Reservas, recordatorios y horarios para consultorios.', 4200, 'activo', web),
        ('Control de gastos', 'Registro móvil de gastos por categoría.', 3600, 'activo', movil),
        ('Portal de cursos', 'Catálogo de cursos, inscripciones y progreso.', 9500, 'cerrado', web),
    ):
        proyecto = obtener_o_crear(
            Proyecto, id_usuario=desarrolladora.id, titulo=f'[Demo] {titulo}',
            datos={'descripcion': descripcion, 'precio': precio, 'estado': estado, 'demo_habilitada': estado == 'activo',
                   'categorias': [CategoriaProyecto(categoria=categoria)]},
        )
        if titulo == 'Agenda de citas':
            agregar_contrato(cliente, desarrolladora, plantilla, proyecto, hoy - timedelta(days=8),
                             'en_progreso', [('Calendario inicial', 'aprobado'),
                                             ('Recordatorios por correo', 'pendiente')],
                             'retenido', ('abierta', 'El cliente solicitó revisar el importe del depósito.', None))
        elif titulo == 'Portal de cursos':
            agregar_contrato(cliente, desarrolladora, plantilla, proyecto, hoy - timedelta(days=18),
                             'finalizado', [('Portal publicado', 'aprobado')], 'liberado')

    for titulo, descripcion, monto, estado_oferta, estado, entregables, escrow, disputa in (
        ('Portal de soporte', 'Mesa de ayuda y seguimiento de tickets.', 12000, 'en_progreso', 'entregado',
         [('Panel de tickets', 'pendiente')], 'retenido', ('en_revision', 'Se está revisando el depósito.', None)),
        ('Exportación de reportes', 'Generación de archivos CSV para contabilidad.', 4800, 'cerrado', 'cancelado',
         [('Exportación inicial', 'rechazado')], 'reembolsado',
         ('resuelta', 'El alcance inicial no se completó.', admin)),
        ('App para entregas', 'Registro de envíos y confirmación de recepción.', 14500, 'abierto', 'borrador',
         [], None, None),
        ('Panel de ventas', 'Indicadores de ventas por sucursal.', 7300, 'abierto', None, [], None, None),
    ):
        oferta = obtener_o_crear(
            OfertaTrabajo, id_cliente=cliente.id, titulo=f'[Demo] {titulo}',
            datos={'descripcion_requerimientos': descripcion, 'presupuesto': monto, 'estado': estado_oferta},
        )
        if estado:
            agregar_contrato(cliente, desarrolladora, plantilla, oferta, hoy - timedelta(days=12),
                             estado, entregables, escrow, disputa)

        db.session.add_all([admin, cliente1, dev1, dev2])
        db.session.flush()

        # ── Catálogo de habilidades y tecnologías ──
        hab_python = Habilidad(nombre='Python')
        hab_flask = Habilidad(nombre='Flask')
        hab_js = Habilidad(nombre='JavaScript')
        hab_gestion = Habilidad(nombre='Gestión de proyectos')
        db.session.add_all([hab_python, hab_flask, hab_js, hab_gestion])

        tech_python = Tecnologia(nombre='Python')
        tech_js = Tecnologia(nombre='JavaScript')
        tech_react = Tecnologia(nombre='React')
        tech_flask = Tecnologia(nombre='Flask')
        db.session.add_all([tech_python, tech_js, tech_react, tech_flask])
        db.session.flush()

        # ── Perfiles (MR: habilidades y tecnologías normalizadas) ──
        for u in [cliente1, dev1, dev2]:
            perfil = Perfil(
                id_usuario=u.id,
                descripcion=f'Perfil de {u.nombres}',
                empresa='Tech Corp' if u.tipo_usuario == 'desarrollador' else None,
                enlaces='https://github.com' if u.tipo_usuario == 'desarrollador' else None
            )
            if u.tipo_usuario == 'desarrollador':
                perfil.habilidades.extend([
                    PerfilHabilidad(habilidad=hab_python),
                    PerfilHabilidad(habilidad=hab_flask),
                    PerfilHabilidad(habilidad=hab_js),
                ])
                perfil.tecnologias.extend([
                    PerfilTecnologia(tecnologia=tech_python),
                    PerfilTecnologia(tecnologia=tech_flask),
                    PerfilTecnologia(tecnologia=tech_react),
                ])
            else:
                perfil.habilidades.append(PerfilHabilidad(habilidad=hab_gestion))
            db.session.add(perfil)

        # ── Categorías ──
        cat_web = Categoria(nombre='Desarrollo Web')
        cat_mobile = Categoria(nombre='Aplicaciones Móviles')
        cat_data = Categoria(nombre='Data Science')
        db.session.add_all([cat_web, cat_mobile, cat_data])

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

        # ── Plantillas de contrato por tipo de operación ──
        ensure_plantillas()

    reservas = obtener_o_crear(
        OfertaTrabajo, id_cliente=mateo.id, titulo='[Demo] Reservas de salas',
        datos={'descripcion_requerimientos': 'Calendario de salas y confirmaciones por correo.', 'presupuesto': 8900},
    )
    agregar_contrato(mateo, nicolas, plantilla, reservas, hoy - timedelta(days=2), 'borrador', [])
    obtener_o_crear(
        OfertaTrabajo, id_cliente=sofia.id, titulo='[Demo] Registro de garantías',
        datos={'descripcion_requerimientos': 'Consulta de garantías y alta de solicitudes.', 'presupuesto': 6150},
    )

    agregar_incidencias(admin, hoy, (
        (sofia, 'bug', 'El calendario muestra en otro día las reservas de la tarde.', 'abierta', None),
        (nicolas, 'incumplimiento', 'La revisión del entregable sigue pendiente.', 'abierta', None),
        (mateo, 'fraude', 'Un tercero solicitó los datos de acceso de la cuenta.', 'en_proceso', None),
        (valeria, 'otro', 'El enlace de descarga expiró antes de la revisión.', 'en_proceso', None),
        (sofia, 'bug', 'La exportación omitía una columna del reporte.', 'resuelta',
         'Se confirmó que la nueva exportación incluye todas las columnas.'),
        (mateo, 'otro', 'Llegó un aviso después de cerrar el contrato.', 'cerrada',
         'Se encontró un aviso anterior al cierre y se documentó el caso.'),
    ))


def agregar_mensajes_demo():
    inicio = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=2)
    for publicacion, titulo, mensajes in (
        (Proyecto, 'Agenda de citas', (
            'Hola, Marina. ¿Podemos revisar el calendario antes de activar los recordatorios?',
            'Sí, Lucía. El calendario ya está listo. Prueba una cita de 30 minutos y otra de una hora.',
            'Probé las dos citas. El horario y la confirmación se mostraron correctamente.',
            'Gracias. Me falta ajustar el texto del recordatorio. Te aviso cuando esté listo.',
        )),
        (Proyecto, 'Gestión de membresías', (
            'Hola, Valeria. ¿La ficha de cada socio muestra la fecha de renovación?',
            'Sí, Sofía. También agregué un filtro para encontrar las renovaciones de este mes.',
            'Perfecto. Mañana reviso el filtro con tres socios de ejemplo.',
        )),
        (OfertaTrabajo, 'Portal para proveedores', (
            'Hola, Nicolás. Ya revisé el directorio. ¿Dónde puedo ver las órdenes pendientes?',
            'En la pestaña Órdenes, selecciona el estado Pendiente. La tabla mostrará el proveedor y el importe.',
            'Ya encontré la opción. ¿Podrías agregar también una columna con la fecha de entrega?',
        )),
    ):
        relacion = Contrato.producto if publicacion is Proyecto else Contrato.encargo
        contrato = db.session.scalar(db.select(Contrato).join(relacion).where(
            publicacion.titulo == f'[Demo] {titulo}').order_by(Contrato.id))
        if contrato is None:
            continue
        conversacion = obtener_conversacion(contrato, contrato.cliente)
        for indice, contenido in enumerate(mensajes):
            emisor = contrato.cliente if indice % 2 == 0 else contrato.desarrollador
            existe = db.session.scalar(db.select(Mensaje.id).filter_by(
                id_conversacion=conversacion.id, id_emisor=emisor.id, contenido=contenido).limit(1))
            if existe is not None:
                continue
            mensaje = enviar_mensaje(conversacion, emisor, contenido)
            mensaje.fecha_hora = inicio + timedelta(minutes=5 * indice)
            mensaje.leido = indice < len(mensajes) - 1


def seed(config_class=None):
    if config_class is None:
        from config import Config
        config_class = Config
    class ConfigSeed(config_class):
        FIREBASE_KEY_PATH = ''

    app = create_app(ConfigSeed)
    with app.app_context():
        try:
            admin = cuenta('admin@zaas.com', 'Admin', 'Zaas', 'admin')
            carlos = cuenta('carlos@mail.com', 'Carlos', 'Lopez', 'cliente')
            ana = cuenta('ana@mail.com', 'Ana', 'Garcia', 'desarrollador')
            luis = cuenta('luis@mail.com', 'Luis', 'Martinez', 'desarrollador')
            web, movil = agregar_catalogo_base(carlos, ana, luis)
            cliente = cuenta('cliente.demo@example.com', 'Lucía', 'Torres', 'cliente')
            desarrolladora = cuenta('dev.demo@example.com', 'Marina', 'Ruiz', 'desarrollador')
            cuenta('cliente2.demo@example.com', 'Diego', 'Hernández', 'cliente')
            cuenta('dev2.demo@example.com', 'Pablo', 'Vega', 'desarrollador')
            agregar_ejemplos(admin, cliente, desarrolladora, web, movil)
            agregar_segundo_grupo(admin, web, movil)
            agregar_mensajes_demo()
            db.session.commit()
        finally:
            db.session.remove()
            db.engine.dispose()

    print('Datos de demostración disponibles en el panel administrativo.')


if __name__ == '__main__':
    seed()
