"""Servicios (reglas de negocio) del módulo de Pagos.

Mantiene la lógica fuera de las rutas para que pueda reutilizarse y probarse.
Todas las operaciones validan permisos y coherencia antes de tocar la BD.
"""

from datetime import datetime

from sqlalchemy import func

from app.auth.models import Usuario
from app.contratos.models import Contrato, Entregable
from app.extensions import db
from app.pagos.models import Arbitraje, Disputa, Liberacion, Pago, Recibo


# ---------------------------------------------------------------- adaptador

class ProveedorPagoStub:
    """Adaptador simulado de proveedor de pagos (TODO: integrar proveedor real)."""

    def procesar(self, monto):
        import uuid

        return f'TX-{uuid.uuid4().hex[:12].upper()}'


proveedor_pago = ProveedorPagoStub()


def procesar_pago_simulado(monto):
    """Devuelve un identificador de transacción simulado."""
    return proveedor_pago.procesar(monto)


# ---------------------------------------------------------------- helpers

def _es_parte(contrato, usuario):
    return usuario.id in (contrato.id_cliente, contrato.id_desarrollador)


def _contrato_permite_pagos(contrato):
    # Estados que ya usa el código para admitir pagos.
    return contrato.estado in ('aceptado', 'en_progreso', 'entregado')


def contrato_de_usuario(id_contrato, usuario):
    contrato = db.session.get(Contrato, id_contrato)
    if contrato is None:
        return None
    if usuario.tipo_usuario == 'admin':
        return contrato
    if usuario.id not in (contrato.id_cliente, contrato.id_desarrollador):
        return None
    return contrato


# ---------------------------------------------------------------- pagos

def registrar_pago(contrato, usuario, monto=None, metodo_pago=None, transaccion_id=None):
    if usuario.id != contrato.id_cliente:
        raise ValueError('Solo el cliente del contrato puede registrar un pago.')
    if not _contrato_permite_pagos(contrato):
        raise ValueError('Este contrato no está listo para pago.')

    if monto is None:
        monto = contrato.costo_acordado
    try:
        monto = float(monto)
    except (TypeError, ValueError):
        raise ValueError('El monto debe ser numérico.')
    if monto <= 0:
        raise ValueError('El monto debe ser mayor a 0.')

    if transaccion_id is None:
        transaccion_id = procesar_pago_simulado(monto)

    pago = Pago(
        id_contrato=contrato.id,
        monto=monto,
        estado_escrow='retenido',
        fecha_pago=datetime.utcnow(),
        metodo_pago=metodo_pago or 'simulado',
        transaccion_id=transaccion_id,
    )
    db.session.add(pago)
    db.session.flush()

    # Generar recibo automáticamente.
    generar_recibo(pago, contrato)
    return pago


def obtener_pago(id_pago, usuario):
    pago = db.session.get(Pago, id_pago)
    if pago is None:
        return None
    contrato = pago.contrato
    if contrato is None:
        return None
    if usuario.tipo_usuario != 'admin' and usuario.id not in (contrato.id_cliente, contrato.id_desarrollador):
        return None
    return pago


def listar_pagos_contrato(id_contrato, usuario):
    contrato = contrato_de_usuario(id_contrato, usuario)
    if contrato is None:
        return None
    return sorted(contrato.pagos or [], key=lambda p: p.fecha_pago or datetime.min)


# ---------------------------------------------------------------- liberaciones

