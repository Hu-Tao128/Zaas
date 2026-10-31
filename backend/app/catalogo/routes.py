from flask import render_template, redirect, url_for, request, flash, abort
from sqlalchemy import update, select, func, exists, or_
from flask_login import login_required, current_user
from app.auth.routes import rol_requerido
from app.catalogo import catalogo_bp
from app.catalogo.models import (
    Proyecto, OfertaTrabajo, Postulacion, SolicitudDemo, Categoria, Tecnologia,
    CategoriaProyecto, TecnologiaProyecto,
)
from app.catalogo.forms import ProyectoForm, OfertaForm, PostulacionForm, DemoForm, ActionForm
from app.contratos.models import Contrato
from app.extensions import db

# Un contrato deja de estar "activo" solo en estos estados: son los únicos que
# contratos.cancelar_contrato trata como cerrados ("Este contrato ya está cerrado").
# Cualquier otro (borrador, pendiente, aceptado, en_progreso, entregado) se considera activo.
ESTADOS_CONTRATO_TERMINALES = ('finalizado', 'cancelado')


def _contrato_activo_expr():
    """Subconsulta correlacionada: existe un contrato activo para la oferta."""
    return exists().where(
        Contrato.id_encargo == OfertaTrabajo.id,
        or_(Contrato.estado.is_(None), Contrato.estado.notin_(ESTADOS_CONTRATO_TERMINALES)),
    )


def _tiene_contrato_activo(id_oferta):
    return db.session.execute(
        select(func.count(Contrato.id)).where(
            Contrato.id_encargo == id_oferta,
            or_(Contrato.estado.is_(None), Contrato.estado.notin_(ESTADOS_CONTRATO_TERMINALES)),
        )
    ).scalar_one() > 0


def _hay_aceptada(id_oferta):
    return db.session.execute(
        select(func.count(Postulacion.id)).where(
            Postulacion.id_oferta == id_oferta, Postulacion.estado == 'aceptada')
    ).scalar_one() > 0


def _motivo_oferta_no_abierta(estado):
    if estado == 'en_progreso':
        return 'Esta oferta está en progreso: ya tiene un desarrollador aceptado y no admite más postulaciones.'
    if estado == 'cerrado':
        return 'Esta oferta está cerrada y no acepta postulaciones.'
    return 'Esta oferta no está abierta.'


def _cargar_opciones(form):
    """Llena las opciones de categorías y tecnologías existentes en la BD."""
    for campo, modelo in ((form.categorias_ids, Categoria), (form.tecnologias_ids, Tecnologia)):
        filas = db.session.execute(db.select(modelo).order_by(modelo.nombre)).scalars().all()
        campo.choices = [(f.id, f.nombre) for f in filas]


def _sincronizar_relaciones(proyecto, categorias_ids, tecnologias_ids):
    """Deja exactamente las categorías/tecnologías indicadas (sin duplicados)."""
    cat_nuevas = set(categorias_ids or [])
    for rel in list(proyecto.categorias):
        if rel.id_categoria in cat_nuevas:
            cat_nuevas.discard(rel.id_categoria)
        else:
            proyecto.categorias.remove(rel)
    for cid in cat_nuevas:
        proyecto.categorias.append(CategoriaProyecto(id_categoria=cid))

    tec_nuevas = set(tecnologias_ids or [])
    for rel in list(proyecto.tecnologias):
        if rel.id_tecnologia in tec_nuevas:
            tec_nuevas.discard(rel.id_tecnologia)
        else:
            proyecto.tecnologias.remove(rel)
    for tid in tec_nuevas:
        proyecto.tecnologias.append(TecnologiaProyecto(id_tecnologia=tid))


@catalogo_bp.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '', type=str)
    cat_filter = request.args.get('categoria', type=int)

    query = db.select(Proyecto).filter_by(estado='activo')
    if search:
        query = query.filter(Proyecto.titulo.ilike(f'%{search}%'))
    proyectos = db.paginate(query, page=page, per_page=12)

    categorias = db.session.execute(db.select(Categoria)).scalars().all()
    return render_template('catalogo/index.html', proyectos=proyectos, categorias=categorias, search=search)


