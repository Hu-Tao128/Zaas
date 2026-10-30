from flask import render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.catalogo import catalogo_bp
from app.catalogo.models import Proyecto, OfertaTrabajo, Postulacion, SolicitudDemo, Categoria, Tecnologia
from app.catalogo.forms import ProyectoForm, OfertaForm, PostulacionForm, DemoForm
from app.extensions import db


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
    return render_template('catalogo/detalle_proyecto.html', proyecto=proyecto)


@catalogo_bp.route('/proyecto/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo_proyecto():
    form = ProyectoForm()
    if form.validate_on_submit():
        proyecto = Proyecto(
            id_usuario=current_user.id,
            titulo=form.titulo.data,
            descripcion=form.descripcion.data,
            precio=form.precio.data,
            demo_habilitada=form.demo_habilitada.data
        )
        db.session.add(proyecto)
        db.session.commit()
        flash('Proyecto publicado.', 'success')
        return redirect(url_for('catalogo.detalle_proyecto', id=proyecto.id))
    return render_template('catalogo/proyecto_form.html', form=form, edit=False)


@catalogo_bp.route('/proyecto/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_proyecto(id):
    proyecto = db.session.get(Proyecto, id)
    if not proyecto or proyecto.id_usuario != current_user.id:
        flash('No tienes permiso para editar este proyecto.', 'danger')
        return redirect(url_for('catalogo.index'))
    form = ProyectoForm(obj=proyecto)
    if form.validate_on_submit():
        form.populate_obj(proyecto)
        db.session.commit()
        flash('Proyecto actualizado.', 'success')
        return redirect(url_for('catalogo.detalle_proyecto', id=proyecto.id))
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
@login_required
def nueva_oferta():
    form = OfertaForm()
    if form.validate_on_submit():
        oferta = OfertaTrabajo(
            id_cliente=current_user.id,
            titulo=form.titulo.data,
            descripcion_requerimientos=form.descripcion.data,
            presupuesto=form.presupuesto.data,
            fecha_entrega=form.fecha_entrega.data
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
    return render_template('catalogo/detalle_oferta.html', oferta=oferta)


@catalogo_bp.route('/oferta/<int:id>/postular', methods=['GET', 'POST'])
@login_required
def postular_oferta(id):
    oferta = db.session.get(OfertaTrabajo, id)
    if not oferta:
        flash('Oferta no encontrada.', 'danger')
        return redirect(url_for('catalogo.ver_ofertas'))
    form = PostulacionForm()
    if form.validate_on_submit():
        postulacion = Postulacion(
            id_desarrollador=current_user.id,
            id_oferta=id,
            detalles=form.detalles.data,
            costo_propuesto=form.costo_propuesto.data
        )
        db.session.add(postulacion)
        db.session.commit()
        flash('Postulación enviada.', 'success')
        return redirect(url_for('catalogo.detalle_oferta', id=id))
    return render_template('catalogo/postular.html', form=form, oferta=oferta)


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
