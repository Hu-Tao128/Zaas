from flask import render_template, redirect, url_for, request, flash, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import auth_bp
from app.auth.models import Usuario, Perfil
from app.auth.forms import RegistroForm, PerfilForm
from app.auth.firebase_service import verify_firebase_token, is_firebase_ready, revoke_firebase_sessions
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


def find_or_create_user(firebase_data: dict) -> Usuario:
    """
    Busca un usuario por firebase_uid o email. Si no existe, lo crea.
    Retorna el usuario de la base de datos local (SQLite).
    """
    # Buscar por firebase_uid primero
    usuario = db.session.execute(
        db.select(Usuario).filter_by(firebase_uid=firebase_data['uid'])
    ).scalar_one_or_none()

    # Si no encuentra, buscar por email
    if not usuario and firebase_data.get('email'):
        usuario = db.session.execute(
            db.select(Usuario).filter_by(email=firebase_data['email'])
        ).scalar_one_or_none()

    # Si sigue sin existir, crearlo
    if not usuario:
        usuario = Usuario(
            firebase_uid=firebase_data['uid'],
            nombres=firebase_data.get('name', '').split()[0] if firebase_data.get('name') else 'Usuario',
            apellido_paterno=firebase_data.get('name', '').split()[-1] if firebase_data.get('name') else '',
            email=firebase_data['email'],
            tipo_usuario='cliente',
        )
        db.session.add(usuario)
        db.session.flush()

        perfil = Perfil(id_usuario=usuario.id)
        db.session.add(perfil)
        db.session.commit()

    # Actualizar firebase_uid si no lo tenía
    if not usuario.firebase_uid:
        usuario.firebase_uid = firebase_data['uid']
        db.session.commit()

    return usuario


@auth_bp.route('/login', methods=['GET'])
def login():
    """Muestra la página de login con Firebase."""
    if current_user.is_authenticated:
        return redirect(url_for('catalogo.index'))
    return render_template('auth/login.html', firebase_ready=is_firebase_ready())


@auth_bp.route('/auth/callback', methods=['POST'])
def auth_callback():
    """
    Endpoint que recibe el token de Firebase tras login exitoso.
    Verifica el token, busca/crea el usuario local y establece la sesión.
    """
    data = request.get_json()
    id_token = data.get('id_token')

    if not id_token:
        return jsonify({'error': 'Token no proporcionado'}), 400

    firebase_data = verify_firebase_token(id_token)
    if not firebase_data:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    usuario = find_or_create_user(firebase_data)
    login_user(usuario, remember=True)

    return jsonify({
        'redirect': url_for('catalogo.index'),
        'user': {
            'id': usuario.id,
            'email': usuario.email,
            'nombre': usuario.nombres,
        }
    })


@auth_bp.route('/registro', methods=['GET'])
def registro():
    """Muestra la página de registro con Firebase."""
    if current_user.is_authenticated:
        return redirect(url_for('catalogo.index'))
    return render_template('auth/registro.html', firebase_ready=is_firebase_ready())


@auth_bp.route('/registro/callback', methods=['POST'])
def registro_callback():
    """
    Endpoint que recibe el token de Firebase tras registro exitoso.
    Crea el usuario local vinculado al UID de Firebase.
    """
    data = request.get_json()
    id_token = data.get('id_token')
    tipo_usuario = data.get('tipo_usuario', 'cliente')

    if not id_token:
        return jsonify({'error': 'Token no proporcionado'}), 400

    firebase_data = verify_firebase_token(id_token)
    if not firebase_data:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    # Verificar que no exista ya
    existente = db.session.execute(
        db.select(Usuario).filter_by(firebase_uid=firebase_data['uid'])
    ).scalar_one_or_none()

    if existente:
        return jsonify({'error': 'Este usuario ya está registrado'}), 409

    usuario = find_or_create_user(firebase_data)
    usuario.tipo_usuario = tipo_usuario
    db.session.commit()

    login_user(usuario, remember=True)

    return jsonify({
        'redirect': url_for('catalogo.index'),
        'user': {
            'id': usuario.id,
            'email': usuario.email,
            'nombre': usuario.nombres,
        }
    })


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()

    # Revocar sesiones de Firebase también
    if current_user.firebase_uid:
        revoke_firebase_sessions(current_user.firebase_uid)

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
