from flask import render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.auth.models import Usuario, Perfil
from app.auth.forms import RegistroForm, LoginForm, PerfilForm
from app.extensions import db


def rol_requerido(roles):
    """Decorador que requiere que current_user tenga uno de los roles indicados."""
    from functools import wraps
    from flask import abort

    if isinstance(roles, str):
        roles = [roles]

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.tipo_usuario not in roles:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


@auth_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('catalogo.index'))
    form = RegistroForm()
    if form.validate_on_submit():
        usuario = Usuario(
            nombres=form.nombres.data,
            apellido_paterno=form.apellido_paterno.data,
            apellido_materno=form.apellido_materno.data,
            email=form.email.data,
            tipo_usuario=form.tipo_usuario.data
        )
        usuario.set_password(form.password.data)
        db.session.add(usuario)
        db.session.flush()  # obtener el id

        perfil = Perfil(id_usuario=usuario.id)
        db.session.add(perfil)
        db.session.commit()

        flash('¡Registro exitoso! Ahora inicia sesión.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('auth/registro.html', form=form)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('catalogo.index'))
    form = LoginForm()
    if form.validate_on_submit():
        usuario = db.session.execute(
            db.select(Usuario).filter_by(email=form.email.data)
        ).scalar_one_or_none()
        if usuario and usuario.check_password(form.password.data):
            login_user(usuario, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('catalogo.index'))
        flash('Email o contraseña incorrectos.', 'danger')
    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    form = PerfilForm()
    perfil = current_user.perfil or Perfil(id_usuario=current_user.id)
    if form.validate_on_submit():
        perfil.descripcion = form.descripcion.data
        perfil.habilidades = form.habilidades.data
        perfil.empresa = form.empresa.data
        perfil.stack_tecnologico = form.stack_tecnologico.data
        perfil.enlaces = form.enlaces.data
        if not current_user.perfil:
            db.session.add(perfil)
        db.session.commit()
        flash('Perfil actualizado.', 'success')
        return redirect(url_for('auth.editar_perfil'))
    elif request.method == 'GET':
        form.descripcion.data = perfil.descripcion
        form.habilidades.data = perfil.habilidades
        form.empresa.data = perfil.empresa
        form.stack_tecnologico.data = perfil.stack_tecnologico
        form.enlaces.data = perfil.enlaces
    return render_template('auth/perfil_editar.html', form=form, perfil=perfil)


@auth_bp.route('/perfil/<int:id>')
def ver_perfil(id):
    usuario = db.session.get(Usuario, id)
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('catalogo.index'))
    return render_template('auth/perfil_publico.html', usuario=usuario)