def crear_liberacion(pago, usuario, monto_liberado, id_entregable=None, motivo=None):
    contrato = pago.contrato
    if usuario.tipo_usuario != 'admin' and usuario.id != contrato.id_cliente:
        raise PermissionError('Solo el cliente (o un admin) puede liberar fondos.')

    # Bloqueo de fila para evitar condiciones de carrera.
    pago_bloqueado = db.session.execute(
        db.select(Pago).where(Pago.id == pago.id).with_for_update()
    ).scalar_one()

    try:
        monto_liberado = float(monto_liberado)
    except (TypeError, ValueError):
        raise ValueError('El monto a liberar debe ser numérico.')
    if monto_liberado <= 0:
        raise ValueError('El monto a liberar debe ser mayor a 0.')

    if id_entregable is not None:
        entregable = db.session.get(Entregable, id_entregable)
        if entregable is None or entregable.id_contrato != contrato.id:
            raise ValueError('El entregable no pertenece a este contrato.')
    else:
        entregable = None

    ya_liberado = db.session.execute(
        db.select(func.coalesce(func.sum(Liberacion.monto_liberado), 0.0))
        .where(Liberacion.id_pago == pago.id)
    ).scalar() or 0.0
    if float(ya_liberado) + monto_liberado > float(pago.monto) + 1e-9:
        raise ValueError('La suma de liberaciones supera el monto del pago.')

    if pago_bloqueado.estado_escrow in ('reembolsado', 'dividido'):
        raise ValueError('No se pueden liberar fondos de un pago reembolsado o dividido.')

    liberacion = Liberacion(
        id_pago=pago.id,
        id_usuario=usuario.id,
        id_entregable=id_entregable,
        monto_liberado=monto_liberado,
        motivo=motivo,
        fecha_hora=datetime.utcnow(),
    )
    db.session.add(liberacion)

    total_liberado = float(ya_liberado) + monto_liberado
    if total_liberado >= float(pago.monto) - 1e-9:
        pago_bloqueado.estado_escrow = 'liberado'
        pago_bloqueado.fecha_liberacion = datetime.utcnow()
    else:
        pago_bloqueado.estado_escrow = 'retenido'
    db.session.flush()
    return liberacion


def listar_liberaciones_pago(id_pago, usuario):
    pago = obtener_pago(id_pago, usuario)
    if pago is None:
        return None
    return list(pago.liberaciones or [])


# ---------------------------------------------------------------- recibos

def generar_recibo(pago, contrato=None):
    existente = db.session.execute(
        db.select(Recibo).filter_by(id_pago=pago.id)
    ).scalar_one_or_none()
    if existente is not None:
        return existente
    if contrato is None:
        contrato = pago.contrato
    folio = f'ZAS-{datetime.utcnow().strftime("%Y%m%d")}-{__import__("uuid").uuid4().hex[:8].upper()}'
    recibo = Recibo(
        id_pago=pago.id,
        folio=folio,
        fecha_emision=datetime.utcnow(),
        total=pago.monto,
        contenido_html=None,
    )
    db.session.add(recibo)
    return recibo


def obtener_recibo_pago(id_pago, usuario):
    pago = obtener_pago(id_pago, usuario)
    if pago is None:
        return None
    return db.session.execute(
        db.select(Recibo).filter_by(id_pago=pago.id)
    ).scalar_one_or_none()


# ---------------------------------------------------------------- disputas

def abrir_disputa(contrato, reportante, tipo, descripcion, id_pago=None, id_entregable=None, id_incidencia=None):
    if reportante.id not in (contrato.id_cliente, contrato.id_desarrollador):
        raise PermissionError('Solo las partes del contrato pueden abrir una disputa.')
    if contrato.estado in ('finalizado', 'cancelado'):
        raise ValueError('No puedes abrir una disputa de un contrato cerrado.')
    if any(d.estado in ('abierta', 'en_revision') for d in (contrato.disputas or [])):
        raise ValueError('Ya existe una disputa abierta para este contrato.')

    if id_pago is not None and id_entregable is not None:
        raise ValueError('No puedes indicar pago y entregable a la vez.')

    if id_pago is not None:
        pago = db.session.get(Pago, id_pago)
        if pago is None or pago.id_contrato != contrato.id:
            raise ValueError('El pago no pertenece a este contrato.')
    if id_entregable is not None:
        entregable = db.session.get(Entregable, id_entregable)
        if entregable is None or entregable.id_contrato != contrato.id:
            raise ValueError('El entregable no pertenece a este contrato.')

    if id_incidencia is not None:
        incidencia = db.session.get('Incidencia', id_incidencia) if False else None
        # import local
        from app.comunicacion.models import Incidencia

        incidencia = db.session.get(Incidencia, id_incidencia)
        if incidencia is None:
            raise ValueError('La incidencia indicada no existe.')
        existente = db.session.execute(
            db.select(Disputa).filter_by(id_incidencia=id_incidencia)
        ).scalar_one_or_none()
        if existente is not None:
            raise ValueError('La incidencia ya está ligada a otra disputa.')
        # Coherencia solo si el dato existe.
        if getattr(incidencia, 'id_contrato', None) is not None and incidencia.id_contrato != contrato.id:
            raise ValueError('La incidencia no pertenece a este contrato.')

    tipo = (tipo or '').strip() or 'otro'
    descripcion = (descripcion or '').strip()
    if not descripcion:
        raise ValueError('La descripción es obligatoria.')

    disputa = Disputa(
        id_contrato=contrato.id,
        id_reportante=reportante.id,
        id_pago=id_pago,
        id_entregable=id_entregable,
        id_incidencia=id_incidencia,
        tipo=tipo,
        descripcion=descripcion,
        estado='abierta',
        fecha_hora_publicacion=datetime.utcnow(),
    )
    db.session.add(disputa)
    return disputa


