"""Plantilla base de contratos (v1.0).

La plantilla vive en la tabla `plantilla_contrato` para que cada contrato
conserve una copia de los términos que estaban vigentes cuando se creó.
Al crear un contrato se reemplazan los marcadores ``{{...}}`` con los datos
de las partes y el resultado se guarda en ``contrato.terminos_condiciones``.

Para publicar una nueva versión de la plantilla, cambia
``NOMBRE_PLANTILLA_BASE`` y ``PLANTILLA_BASE_V1``: los contratos ya creados
conservan su copia y los nuevos usan la versión nueva.

No se evalúa la plantilla como código (no es Jinja): solo se hacen
reemplazos de texto, así que un texto malicioso en las notas no puede
ejecutar nada.
"""

import html

from app.contratos.models import PlantillaContrato
from app.extensions import db

NOMBRE_PLANTILLA_BASE = 'Contrato de Servicios Profesionales v1.0'


PLANTILLA_BASE_V1 = """
<h2>Contrato de Prestación de Servicios de Desarrollo de Software</h2>
<p>
  <strong>Contrato No.:</strong> {{contrato_id}}<br>
  <strong>Fecha de creación:</strong> {{fecha}}
</p>

<h3>1. Partes</h3>
<p>
  <strong>Cliente:</strong> {{cliente_nombre}} ({{cliente_email}})<br>
  <strong>Desarrollador:</strong> {{desarrollador_nombre}} ({{desarrollador_email}})
</p>

<h3>2. Objeto del contrato</h3>
<p>
  El Desarrollador se compromete a prestar los servicios de desarrollo de
  software correspondientes a: <strong>{{objeto}}</strong>.
</p>

<h3>3. Contraprestación</h3>
<p>
  El Cliente pagará la cantidad de <strong>${{costo}} MXN</strong>. El monto
  se retendrá en escrow y se liberará conforme a los entregables aprobados
  dentro de la plataforma Zaas.
</p>

<h3>4. Entregables y aceptación</h3>
<p>
  El Desarrollador cargará los entregables en la plataforma. El Cliente los
  revisará y podrá aprobarlos o rechazarlos con comentarios. El contrato se
  considerará entregado cuando no queden entregables pendientes y al menos
  uno haya sido aprobado.
</p>

<h3>5. Confidencialidad y propiedad intelectual</h3>
<p>
  Ambas partes se obligan a mantener confidencial la información
  intercambiada durante la ejecución del contrato. Una vez liberado el pago,
  los derechos patrimoniales del trabajo entregado se transfieren al Cliente,
  salvo pacto adicional por escrito.
</p>

<h3>6. Cancelación y disputas</h3>
<p>
  Cualquiera de las partes podrá cancelar el contrato antes de su finalización.
  Las diferencias se resolverán mediante el mecanismo de disputas y arbitraje
  de Zaas.
</p>

<h3>7. Aceptación digital</h3>
<p>
  Las partes aceptan los términos de este contrato mediante el botón de
  aceptación de la plataforma. La aceptación se registra con fecha, hora,
  dirección IP y un folio de verificación (hash).
</p>

{{notas_html}}

<div class="firmas">
  <div class="firma">
    <p>_________________________</p>
    <p><strong>{{cliente_nombre}}</strong><br>Cliente</p>
  </div>
  <div class="firma">
    <p>_________________________</p>
    <p><strong>{{desarrollador_nombre}}</strong><br>Desarrollador</p>
  </div>
</div>
""".strip()


def render_plantilla(contenido_html: str, contexto: dict, claves_html=None) -> str:
    """Reemplaza los marcadores de la plantilla con los datos del contrato.

    ``claves_html`` permite indicar qué valores ya vienen como HTML seguro
    (por ejemplo, las notas adicionales, que se escapan antes de convertirlas
    a HTML). El resto de valores se escapan para evitar inyección.
    """
    claves_html = claves_html or set()
    resultado = contenido_html
    for clave, valor in contexto.items():
        reemplazo = str(valor) if clave in claves_html else html.escape(str(valor))
        resultado = resultado.replace('{{' + clave + '}}', reemplazo)
    return resultado


def ensure_default_plantilla() -> PlantillaContrato:
    """Devuelve la plantilla base v1.0, creándola o actualizando el seed viejo."""
    plantilla = db.session.execute(
        db.select(PlantillaContrato).filter_by(nombre=NOMBRE_PLANTILLA_BASE)
    ).scalars().first()
    if plantilla is not None:
        return plantilla

    # Bases de datos creadas con el seed anterior: "Contrato Estándar" solo
    # tenía texto de ejemplo. Lo actualizamos en lugar de dejar una plantilla
    # inservible como opción por defecto.
    vieja = db.session.execute(
        db.select(PlantillaContrato).filter_by(nombre='Contrato Estándar')
    ).scalars().first()
    if vieja is not None and 'Términos estándar' in (vieja.contenido_html or ''):
        vieja.nombre = NOMBRE_PLANTILLA_BASE
        vieja.contenido_html = PLANTILLA_BASE_V1
        db.session.commit()
        return vieja

    plantilla = PlantillaContrato(
        nombre=NOMBRE_PLANTILLA_BASE,
        contenido_html=PLANTILLA_BASE_V1,
    )
    db.session.add(plantilla)
    db.session.commit()
    return plantilla