@catalogo_bp.route('/proyecto/<int:id>')
def detalle_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        flash('Proyecto no encontrado.', 'danger')
        return redirect(url_for('catalogo.index'))
    return render_template('catalogo/detalle_proyecto.html', proyecto=proyecto, csrf_form=ActionForm())


@catalogo_bp.route('/mis-productos')
@rol_requerido('desarrollador')
def mis_productos():
    proyectos = db.session.execute(
        db.select(Proyecto).filter_by(id_usuario=current_user.id).order_by(Proyecto.fecha_publicacion.desc())
    ).scalars().all()
    return render_template('catalogo/mis_productos.html', proyectos=proyectos, csrf_form=ActionForm())


@catalogo_bp.route('/proyecto/<int:id>/cerrar', methods=['POST'])
@rol_requerido('desarrollador')
def cerrar_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        abort(404)
    if proyecto.id_usuario != current_user.id:
        flash('No tienes permiso para cerrar este proyecto.', 'danger')
        return redirect(url_for('catalogo.detalle_proyecto', id=id))
    if not ActionForm().validate_on_submit():
        flash('Solicitud inválida. Inténtalo de nuevo.', 'danger')
    elif proyecto.estado == 'cerrado':
        flash('El proyecto ya estaba cerrado.', 'warning')
    else:
        proyecto.estado = 'cerrado'
        db.session.commit()
        flash('Proyecto cerrado. Ya no aparece en el catálogo público.', 'success')
    return redirect(url_for('catalogo.mis_productos'))


@catalogo_bp.route('/proyecto/nuevo', methods=['GET', 'POST'])
@rol_requerido('desarrollador')
def nuevo_proyecto():
    form = ProyectoForm()
    _cargar_opciones(form)
    if form.validate_on_submit():
        proyecto = Proyecto(
            id_usuario=current_user.id,
            titulo=form.titulo.data.strip(),
            descripcion=form.descripcion.data.strip(),
            precio=form.precio.data,
            demo_habilitada=form.demo_habilitada.data,
            estado='activo'
        )
        _sincronizar_relaciones(proyecto, form.categorias_ids.data, form.tecnologias_ids.data)
        db.session.add(proyecto)
        db.session.commit()
        flash('Proyecto publicado.', 'success')
        return redirect(url_for('catalogo.detalle_proyecto', id=proyecto.id))
    return render_template('catalogo/proyecto_form.html', form=form, edit=False)


@catalogo_bp.route('/proyecto/<int:id>/editar', methods=['GET', 'POST'])
@rol_requerido('desarrollador')
def editar_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto:
        abort(404)
    if proyecto.id_usuario != current_user.id:
        flash('No tienes permiso para editar este proyecto.', 'danger')
        return redirect(url_for('catalogo.detalle_proyecto', id=id))
    form = ProyectoForm(obj=proyecto)
    _cargar_opciones(form)
    if form.validate_on_submit():
        proyecto.titulo = form.titulo.data.strip()
        proyecto.descripcion = form.descripcion.data.strip()
        proyecto.precio = form.precio.data
        proyecto.demo_habilitada = form.demo_habilitada.data
        _sincronizar_relaciones(proyecto, form.categorias_ids.data, form.tecnologias_ids.data)
        db.session.commit()
        flash('Proyecto actualizado.', 'success')
        return redirect(url_for('catalogo.detalle_proyecto', id=proyecto.id))
    if request.method == 'GET':
        form.categorias_ids.data = [c.id_categoria for c in proyecto.categorias]
        form.tecnologias_ids.data = [t.id_tecnologia for t in proyecto.tecnologias]
    return render_template('catalogo/proyecto_form.html', form=form, edit=True, proyecto=proyecto)


@catalogo_bp.route('/ofertas')
def ver_ofertas():
    page = request.args.get('page', 1, type=int)
    ofertas = db.paginate(
        db.select(OfertaTrabajo).filter_by(estado='abierto').order_by(OfertaTrabajo.fecha_publicacion.desc()),
        page=page, per_page=12
    )
    return render_template('catalogo/ofertas.html', ofertas=ofertas)


