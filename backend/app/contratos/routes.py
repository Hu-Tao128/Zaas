import hashlib
import html
from datetime import datetime

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.auth.models import Usuario
from app.catalogo.models import OfertaTrabajo, Proyecto
from app.contratos import contratos_bp
from app.contratos.forms import (
    AceptacionForm,
    ConfirmarForm,
    ContratoForm,
    EntregableForm,
    RevisionEntregableForm,
)
from app.contratos.models import Aceptacion, Contrato, Entregable, PlantillaContrato
from app.contratos.plantillas import (
    NOMBRE_PLANTILLA_BASE,
    ensure_default_plantilla,
    render_plantilla,
)
from app.extensions import db


# --------------------------------------------------------------------- utils

def _get_client_ip():
    """IP real del cliente, respetando el proxy (Vite / despliegues)."""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or ''


def _es_parte(contrato):
    return current_user.id in (contrato.id_cliente, contrato.id_desarrollador)


def _puede_ver_contrato(contrato):
    return _es_parte(contrato) or current_user.tipo_usuario == 'admin'


def _ya_firmo(contrato, usuario_id):
    if usuario_id == contrato.id_cliente:
        return bool(contrato.firma_cliente)
    if usuario_id == contrato.id_desarrollador:
        return bool(contrato.firma_desarrollador)
    return False


def _obtener_contrato(id):
    contrato = db.session.get(Contrato, id)
    if contrato is None:
        abort(404)
    if not _puede_ver_contrato(contrato):
        abort(403)
    return contrato


def _objeto_contrato(contrato):
    if contrato.producto:
        return f'Desarrollo del proyecto "{contrato.producto.titulo}"'
    if contrato.encargo:
        return f'Desarrollo del encargo "{contrato.encargo.titulo}"'
    return 'Servicio de desarrollo de software'


def _contexto_plantilla(contrato, notas=''):
    """Datos que se inyectan en la plantilla base del contrato."""
    notas = (notas or '').strip()
    notas_html = ''
    if notas:
        notas_html = (
            '<h3>Notas adicionales</h3><p>'
            + html.escape(notas).replace('\n', '<br>')
            + '</p>'
        )

    fecha = contrato.fecha_creacion or datetime.utcnow()
    return {
        'contrato_id': contrato.id,
        'fecha': fecha.strftime('%d/%m/%Y'),
        'cliente_nombre': contrato.cliente.nombre_completo,
        'cliente_email': contrato.cliente.email,
        'desarrollador_nombre': contrato.desarrollador.nombre_completo,
        'desarrollador_email': contrato.desarrollador.email,
        'objeto': _objeto_contrato(contrato),
        'costo': f'{contrato.costo_acordado:,.2f}',
        'notas_html': notas_html,
    }


def _asegurar_terminos(contrato):
    """Genera los términos de contratos viejos que aún no tienen plantilla."""
    if contrato.terminos_condiciones:
        return
    plantilla = ensure_default_plantilla()
    contrato.terminos_condiciones = render_plantilla(
        plantilla.contenido_html,
        _contexto_plantilla(contrato),
        claves_html={'notas_html'},
    )
    db.session.commit()


def _cargar_opciones_formulario(form):
    """Llena los selects del formulario con datos reales de la base."""
    desarrolladores = db.session.execute(
        db.select(Usuario).filter(
            Usuario.tipo_usuario == 'desarrollador',
            Usuario.id != current_user.id,
        ).order_by(Usuario.nombres, Usuario.apellido_paterno)
    ).scalars().all()

    if desarrolladores:
        form.id_desarrollador.choices = [
            (u.id, f'{u.nombre_completo} — {u.email}') for u in desarrolladores
        ]
    else:
        form.id_desarrollador.choices = [(0, 'No hay desarrolladores registrados')]

    # Productos: si ya se eligió un desarrollador, solo mostramos los suyos.
    proyecto_query = db.select(Proyecto).filter(Proyecto.estado == 'activo')
    if form.id_desarrollador.data:
        proyecto_query = proyecto_query.filter(
            Proyecto.id_usuario == form.id_desarrollador.data
        )
    proyectos = db.session.execute(
        proyecto_query.order_by(Proyecto.titulo)
    ).scalars().all()
    form.id_producto.choices = [(0, 'Sin producto relacionado')] + [
        (p.id, f'{p.titulo} — {p.autor.email}') for p in proyectos
    ]

    # Ofertas: solo las que publicó el cliente autenticado.
    ofertas = db.session.execute(
        db.select(OfertaTrabajo)
        .filter(OfertaTrabajo.id_cliente == current_user.id)
        .order_by(OfertaTrabajo.titulo)
    ).scalars().all()
    form.id_encargo.choices = [(0, 'Sin oferta relacionada')] + [
        (o.id, f'{o.titulo} — ${o.presupuesto:,.2f} MXN' if o.presupuesto else o.titulo)
        for o in ofertas
    ]

    plantillas = db.session.execute(
        db.select(PlantillaContrato).order_by(PlantillaContrato.id)
    ).scalars().all()
    if not plantillas:
        plantillas = [ensure_default_plantilla()]
    # La plantilla base v1.0 aparece primero para que sea la opción por defecto.
    plantillas = sorted(
        plantillas,
        key=lambda p: (p.nombre != NOMBRE_PLANTILLA_BASE, p.id),
    )
    form.plantilla_id.choices = [(p.id, p.nombre) for p in plantillas]


