from __future__ import annotations

from datetime import datetime

from sqlalchemy import or_

from app.auth.models import Usuario
from app.comunicacion.errors import (
    IncidenciaContratoAjenoError,
    IncidenciaContratoRequeridoError,
    IncidenciaDescripcionInvalidaError,
    IncidenciaDetalleRequeridoError,
    IncidenciaTipoInvalidoError,
)
from app.comunicacion.models import Incidencia, Notificacion
from app.contratos.models import Contrato
from app.extensions import db

TIPOS_INCIDENCIA = {"acoso", "fraude", "incumplimiento", "bug", "otro"}
TIPOS_REQUIEREN_CONTRATO = {"fraude", "incumplimiento"}

ESTADOS_CONTRATO_LABEL = {
    "borrador": "Borrador",
    "pendiente": "Pendiente",
    "aceptado": "Aceptado",
    "en_progreso": "En progreso",
    "entregado": "Entregado",
    "finalizado": "Finalizado",
    "cancelado": "Cancelado",
}


def _texto(valor):
    return str(valor or "").strip()


def _nombre_usuario(u):
    if u is None:
        return "Usuario"
    nombre = " ".join([p for p in [getattr(u, "nombres", ""), getattr(u, "apellido_paterno", ""), getattr(u, "apellido_materno", "")] if p]).strip()
    return nombre or getattr(u, "email", None) or "Usuario"


def contrato_legible(contrato, usuario_actual):
    objeto = getattr(contrato, "objeto", None) or "Contrato"
    # otra parte
    otra = None
    if getattr(contrato, "id_cliente", None) == getattr(usuario_actual, "id", None):
        otra = getattr(contrato, "desarrollador", None)
    elif getattr(contrato, "id_desarrollador", None) == getattr(usuario_actual, "id", None):
        otra = getattr(contrato, "cliente", None)
    else:
        otra = getattr(contrato, "cliente", None) or getattr(contrato, "desarrollador", None)
    otra_nombre = _nombre_usuario(otra)
    try:
        monto = f"${float(getattr(contrato, 'costo_acordado', 0) or 0):,.2f} MXN"
    except Exception:
        monto = "Monto no disponible"
    estado = ESTADOS_CONTRATO_LABEL.get(getattr(contrato, "estado", None), str(getattr(contrato, "estado", "") or "Desconocido"))
    return f"{objeto} — con {otra_nombre} — {monto} — {estado}"


def listar_contratos_usuario(usuario):
    contratos = db.session.execute(
        db.select(Contrato)
        .filter(or_(Contrato.id_cliente == usuario.id, Contrato.id_desarrollador == usuario.id))
        .order_by(Contrato.fecha_creacion.desc())
    ).scalars().all()
    items = []
    for c in contratos:
        items.append({
            "id": c.id,
            "etiqueta": contrato_legible(c, usuario),
            "estado": c.estado,
            "estado_etiqueta": ESTADOS_CONTRATO_LABEL.get(c.estado, c.estado or ""),
            "objeto": getattr(c, "objeto", None),
        })
    return items


def _resolver_contrato(id_contrato, usuario):
    if id_contrato in (None, "", 0, "0"):
        return None
    try:
        cid = int(id_contrato)
    except (TypeError, ValueError):
        raise IncidenciaContratoAjenoError()
    if cid <= 0:
        raise IncidenciaContratoAjenoError()
    contrato = db.session.get(Contrato, cid)
    if contrato is None:
        raise IncidenciaContratoAjenoError()
    # pertenencia: cliente o desarrollador (admin no crea en nombre ajeno aquí; se valida como usuario actual)
    if usuario.id not in (contrato.id_cliente, contrato.id_desarrollador):
        raise IncidenciaContratoAjenoError()
    return contrato


def crear_incidencia(usuario, datos):
    tipo = _texto((datos or {}).get("tipo")).lower()
    if not tipo or tipo not in TIPOS_INCIDENCIA:
        raise IncidenciaTipoInvalidoError()

    descripcion = _texto((datos or {}).get("descripcion"))
    if len(descripcion) < 10 or len(descripcion) > 1000:
        raise IncidenciaDescripcionInvalidaError()

    # contrato
    raw_contrato = (datos or {}).get("id_contrato")
    if tipo in TIPOS_REQUIEREN_CONTRATO and raw_contrato in (None, "", 0, "0"):
        raise IncidenciaContratoRequeridoError()
    contrato = _resolver_contrato(raw_contrato, usuario) if raw_contrato not in (None, "", 0, "0") else None
    if tipo in TIPOS_REQUIEREN_CONTRATO and contrato is None:
        raise IncidenciaContratoRequeridoError()

    # tipo_detalle
    raw_detalle = (datos or {}).get("tipo_detalle")
    detalle = _texto(raw_detalle)
    if tipo == "otro":
        if not detalle:
            raise IncidenciaDetalleRequeridoError()
        if len(detalle) > 100:
            raise IncidenciaDetalleRequeridoError("El detalle del tipo de incidencia no puede superar 100 caracteres.")
        tipo_detalle = detalle
    else:
        # solo obligatorio en nuevas de tipo otro; para otros tipos debe ser nulo
        tipo_detalle = None

    incidencia = Incidencia(
        id_usuario=usuario.id,
        id_contrato=contrato.id if contrato else None,
        tipo=tipo,
        descripcion=descripcion,
        tipo_detalle=tipo_detalle,
        estado="abierta",
    )
    db.session.add(incidencia)
    db.session.flush()

    admins = db.session.execute(db.select(Usuario).filter_by(tipo_usuario="admin")).scalars().all()
    etiqueta_tipo = tipo_detalle if (tipo == "otro" and tipo_detalle) else tipo
    for admin in admins:
        db.session.add(Notificacion(
            id_usuario=admin.id,
            asunto=f"Nueva incidencia: {etiqueta_tipo}"[:200],
            mensaje=f"Nueva incidencia de {_nombre_usuario(usuario)}: {etiqueta_tipo}",
            link="/incidencias",
        ))
    return incidencia
