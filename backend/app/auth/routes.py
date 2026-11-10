from flask import (
    render_template, redirect, url_for, request, flash, jsonify, session,
    make_response, current_app,
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.auth import auth_bp
from app.auth.models import Usuario, Perfil
from app.auth.forms import RegistroForm, PerfilForm
from app.auth.firebase_service import verify_firebase_token, is_firebase_ready, revoke_firebase_sessions
from app.auth.perfil_utils import sincronizar_habilidades, sincronizar_tecnologias
from app.extensions import db


def _sincronizar_supabase(firebase_data, tipo_usuario):
    """Puente best-effort Firebase -> Supabase; nunca bloquea el login local."""
    try:
        from app.auth.firebase_supabase import sync_firebase_user
        return sync_firebase_user(firebase_data, tipo_usuario=tipo_usuario)
    except Exception as error:  # noqa: BLE001
        current_app.logger.warning(
            'No se pudo sincronizar el usuario %s con Supabase: %s',
            firebase_data.get('uid'), error,
        )
        return None


def _verificar_token_firebase(id_token, datos=None):
    """Verifica un ID token de Firebase; en desarrollo local acepta tokens sin firma."""
    datos = datos or {}
    firebase_data = verify_firebase_token(id_token)
    if firebase_data or is_firebase_ready():
        return firebase_data

    import jwt
    try:
        payload = jwt.decode(id_token, options={"verify_signature": False})
        return {
            'uid': payload.get('sub', datos.get('firebase_uid', 'dev_user')),
            'email': payload.get('email', datos.get('email', 'dev@test.com')),
            'name': payload.get('name'),
        }
    except Exception:
        return None


# Manejar OPTIONS preflight para CORS
@auth_bp.route('/callback', methods=['OPTIONS'])
def handle_options():
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response, 200


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


def find_or_create_user(
    firebase_data: dict,
    tipo_usuario=None,
    datos=None,
    sync_supabase=True,
) -> Usuario:
    """
    Busca un usuario por firebase_uid o email. Si no existe, lo crea.
    Retorna el usuario de la base de datos local (SQLite).

    ``tipo_usuario``/``datos`` permiten aplicar los datos del registro.
    ``sync_supabase=False`` deja la escritura en Supabase al llamador.
    """
    datos = datos or {}
    email = firebase_data.get('email') or datos.get('email') or ''
    if not email:
        raise ValueError('El token de Firebase no contiene email.')

    usuario = db.session.execute(
        db.select(Usuario).filter_by(firebase_uid=firebase_data['uid'])
    ).scalar_one_or_none()

    if not usuario:
        usuario = db.session.execute(
            db.select(Usuario).filter_by(email=email)
        ).scalar_one_or_none()

    nombre_completo = (firebase_data.get('name') or '').strip()
    partes = nombre_completo.split()
    nombres = (datos.get('nombres') or '').strip() or (partes[0] if partes else '')
    apellido_paterno = (datos.get('apellido_paterno') or '').strip() or (
        partes[-1] if partes else ''
    )
    apellido_materno = (datos.get('apellido_materno') or '').strip()

    if not usuario:
        try:
            usuario = Usuario(
                firebase_uid=firebase_data['uid'],
                nombres=nombres or 'Usuario',
                apellido_paterno=apellido_paterno,
                apellido_materno=apellido_materno,
                email=email,
                tipo_usuario=tipo_usuario or 'cliente',
            )
            db.session.add(usuario)
            db.session.flush()
            db.session.add(Perfil(id_usuario=usuario.id))
            db.session.commit()
        except IntegrityError:
            # Dos logins simultáneos (onAuthStateChanged + registro) pueden
            # intentar crear el mismo usuario. Gana el primero; el segundo relee.
            db.session.rollback()
            usuario = db.session.execute(
                db.select(Usuario).filter_by(firebase_uid=firebase_data['uid'])
            ).scalar_one_or_none()
            if not usuario:
                usuario = db.session.execute(
                    db.select(Usuario).filter_by(email=email)
                ).scalar_one_or_none()
            if not usuario:
                raise

    # Aplica los datos del registro tanto al usuario existente como al que
    # acaba de ganar la carrera de creación.
    if tipo_usuario:
        usuario.tipo_usuario = tipo_usuario
    # No sobrescribir nombres existentes si el token no trae nombre.
    if nombres:
        usuario.nombres = nombres
    if apellido_paterno:
        usuario.apellido_paterno = apellido_paterno
    if apellido_materno:
        usuario.apellido_materno = apellido_materno
    if not usuario.firebase_uid:
        usuario.firebase_uid = firebase_data['uid']
    if not usuario.perfil:
        db.session.add(Perfil(id_usuario=usuario.id))
    db.session.commit()

    if sync_supabase:
        _sincronizar_supabase(
            {**firebase_data, **{k: v for k, v in datos.items() if v}},
            usuario.tipo_usuario,
        )
    return usuario


@auth_bp.route('/login', methods=['GET'])
def login():
    """Muestra la página de login con Firebase."""
    if current_user.is_authenticated:
        return redirect(url_for('catalogo.index'))
    return render_template('auth/login.html', firebase_ready=is_firebase_ready())


@auth_bp.route('/firebase-login', methods=['POST', 'OPTIONS'])
def firebase_login():
    """Login único: valida Firebase y guarda usuario/perfil directo en Supabase.

    No depende de Supabase Auth ni de Third-Party Auth. Toda la escritura se
    hace desde el backend con la service_role key.
    """
    if request.method == 'OPTIONS':
        return handle_options()

    datos = request.get_json(silent=True) or {}
    id_token = datos.get('id_token')
    if not id_token:
        return jsonify({'error': 'Token no proporcionado'}), 400

    firebase_data = _verificar_token_firebase(id_token, datos)
    if not firebase_data:
        return jsonify({'error': 'Token inválido o expirado'}), 401
    if not firebase_data.get('email'):
        firebase_data['email'] = datos.get('email')
    if not firebase_data.get('email'):
        return jsonify({'error': 'El token no contiene email'}), 400

    tipo_usuario = datos.get('tipo_usuario')
    if tipo_usuario not in (None, 'cliente', 'desarrollador'):
        tipo_usuario = 'cliente'

    try:
        usuario = find_or_create_user(
            firebase_data,
            tipo_usuario=tipo_usuario,
            datos=datos,
            sync_supabase=False,
        )
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    try:
        from app.auth.firebase_supabase import sync_firebase_user
        supabase_data = {
            **firebase_data,
            **{
                clave: datos.get(clave)
                for clave in ('nombres', 'apellido_paterno', 'apellido_materno')
                if datos.get(clave)
            },
        }
        supabase_id = sync_firebase_user(supabase_data, tipo_usuario=usuario.tipo_usuario)
    except Exception as error:  # noqa: BLE001
        current_app.logger.error(
            'No se pudo guardar el usuario %s en Supabase: %s',
            firebase_data.get('uid'), error,
        )
        return jsonify({
            'error': 'No se pudo guardar el usuario en Supabase.',
            'detalle': str(error),
        }), 502

    login_user(usuario, remember=True)
    return jsonify({
        'ok': True,
        'redirect': url_for('catalogo.index'),
        'usuario': {
            'id': usuario.id,
            'firebase_uid': usuario.firebase_uid,
            'email': usuario.email,
            'nombres': usuario.nombres,
            'apellido_paterno': usuario.apellido_paterno,
            'apellido_materno': usuario.apellido_materno or '',
            'tipo_usuario': usuario.tipo_usuario,
            'supabase_id': supabase_id,
        },
    })


@auth_bp.route('/callback', methods=['POST'])
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
    
    # Modo desarrollo: si Firebase no está configurado, decodificar sin verificar
    if not firebase_data and not is_firebase_ready():
        import jwt
        try:
            payload = jwt.decode(id_token, options={"verify_signature": False})
            firebase_data = {
                'uid': payload.get('sub', 'dev_user'),
                'email': payload.get('email', 'dev@test.com'),
                'name': payload.get('name', 'Dev User'),
            }
        except Exception:
            return jsonify({'error': 'Token inválido'}), 400
    
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


@auth_bp.route('/registro/callback', methods=['OPTIONS'])
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

    # Modo desarrollo: si Firebase no está configurado, decodificar sin verificar
    if not firebase_data and not is_firebase_ready():
        import jwt
        try:
            payload = jwt.decode(id_token, options={"verify_signature": False})
            firebase_data = {
                'uid': payload.get('sub', data.get('firebase_uid', 'dev_user')),
                'email': payload.get('email', data.get('email', 'dev@test.com')),
                'name': payload.get('name', 'Dev User'),
            }
        except Exception:
            return jsonify({'error': 'Token inválido'}), 400

    if not firebase_data:
        return jsonify({'error': 'Token inválido o expirado'}), 401

    # Buscar usuario existente por firebase_uid o por email
    usuario = db.session.execute(
        db.select(Usuario).filter_by(firebase_uid=firebase_data['uid'])
    ).scalar_one_or_none()

    if not usuario and firebase_data.get('email'):
        usuario = db.session.execute(
            db.select(Usuario).filter_by(email=firebase_data['email'])
        ).scalar_one_or_none()

    if not usuario:
        nombre_default = firebase_data.get('name', '').split()[0] if firebase_data.get('name') else 'Usuario'
        apellido_default = firebase_data.get('name', '').split()[-1] if firebase_data.get('name') else 'Zaas'
        usuario = Usuario(
            firebase_uid=firebase_data['uid'],
            nombres=data.get('nombres') or nombre_default,
            apellido_paterno=data.get('apellido_paterno') or apellido_default,
            apellido_materno=data.get('apellido_materno') or '',
            email=firebase_data.get('email') or data.get('email', ''),
            tipo_usuario=tipo_usuario,
        )
        db.session.add(usuario)
        db.session.flush()

        perfil = Perfil(id_usuario=usuario.id)
        db.session.add(perfil)
    else:
        usuario.tipo_usuario = tipo_usuario
        if not usuario.firebase_uid:
            usuario.firebase_uid = firebase_data['uid']
        if data.get('nombres'):
            usuario.nombres = data.get('nombres')
        if data.get('apellido_paterno'):
            usuario.apellido_paterno = data.get('apellido_paterno')
        if data.get('apellido_materno'):
            usuario.apellido_materno = data.get('apellido_materno')
        if not usuario.perfil:
            perfil = Perfil(id_usuario=usuario.id)
            db.session.add(perfil)

    db.session.commit()
    login_user(usuario, remember=True)
    _sincronizar_supabase(firebase_data, usuario.tipo_usuario)

    return jsonify({
        'redirect': url_for('catalogo.index'),
        'user': {
            'id': usuario.id,
            'email': usuario.email,
            'nombre': usuario.nombres,
            'tipo_usuario': usuario.tipo_usuario,
        }
    })


@auth_bp.route('/logout')
@login_required
def logout():
    # Guardar el uid antes de cerrar la sesión: después de logout_user()
    # current_user pasa a ser anónimo y no tendría firebase_uid.
    firebase_uid = getattr(current_user, 'firebase_uid', None)

    logout_user()
    session.clear()

    # Revocar sesiones de Firebase también
    if firebase_uid:
        revoke_firebase_sessions(firebase_uid)

    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    form = PerfilForm()
    perfil = current_user.perfil or Perfil(id_usuario=current_user.id)
    if form.validate_on_submit():
        perfil.descripcion = form.descripcion.data
        perfil.empresa = form.empresa.data
        perfil.enlaces = form.enlaces.data
        if not current_user.perfil:
            db.session.add(perfil)
        sincronizar_habilidades(perfil, form.habilidades.data)
        sincronizar_tecnologias(perfil, form.tecnologias.data)
        db.session.commit()
        flash('Perfil actualizado.', 'success')
        return redirect(url_for('auth.editar_perfil'))
    elif request.method == 'GET':
        form.descripcion.data = perfil.descripcion
        form.habilidades.data = ', '.join(perfil.nombres_habilidades)
        form.empresa.data = perfil.empresa
        form.tecnologias.data = ', '.join(perfil.nombres_tecnologias)
        form.enlaces.data = perfil.enlaces
    return render_template('auth/perfil_editar.html', form=form, perfil=perfil)


@auth_bp.route('/perfil/<int:id>')
def ver_perfil(id):
    usuario = db.session.get(Usuario, id)
    if not usuario:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('catalogo.index'))
    return render_template('auth/perfil_publico.html', usuario=usuario)