# ------------------------------------------------------------------- rutas

@contratos_bp.route('/')
@login_required
def listar_contratos():
    contratos = db.session.execute(
        db.select(Contrato).filter(
            (Contrato.id_cliente == current_user.id) |
            (Contrato.id_desarrollador == current_user.id)
        ).order_by(Contrato.fecha_creacion.desc())
    ).scalars().all()
    return render_template('contratos/listar.html', contratos=contratos)


@contratos_bp.route('/<int:id>')
@login_required
def ver_contrato(id):
    contrato = _obtener_contrato(id)
    _asegurar_terminos(contrato)
    return render_template(
        'contratos/ver.html',
        contrato=contrato,
        es_parte=_es_parte(contrato),
        ya_firmo=_ya_firmo(contrato, current_user.id),
        puede_firmar=contrato.estado in ('borrador', 'pendiente'),
        cancelar_form=ConfirmarForm(),
        revision_form=RevisionEntregableForm(),
    )


@contratos_bp.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_contrato():
    form = ContratoForm()
    _cargar_opciones_formulario(form)

    if form.validate_on_submit():
        valido = True

        desarrollador = db.session.get(Usuario, form.id_desarrollador.data)
        if not desarrollador or desarrollador.tipo_usuario != 'desarrollador':
            form.id_desarrollador.errors.append('Selecciona un desarrollador válido.')
            valido = False
        elif desarrollador.id == current_user.id:
            form.id_desarrollador.errors.append('No puedes crear un contrato contigo mismo.')
            valido = False

        producto = None
        if form.id_producto.data:
            producto = db.session.get(Proyecto, form.id_producto.data)
            if producto is None:
                form.id_producto.errors.append('El producto seleccionado no existe.')
                valido = False
            elif desarrollador and producto.id_usuario != desarrollador.id:
                form.id_producto.errors.append(
                    'El producto no pertenece al desarrollador seleccionado.'
                )
                valido = False

        encargo = None
        if form.id_encargo.data:
            encargo = db.session.get(OfertaTrabajo, form.id_encargo.data)
            if encargo is None:
                form.id_encargo.errors.append('La oferta seleccionada no existe.')
                valido = False
            elif encargo.id_cliente != current_user.id:
                form.id_encargo.errors.append('La oferta no pertenece a tu cuenta.')
                valido = False

        plantilla = db.session.get(PlantillaContrato, form.plantilla_id.data)
        if plantilla is None:
            form.plantilla_id.errors.append('La plantilla seleccionada no existe.')
            valido = False

        if valido:
            contrato = Contrato(
                id_cliente=current_user.id,
                id_desarrollador=desarrollador.id,
                id_producto=producto.id if producto else None,
                id_encargo=encargo.id if encargo else None,
                costo_acordado=form.costo_acordado.data,
                estado='borrador',
            )
            db.session.add(contrato)
            db.session.flush()

            # Guardamos una copia de los términos con los nombres ya puestos.
            # Así, si luego se edita la plantilla, este contrato no cambia.
            contrato.terminos_condiciones = render_plantilla(
                plantilla.contenido_html,
                _contexto_plantilla(contrato, form.notas.data),
                claves_html={'notas_html'},
            )
            db.session.commit()

            flash(
                'Contrato creado como borrador. Revisa la plantilla y firma para aceptarlo.',
                'success',
            )
            return redirect(url_for('contratos.ver_contrato', id=contrato.id))

    return render_template('contratos/form.html', form=form)