@catalogo_bp.route('/oferta/nueva', methods=['GET', 'POST'])
@rol_requerido('cliente')
def nueva_oferta():
    form = OfertaForm()
    if form.validate_on_submit():
        oferta = OfertaTrabajo(
            id_cliente=current_user.id,
            titulo=form.titulo.data.strip(),
            descripcion_requerimientos=form.descripcion.data.strip(),
            presupuesto=form.presupuesto.data,
            fecha_entrega=form.fecha_entrega.data,
            estado='abierto'
        )
        db.session.add(oferta)
        db.session.commit()
        flash('Oferta publicada.', 'success')
        return redirect(url_for('catalogo.detalle_oferta', id=oferta.id))
    return render_template('catalogo/oferta_form.html', form=form)


@catalogo_bp.route('/oferta/<int:id>')
def detalle_oferta(id):
    oferta = db.session.get(OfertaTrabajo, id)
    if not oferta:
        flash('Oferta no encontrada.', 'danger')
        return redirect(url_for('catalogo.ver_ofertas'))
    es_dueno = current_user.is_authenticated and current_user.id == oferta.id_cliente
    mi_postulacion = None
    if current_user.is_authenticated and current_user.tipo_usuario == 'desarrollador':
        mi_postulacion = _postulacion_de(current_user.id, id)
    return render_template('catalogo/detalle_oferta.html', oferta=oferta, es_dueno=es_dueno,
                           mi_postulacion=mi_postulacion, csrf_form=ActionForm())


def _postulacion_de(id_desarrollador, id_oferta):
    return db.session.execute(
        db.select(Postulacion).filter_by(id_desarrollador=id_desarrollador, id_oferta=id_oferta)
    ).scalars().first()


@catalogo_bp.route('/mis-ofertas')
@rol_requerido('cliente')
def mis_ofertas():
    ofertas = db.session.execute(
        db.select(OfertaTrabajo).filter_by(id_cliente=current_user.id)
        .order_by(OfertaTrabajo.fecha_publicacion.desc())
    ).scalars().all()
    return render_template('catalogo/mis_ofertas.html', ofertas=ofertas, csrf_form=ActionForm())