def obtener_disputa(id_disputa, usuario):
    disputa = db.session.get(Disputa, id_disputa)
    if disputa is None:
        return None
    contrato = disputa.contrato
    if usuario.tipo_usuario == 'admin':
        return disputa
    if usuario.id not in (contrato.id_cliente, contrato.id_desarrollador):
        return None
    return disputa


def listar_disputas(usuario):
    query = db.select(Disputa).order_by(Disputa.fecha_hora_publicacion.desc())
    if usuario.tipo_usuario != 'admin':
        # Cada parte ve las suyas: reportante o parte del contrato.
        query = query.join(Contrato).filter(
            (Disputa.id_reportante == usuario.id)
            | (Contrato.id_cliente == usuario.id)
            | (Contrato.id_desarrollador == usuario.id)
        )
    return db.session.execute(query).scalars().all()


# ---------------------------------------------------------------- arbitraje

def crear_arbitraje(disputa, arbitro, decision, porcentaje=None, notas=None):
    if arbitro.tipo_usuario != 'admin':
        raise PermissionError('Solo un administrador puede arbitrar.')
    if disputa.estado in ('resuelta', 'cerrada'):
        raise ValueError('Esta disputa ya fue resuelta.')
    existente = db.session.execute(
        db.select(Arbitraje).filter_by(id_disputa=disputa.id)
    ).scalar_one_or_none()
    if existente is not None:
        raise ValueError('Ya existe un arbitraje para esta disputa.')

    if decision not in ('liberar', 'reembolsar', 'dividir'):
        raise ValueError('Decisión inválida.')
    porcentaje_val = None
    if decision == 'dividir':
        if porcentaje is None:
            raise ValueError('El porcentaje es obligatorio en una división.')
        try:
            porcentaje_val = float(porcentaje)
        except (TypeError, ValueError):
            raise ValueError('El porcentaje debe ser numérico.')
        if not 0 <= porcentaje_val <= 100:
            raise ValueError('El porcentaje debe estar entre 0 y 100.')
    elif porcentaje is not None:
        try:
            porcentaje_val = float(porcentaje)
        except (TypeError, ValueError):
            porcentaje_val = None

    arbitraje = Arbitraje(
        id_disputa=disputa.id,
        id_arbitro=arbitro.id,
        decision=decision,
        porcentaje_desarrollador=porcentaje_val,
        notas=(notas or '').strip() or None,
        fecha_hora=datetime.utcnow(),
    )
    db.session.add(arbitraje)

    disputa.id_admin = arbitro.id
    disputa.estado = 'resuelta'
    disputa.fecha_hora_resolucion = datetime.utcnow()
    disputa.resolucion = (notas or '').strip() or None

    # Actualizar pago(s) involucrado(s).
    pagos = []
    if disputa.id_pago is not None:
        pago = db.session.get(Pago, disputa.id_pago)
        if pago is not None:
            pagos = [pago]
    else:
        # Origen contrato/entregable: aplicar sobre pagos retenidos del contrato.
        pagos = [p for p in (disputa.contrato.pagos or []) if p.estado_escrow == 'retenido']

    for pago in pagos:
        pago.fecha_liberacion = datetime.utcnow()
        if decision == 'liberar':
            pago.estado_escrow = 'liberado'
        elif decision == 'reembolsar':
            pago.estado_escrow = 'reembolsado'
        elif decision == 'dividir':
            pago.estado_escrow = 'dividido'
    return arbitraje


def obtener_arbitraje_disputa(id_disputa, usuario):
    disputa = obtener_disputa(id_disputa, usuario)
    if disputa is None:
        return None
    return db.session.execute(
        db.select(Arbitraje).filter_by(id_disputa=disputa.id)
    ).scalar_one_or_none()
