"""Puente directo Firebase Auth -> Supabase.

El backend verifica el ID token de Firebase y, con la service_role key de
Supabase, crea/actualiza ``public.usuario`` y su ``public.perfil`` usando
``firebase_uid`` como llave natural.

No se usa Supabase Third-Party Auth ni funciones/triggers nativos de Supabase:
toda la escritura ocurre desde el backend con el cliente service_role.
"""

import logging

from app.extensions import get_supabase

log = logging.getLogger(__name__)


def _partes_nombre(nombre):
    partes = (nombre or '').strip().split()
    if not partes:
        return 'Usuario', 'Firebase', None
    if len(partes) == 1:
        return partes[0], 'Firebase', None
    if len(partes) == 2:
        return partes[0], partes[1], None
    return partes[0], partes[1], ' '.join(partes[2:])


def _payload(firebase_data, tipo_usuario=None):
    nombres = (firebase_data.get('nombres') or '').strip()
    apellido_paterno = (firebase_data.get('apellido_paterno') or '').strip()
    apellido_materno = (firebase_data.get('apellido_materno') or '').strip()
    nombre_token = (
        firebase_data.get('name') or firebase_data.get('display_name') or ''
    ).strip()

    if nombre_token:
        n, a, m = _partes_nombre(nombre_token)
        nombres = nombres or n
        apellido_paterno = apellido_paterno or a
        apellido_materno = apellido_materno or (m or '')

    payload = {
        'firebase_uid': firebase_data['uid'],
        'email': firebase_data['email'],
    }
    # Solo se actualizan los nombres si hay una fuente real; así un login sin
    # displayName no borra los datos que el usuario ya tenía.
    if nombres:
        payload['nombres'] = nombres
    if apellido_paterno:
        payload['apellido_paterno'] = apellido_paterno
    if apellido_materno:
        payload['apellido_materno'] = apellido_materno
    if tipo_usuario:
        payload['tipo_usuario'] = tipo_usuario
    return payload


def _ensure_perfil(usuario_id):
    """Garantiza la relación 1:1 usuario -> perfil que exige el MR."""
    if not usuario_id:
        return None
    client = get_supabase()
    existente = (
        client.table('perfil')
        .select('id')
        .eq('id_usuario', usuario_id)
        .limit(1)
        .execute()
        .data
    )
    if existente:
        return existente[0]['id']
    try:
        respuesta = client.table('perfil').insert({'id_usuario': usuario_id}).execute()
        return respuesta.data[0]['id'] if respuesta.data else None
    except Exception:  # noqa: BLE001 - carrera de dos logins simultáneos
        existente = (
            client.table('perfil')
            .select('id')
            .eq('id_usuario', usuario_id)
            .limit(1)
            .execute()
            .data
        )
        return existente[0]['id'] if existente else None


def sync_firebase_user(firebase_data, tipo_usuario=None):
    """Crea o actualiza ``usuario`` y ``perfil`` en Supabase desde Firebase.

    Es idempotente: busca por ``firebase_uid`` y, si no existe, por ``email``
    (para no duplicar cuentas creadas antes del puente). Devuelve el id de
    Supabase o ``None`` si no hay datos suficientes.
    """
    uid = firebase_data.get('uid')
    email = firebase_data.get('email')
    if not uid or not email:
        return None

    client = get_supabase()
    payload = _payload(firebase_data, tipo_usuario=tipo_usuario)

    existentes = (
        client.table('usuario')
        .select('id')
        .eq('firebase_uid', uid)
        .limit(1)
        .execute()
        .data
    )
    if existentes:
        actualizacion = {k: v for k, v in payload.items() if k != 'firebase_uid'}
        client.table('usuario').update(actualizacion).eq(
            'id', existentes[0]['id']
        ).execute()
        usuario_id = existentes[0]['id']
        _ensure_perfil(usuario_id)
        return usuario_id

    por_email = (
        client.table('usuario')
        .select('id, firebase_uid')
        .eq('email', email)
        .limit(1)
        .execute()
        .data
    )
    if por_email:
        actualizacion = dict(payload)
        if por_email[0].get('firebase_uid'):
            # El email ya pertenece a otra cuenta de Firebase: no la robamos.
            actualizacion.pop('firebase_uid', None)
        client.table('usuario').update(actualizacion).eq(
            'id', por_email[0]['id']
        ).execute()
        usuario_id = por_email[0]['id']
        _ensure_perfil(usuario_id)
        return usuario_id

    payload.setdefault('nombres', 'Usuario')
    payload.setdefault('apellido_paterno', 'Firebase')
    payload.setdefault('tipo_usuario', 'cliente')
    respuesta = client.table('usuario').insert(payload).execute()
    usuario_id = respuesta.data[0]['id'] if respuesta.data else None
    _ensure_perfil(usuario_id)
    return usuario_id


def _iterar_usuarios_firebase():
    from firebase_admin import auth as firebase_auth

    pagina = firebase_auth.list_users()
    while pagina:
        yield from pagina.users
        pagina = pagina.get_next_page() if pagina.has_next_page else None


def sync_all_firebase_users():
    """Sincroniza todos los usuarios de Firebase con ``public.usuario``."""
    total = sincronizados = omitidos = errores = 0
    for usuario in _iterar_usuarios_firebase():
        total += 1
        if not usuario.email:
            omitidos += 1
            continue
        claims = usuario.custom_claims or {}
        datos = {
            'uid': usuario.uid,
            'email': usuario.email,
            'name': usuario.display_name,
            'nombres': claims.get('nombres'),
            'apellido_paterno': claims.get('apellido_paterno'),
            'apellido_materno': claims.get('apellido_materno'),
        }
        tipo_usuario = claims.get('tipo_usuario')
        try:
            sync_firebase_user(datos, tipo_usuario=tipo_usuario)
            sincronizados += 1
        except Exception as error:  # noqa: BLE001 - se reporta y se continúa
            errores += 1
            log.warning('No se pudo sincronizar %s: %s', usuario.uid, error)
    return {
        'total': total,
        'sincronizados': sincronizados,
        'omitidos': omitidos,
        'errores': errores,
    }