@catalogo_bp.route('/oferta/<int:id>/cerrar', methods=['POST'])
@rol_requerido('cliente')
def cerrar_oferta(id):
    oferta = db.session.get(OfertaTrabajo, id)
    if not oferta:
        abort(404)
    if oferta.id_cliente != current_user.id:
        flash('No tienes permiso para cerrar esta oferta.', 'danger')
        return redirect(url_for('catalogo.detalle_oferta', id=id))
    if not ActionForm().validate_on_submit():
        flash('Solicitud inválida. Inténtalo de nuevo.', 'danger')
        return redirect(url_for('catalogo.mis_ofertas'))
    # Cierre atómico: una sola sentencia comprueba estado y contratos activos.
    try:
        resultado = db.session.execute(
            update(OfertaTrabajo)
            .where(
                OfertaTrabajo.id == id,
                OfertaTrabajo.id_cliente == current_user.id,
                or_(
                    OfertaTrabajo.estado == 'abierto',
                    (OfertaTrabajo.estado == 'en_progreso') & ~_contrato_activo_expr(),
                ),
            )
            .values(estado='cerrado')
            .execution_options(synchronize_session=False)
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    if resultado.rowcount == 1:
        flash('Oferta cerrada. Ya no aparece en el listado público.', 'success')
    else:
        db.session.expire_all()
        actual = db.session.get(OfertaTrabajo, id).estado
        if actual == 'cerrado':
            flash('La oferta ya estaba cerrada.', 'warning')
        elif actual == 'en_progreso' and _tiene_contrato_activo(id):
            flash('No se puede cerrar: la oferta tiene un contrato activo. '
                  'Cancela o finaliza el contrato primero.', 'warning')
        else:
            flash('No se pudo cerrar la oferta en su estado actual.', 'warning')
    return redirect(url_for('catalogo.mis_ofertas'))


@catalogo_bp.route('/oferta/<int:id>/postular', methods=['GET', 'POST'])
@rol_requerido('desarrollador')
def postular_oferta(id):
    oferta = db.session.get(OfertaTrabajo, id)
    if not oferta:
        flash('Oferta no encontrada.', 'danger')
        return redirect(url_for('catalogo.ver_ofertas'))
    existente = _postulacion_de(current_user.id, id)
    if existente:
        flash('Ya te postulaste a esta oferta.', 'warning')
        return redirect(url_for('catalogo.ver_postulacion', id=existente.id))
    if oferta.estado != 'abierto' or _hay_aceptada(id):
        flash(_motivo_oferta_no_abierta(oferta.estado if oferta.estado != 'abierto' else 'en_progreso'), 'warning')
        return redirect(url_for('catalogo.detalle_oferta', id=id))
    form = PostulacionForm()
    if form.validate_on_submit():
        id_dev = current_user.id
        try:
            # "Cerrojo" sobre la fila de la oferta: toma el bloqueo de escritura y,
            # a la vez, confirma que sigue abierta. Quien llegue después espera aquí
            # y vuelve a comprobar con los datos ya confirmados por el primero.
            bloqueo = db.session.execute(
                update(OfertaTrabajo)
                .where(OfertaTrabajo.id == id, OfertaTrabajo.estado == 'abierto')
                .values(estado=OfertaTrabajo.estado)
                .execution_options(synchronize_session=False)
            )
            if bloqueo.rowcount != 1:
                db.session.rollback()
                actual = db.session.get(OfertaTrabajo, id).estado
                flash(_motivo_oferta_no_abierta(actual), 'warning')
                return redirect(url_for('catalogo.detalle_oferta', id=id))
            if _postulacion_de(id_dev, id) or _hay_aceptada(id):
                db.session.rollback()
                flash('Ya te postulaste a esta oferta o ya no admite postulaciones.', 'warning')
                return redirect(url_for('catalogo.mis_postulaciones'))
            db.session.add(Postulacion(
                id_desarrollador=id_dev,
                id_oferta=id,
                detalles=form.detalles.data.strip(),
                costo_propuesto=form.costo_propuesto.data,
                estado='pendiente',
            ))
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        flash('Postulación enviada.', 'success')
        return redirect(url_for('catalogo.mis_postulaciones'))
    return render_template('catalogo/postular.html', form=form, oferta=oferta)


@catalogo_bp.route('/mis-postulaciones')
@rol_requerido('desarrollador')
def mis_postulaciones():
    postulaciones = db.session.execute(
        db.select(Postulacion).filter_by(id_desarrollador=current_user.id)
        .order_by(Postulacion.fecha_hora.desc())
    ).scalars().all()
    return render_template('catalogo/mis_postulaciones.html', postulaciones=postulaciones)


@catalogo_bp.route('/postulacion/<int:id>')
@login_required
def ver_postulacion(id):
    postulacion = db.session.get(Postulacion, id)
    if not postulacion:
        abort(404)
    es_cliente = postulacion.oferta.id_cliente == current_user.id
    if not es_cliente and postulacion.id_desarrollador != current_user.id:
        abort(403)
    return render_template('catalogo/detalle_postulacion.html', postulacion=postulacion,
                           es_cliente=es_cliente, csrf_form=ActionForm())


def _resolver_postulacion(id, nuevo_estado):
    postulacion = db.session.get(Postulacion, id)
    if not postulacion:
        abort(404)
    oferta = postulacion.oferta
    if oferta.id_cliente != current_user.id:
        flash('No tienes permiso para gestionar esta postulación.', 'danger')
        return redirect(url_for('catalogo.mis_ofertas'))
    destino = redirect(url_for('catalogo.ver_postulacion', id=id))
    if not ActionForm().validate_on_submit():
        flash('Solicitud inválida. Inténtalo de nuevo.', 'danger')
        return destino
    id_oferta, id_cliente = oferta.id, current_user.id
    if postulacion.estado != 'pendiente':
        flash('Esta postulación ya fue resuelta y no puede cambiarse.', 'warning')
    elif nuevo_estado == 'aceptada':
        ok, mensaje = _aceptar_postulacion(id, id_oferta, id_cliente)
        flash(mensaje, 'success' if ok else 'warning')
    else:
        ok, mensaje = _rechazar_postulacion(id)
        flash(mensaje, 'success' if ok else 'warning')
    return destino


def _aceptar_postulacion(id_postulacion, id_oferta, id_cliente):
    """Acepta una postulación de forma atómica. Devuelve (ok, mensaje).

    La oferta es el "cerrojo": el UPDATE condicional abierto -> en_progreso solo
    afecta una fila para el primero que llega; los demás ven rowcount 0 y
    cancelan sin tocar nada. Todo ocurre en una sola transacción.
    """
    try:
        r_oferta = db.session.execute(
            update(OfertaTrabajo)
            .where(OfertaTrabajo.id == id_oferta,
                   OfertaTrabajo.id_cliente == id_cliente,
                   OfertaTrabajo.estado == 'abierto')
            .values(estado='en_progreso')
            .execution_options(synchronize_session=False)
        )
        if r_oferta.rowcount != 1:
            db.session.rollback()
            actual = db.session.get(OfertaTrabajo, id_oferta).estado
            if actual == 'en_progreso':
                return False, 'Esta oferta ya está en progreso: ya tiene una postulación aceptada.'
            if actual == 'cerrado':
                return False, 'No se puede aceptar una postulación de una oferta cerrada.'
            return False, 'No se pudo aceptar la postulación en el estado actual de la oferta.'
        if _hay_aceptada(id_oferta):
            # Datos heredados: oferta abierta que ya tenía una aceptada.
            db.session.rollback()
            return False, 'Esta oferta ya tiene una postulación aceptada.'
        r_post = db.session.execute(
            update(Postulacion)
            .where(Postulacion.id == id_postulacion,
                   Postulacion.id_oferta == id_oferta,
                   Postulacion.estado == 'pendiente')
            .values(estado='aceptada')
            .execution_options(synchronize_session=False)
        )
        if r_post.rowcount != 1:
            db.session.rollback()
            return False, 'Esta postulación ya fue resuelta y no puede cambiarse.'
        db.session.execute(
            update(Postulacion)
            .where(Postulacion.id_oferta == id_oferta,
                   Postulacion.id != id_postulacion,
                   Postulacion.estado == 'pendiente')
            .values(estado='rechazada')
            .execution_options(synchronize_session=False)
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return True, 'Postulación aceptada. La oferta pasó a "en progreso" y las demás postulaciones pendientes fueron rechazadas.'


def _rechazar_postulacion(id_postulacion):
    try:
        r = db.session.execute(
            update(Postulacion)
            .where(Postulacion.id == id_postulacion, Postulacion.estado == 'pendiente')
            .values(estado='rechazada')
            .execution_options(synchronize_session=False)
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    if r.rowcount != 1:
        return False, 'Esta postulación ya fue resuelta y no puede cambiarse.'
    return True, 'Postulación rechazada.'


@catalogo_bp.route('/postulacion/<int:id>/aceptar', methods=['POST'])
@rol_requerido('cliente')
def aceptar_postulacion(id):
    return _resolver_postulacion(id, 'aceptada')


@catalogo_bp.route('/postulacion/<int:id>/rechazar', methods=['POST'])
@rol_requerido('cliente')
def rechazar_postulacion(id):
    return _resolver_postulacion(id, 'rechazada')


@catalogo_bp.route('/proyecto/<int:id>/demo', methods=['GET', 'POST'])
@login_required
def solicitar_demo(id):
    producto = db.session.get(Proyecto, id)
    if not producto:
        flash('Proyecto no encontrado.', 'danger')
        return redirect(url_for('catalogo.index'))
    form = DemoForm()
    if form.validate_on_submit():
        solicitud = SolicitudDemo(
            id_producto=id,
            id_cliente=current_user.id,
            nombre_contacto=form.nombre_contacto.data,
            correo_contacto=form.correo_contacto.data
        )
        db.session.add(solicitud)
        db.session.commit()
        flash('Solicitud de demo enviada.', 'success')
        return redirect(url_for('catalogo.detalle_proyecto', id=id))
    return render_template('catalogo/demo_form.html', form=form, producto=producto)
