"""Utilidades para sincronizar el perfil normalizado del MR.

El perfil ya no guarda cadenas de habilidades/tecnologías: ahora usa las tablas
intermedias ``perfil_habilidad`` y ``perfil_tecnologia``. Estas funciones aceptan
texto separado por comas o listas (de strings u objetos con ``nombre``) y dejan
exactamente los valores indicados.
"""

from sqlalchemy import func

from app.auth.models import Habilidad, PerfilHabilidad, PerfilTecnologia
from app.extensions import db


def normalizar_nombres(items):
    """Devuelve una lista de nombres únicos, sin vacíos y con máximo 100 caracteres."""
    if items is None:
        return []
    if isinstance(items, str):
        items = items.split(',')

    nombres = []
    vistos = set()
    for item in items:
        if isinstance(item, dict):
            nombre = str(item.get('nombre', '')).strip()
        else:
            nombre = str(item).strip()

        if not nombre:
            continue

        nombre = nombre[:100]
        clave = nombre.casefold()
        if clave in vistos:
            continue
        vistos.add(clave)
        nombres.append(nombre)
    return nombres


def _obtener_o_crear(modelo, nombre):
    existente = db.session.execute(
        db.select(modelo).where(func.lower(modelo.nombre) == nombre.lower())
    ).scalars().first()
    if existente:
        return existente

    nuevo = modelo(nombre=nombre)
    db.session.add(nuevo)
    db.session.flush()
    return nuevo


def sincronizar_habilidades(perfil, items):
    """Reemplaza las habilidades del perfil por las indicadas."""
    deseadas = {}
    for nombre in normalizar_nombres(items):
        habilidad = _obtener_o_crear(Habilidad, nombre)
        deseadas[habilidad.id] = habilidad

    actuales = {rel.id_habilidad: rel for rel in list(perfil.habilidades)}
    for id_habilidad, rel in list(actuales.items()):
        if id_habilidad not in deseadas:
            perfil.habilidades.remove(rel)

    for id_habilidad, habilidad in deseadas.items():
        if id_habilidad not in actuales:
            perfil.habilidades.append(PerfilHabilidad(habilidad=habilidad))


def sincronizar_tecnologias(perfil, items):
    """Reemplaza las tecnologías del perfil por las indicadas."""
    # Import local para evitar un ciclo auth.routes -> perfil_utils -> catalogo.
    from app.catalogo.models import Tecnologia

    deseadas = {}
    for nombre in normalizar_nombres(items):
        tecnologia = _obtener_o_crear(Tecnologia, nombre)
        deseadas[tecnologia.id] = tecnologia

    actuales = {rel.id_tecnologia: rel for rel in list(perfil.tecnologias)}
    for id_tecnologia, rel in list(actuales.items()):
        if id_tecnologia not in deseadas:
            perfil.tecnologias.remove(rel)

    for id_tecnologia, tecnologia in deseadas.items():
        if id_tecnologia not in actuales:
            perfil.tecnologias.append(PerfilTecnologia(tecnologia=tecnologia))