@contratos_bp.route('/<int:id>/aceptar', methods=['GET', 'POST'])
@login_required
def aceptar_contrato(id):
    contrato = _obtener_contrato(id)

    if not _es_parte(contrato):
        abort(403)
    if contrato.estado not in ('borrador', 'pendiente'):
        flash('Este contrato ya no se puede aceptar en su estado actual.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=id))
    if _ya_firmo(contrato, current_user.id):
        flash('Ya firmaste este contrato.', 'info')
        return redirect(url_for('contratos.ver_contrato', id=id))

    _asegurar_terminos(contrato)
    form = AceptacionForm()

    if form.validate_on_submit():
        firma_hash = hashlib.sha256(
            f'{current_user.id}:{contrato.id}:{datetime.utcnow().isoformat()}:{_get_client_ip()}'.encode()
        ).hexdigest()[:16]

        if current_user.id == contrato.id_cliente:
            contrato.firma_cliente = firma_hash
        elif current_user.id == contrato.id_desarrollador:
            contrato.firma_desarrollador = firma_hash
        else:
            abort(403)

        db.session.add(Aceptacion(
            id_contrato=contrato.id,
            id_usuario=current_user.id,
            ip=_get_client_ip(),
        ))

        contrato.estado = 'aceptado' if contrato.firmas_completas else 'pendiente'
        db.session.commit()

        if contrato.estado == 'aceptado':
            flash('Contrato aceptado por ambas partes. Ya pueden comenzar.', 'success')
        else:
            flash('Tu aceptación fue registrada. Falta la firma de la otra parte.', 'success')
        return redirect(url_for('contratos.ver_contrato', id=id))

    return render_template('contratos/aceptar.html', contrato=contrato, form=form)


@contratos_bp.route('/<int:id>/cancelar', methods=['POST'])
@login_required
def cancelar_contrato(id):
    contrato = _obtener_contrato(id)

    if not _es_parte(contrato):
        abort(403)
    if contrato.estado in ('finalizado', 'cancelado'):
        flash('Este contrato ya está cerrado.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=id))

    form = ConfirmarForm()
    if not form.validate_on_submit():
        flash('No se pudo procesar la cancelación. Intenta de nuevo.', 'danger')
        return redirect(url_for('contratos.ver_contrato', id=id))

    contrato.estado = 'cancelado'
    db.session.commit()
    flash('Contrato cancelado.', 'info')
    return redirect(url_for('contratos.ver_contrato', id=id))


@contratos_bp.route('/<int:id>/entregable/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_entregable(id):
    contrato = _obtener_contrato(id)

    if contrato.id_desarrollador != current_user.id:
        abort(403)
    if contrato.estado not in ('aceptado', 'en_progreso'):
        flash('Solo puedes subir entregables de un contrato aceptado y en progreso.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=id))

    form = EntregableForm()
    if form.validate_on_submit():
        entregable = Entregable(
            id_contrato=contrato.id,
            titulo=form.titulo.data.strip(),
            descripcion=form.descripcion.data,
            url_archivo=(form.url_archivo.data or '').strip() or None,
        )
        db.session.add(entregable)

        if contrato.estado == 'aceptado':
            contrato.estado = 'en_progreso'

        db.session.commit()
        flash('Entregable subido. El cliente debe revisarlo.', 'success')
        return redirect(url_for('contratos.ver_contrato', id=contrato.id))

    return render_template('contratos/entregable_form.html', form=form, contrato=contrato)


@contratos_bp.route('/entregable/<int:id>/revisar', methods=['POST'])
@login_required
def revisar_entregable(id):
    entregable = db.session.get(Entregable, id)
    if entregable is None:
        abort(404)

    contrato = _obtener_contrato(entregable.id_contrato)
    if contrato.id_cliente != current_user.id:
        abort(403)
    if entregable.estado != 'pendiente':
        flash('Este entregable ya fue revisado.', 'warning')
        return redirect(url_for('contratos.ver_contrato', id=contrato.id))

    form = RevisionEntregableForm()
    if not form.validate_on_submit():
        flash('No se pudo procesar la revisión. Intenta de nuevo.', 'danger')
        return redirect(url_for('contratos.ver_contrato', id=contrato.id))

    if form.aprobar.data:
        accion = 'aprobar'
    elif form.rechazar.data:
        accion = 'rechazar'
    else:
        flash('Selecciona aprobar o rechazar.', 'danger')
        return redirect(url_for('contratos.ver_contrato', id=contrato.id))

    entregable.comentario_revision = (form.comentario.data or '').strip()
    entregable.fecha_revision = datetime.utcnow()

    if accion == 'aprobar':
        entregable.estado = 'aprobado'
        pendientes = [e for e in contrato.entregables if e.estado == 'pendiente']
        aprobados = [e for e in contrato.entregables if e.estado == 'aprobado']
        if not pendientes and aprobados:
            contrato.estado = 'entregado'
        elif contrato.estado == 'aceptado':
            contrato.estado = 'en_progreso'
        flash('Entregable aprobado.', 'success')
    else:
        entregable.estado = 'rechazado'
        if contrato.estado == 'aceptado':
            contrato.estado = 'en_progreso'
        flash('Entregable rechazado. El desarrollador debe corregirlo.', 'warning')

    db.session.commit()
    return redirect(url_for('contratos.ver_contrato', id=contrato.id))
