"""Plantillas de contrato por tipo de operación.

Cada plantilla vive en la tabla ``plantilla_contrato`` para que cada contrato
conserve una copia inmutable de los términos que estaban vigentes cuando se
creó. Al crear un contrato se reemplazan los marcadores ``{{...}}`` con los
datos de las partes y el resultado se guarda en
``contrato.terminos_condiciones``.

Tipos disponibles:
  - desarrollo: desarrollo de software a medida.
  - licencia_software: licencia de uso de un software ya existente.
  - compra_codigo: compraventa y cesión del código fuente.
  - soporte_mantenimiento: soporte, mantenimiento y actualizaciones.

No se evalúa la plantilla como código (no es Jinja): solo se hacen
reemplazos de texto, así que un texto malicioso en las notas no puede
ejecutar nada.
"""

import html

from app.contratos.models import PlantillaContrato
from app.extensions import db

NOMBRE_DESARROLLO = 'Contrato de Desarrollo de Software a Medida v1.0'
NOMBRE_LICENCIA = 'Contrato de Licencia de Uso de Software v1.0'
NOMBRE_CODIGO_FUENTE = 'Contrato de Compraventa de Código Fuente v1.0'
NOMBRE_SOPORTE = 'Contrato de Soporte y Mantenimiento v1.0'

# Nombre histórico que se conserva para migrar bases de datos existentes.
NOMBRE_PLANTILLA_LEGACY = 'Contrato de Servicios Profesionales v1.0'
NOMBRE_PLANTILLA_BASE = NOMBRE_DESARROLLO


_FIRMAS_Y_NOTAS = """
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


PLANTILLA_DESARROLLO_V1 = f"""
<h2>Contrato de Desarrollo de Software a Medida</h2>
<p>
  <strong>Contrato No.:</strong> {{{{contrato_id}}}}<br>
  <strong>Fecha de creación:</strong> {{{{fecha}}}}
</p>

<h3>1. Partes</h3>
<p>
  <strong>Cliente:</strong> {{{{cliente_nombre}}}} ({{{{cliente_email}}}})<br>
  <strong>Desarrollador:</strong> {{{{desarrollador_nombre}}}} ({{{{desarrollador_email}}}})
</p>

<h3>2. Objeto del contrato</h3>
<p>
  El Desarrollador se compromete a prestar los servicios de desarrollo de
  software a medida correspondientes a: <strong>{{{{objeto}}}}</strong>.
</p>

<h3>3. Contraprestación y custodia de fondos</h3>
<p>
  El Cliente pagará la cantidad de <strong>${{{{costo}}}} MXN</strong>. El monto
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

<h3>5. Propiedad intelectual</h3>
<p>
  Una vez liberado el pago total, el Desarrollador cede al Cliente los derechos
  patrimoniales sobre el código, la documentación y demás entregables creados
  específicamente para este contrato. Las herramientas, librerías y
  componentes preexistentes conservan su licencia original.
</p>

<h3>6. Confidencialidad</h3>
<p>
  Ambas partes se obligan a mantener confidencial la información intercambiada
  durante la ejecución del contrato y a utilizarla únicamente para cumplir con
  el objeto pactado.
</p>

<h3>7. Cancelación y disputas</h3>
<p>
  Cualquiera de las partes podrá cancelar el contrato antes de su finalización.
  Las diferencias se resolverán mediante el mecanismo de disputas y arbitraje
  de Zaas.
</p>

<h3>8. Aceptación digital</h3>
<p>
  Las partes aceptan los términos de este contrato mediante el botón de
  aceptación de la plataforma. La aceptación se registra con fecha, hora,
  dirección IP y un folio de verificación (hash).
</p>

{_FIRMAS_Y_NOTAS}
""".strip()


PLANTILLA_LICENCIA_V1 = f"""
<h2>Contrato de Licencia de Uso de Software</h2>
<p>
  <strong>Contrato No.:</strong> {{{{contrato_id}}}}<br>
  <strong>Fecha de creación:</strong> {{{{fecha}}}}
</p>

<h3>1. Partes</h3>
<p>
  <strong>Licenciante:</strong> {{{{desarrollador_nombre}}}} ({{{{desarrollador_email}}}})<br>
  <strong>Licenciatario:</strong> {{{{cliente_nombre}}}} ({{{{cliente_email}}}})
</p>

<h3>2. Objeto</h3>
<p>
  El Licenciante otorga al Licenciatario una licencia de uso sobre el software
  <strong>{{{{objeto}}}}</strong>, en las condiciones y con el alcance descritos
  en este contrato.
</p>

<h3>3. Alcance de la licencia</h3>
<p>
  La licencia es no exclusiva, no transferible y limitada al uso interno del
  Licenciatario. Salvo pacto adicional por escrito, no incluye la venta,
  cesión o transmisión del código fuente ni de los derechos patrimoniales del
  software.
</p>

<h3>4. Restricciones</h3>
<p>
  El Licenciatario no podrá sublicenciar, revender, redistribuir ni poner el
  software a disposición de terceros como producto propio. Tampoco podrá
  descompilar, realizar ingeniería inversa o intentar obtener el código fuente,
  salvo en los casos permitidos por la ley.
</p>

<h3>5. Contraprestación y custodia de fondos</h3>
<p>
  El Licenciatario pagará la cantidad de <strong>${{{{costo}}}} MXN</strong>.
  El monto se retendrá en escrow y se liberará conforme a las condiciones de
  entrega y aceptación acordadas en la plataforma Zaas.
</p>

<h3>6. Soporte y actualizaciones</h3>
<p>
  Salvo que se contrate un servicio adicional, la licencia no incluye soporte,
  mantenimiento ni actualizaciones futuras. Cualquier servicio adicional deberá
  documentarse mediante un contrato independiente.
</p>

<h3>7. Propiedad intelectual</h3>
<p>
  El software, su código fuente, documentación, marcas y demás elementos
  continúan siendo propiedad del Licenciante. Este contrato solo concede el
  derecho de uso limitado descrito en las cláusulas anteriores.
</p>

<h3>8. Confidencialidad</h3>
<p>
  Las partes mantendrán confidencial la información técnica, comercial y
  operativa conocida con motivo de este contrato y no la divulgarán a terceros
  sin autorización previa por escrito.
</p>

<h3>9. Vigencia y terminación</h3>
<p>
  La licencia tendrá la vigencia pactada en la plataforma. El incumplimiento
  grave de las restricciones faculta al Licenciante a terminar la licencia,
  sin perjuicio de las acciones legales que correspondan.
</p>

<h3>10. Disputas y aceptación digital</h3>
<p>
  Las diferencias se resolverán mediante el mecanismo de disputas y arbitraje
  de Zaas. Las partes aceptan los términos mediante el botón de aceptación de
  la plataforma, que registra fecha, hora, dirección IP y folio de verificación.
</p>

{_FIRMAS_Y_NOTAS}
""".strip()


PLANTILLA_CODIGO_FUENTE_V1 = f"""
<h2>Contrato de Compraventa de Código Fuente</h2>
<p>
  <strong>Contrato No.:</strong> {{{{contrato_id}}}}<br>
  <strong>Fecha de creación:</strong> {{{{fecha}}}}
</p>

<h3>1. Partes</h3>
<p>
  <strong>Vendedor:</strong> {{{{desarrollador_nombre}}}} ({{{{desarrollador_email}}}})<br>
  <strong>Comprador:</strong> {{{{cliente_nombre}}}} ({{{{cliente_email}}}})
</p>

<h3>2. Objeto</h3>
<p>
  El Vendedor se obliga a transferir al Comprador el código fuente, los archivos
  de compilación, la documentación técnica y los derechos patrimoniales
  asociados al software <strong>{{{{objeto}}}}</strong>, en los términos de este
  contrato.
</p>

<h3>3. Precio y custodia de fondos</h3>
<p>
  El Comprador pagará la cantidad de <strong>${{{{costo}}}} MXN</strong>. El monto
  se retendrá en escrow y se liberará una vez que el Comprador verifique y
  acepte la entrega del código y la documentación.
</p>

<h3>4. Entrega y verificación</h3>
<p>
  El Vendedor entregará el repositorio o paquete de código, las instrucciones
  de instalación, las dependencias y la documentación necesaria para compilar y
  ejecutar el software. El Comprador dispondrá del plazo acordado en la
  plataforma para revisar la entrega y reportar faltantes o defectos.
</p>

<h3>5. Propiedad intelectual</h3>
<p>
  Una vez liberado el pago total, el Vendedor cede al Comprador todos los
  derechos patrimoniales sobre el código y la documentación entregados. El
  Vendedor conserva los derechos morales y las herramientas o componentes de
  terceros, que se rigen por sus propias licencias.
</p>

<h3>6. Garantías</h3>
<p>
  El Vendedor declara que es titular de los derechos necesarios para realizar
  esta venta y que el código no infringe derechos de terceros. El software se
  entrega en el estado en que se encuentra, sin garantías implícitas distintas
  de las expresamente pactadas.
</p>

<h3>7. Confidencialidad</h3>
<p>
  El Comprador tratará el código y la documentación como información
  confidencial y no los divulgará a terceros ajenos a la operación, salvo
  obligación legal o autorización del Vendedor.
</p>

<h3>8. Cancelación y disputas</h3>
<p>
  Cualquiera de las partes podrá cancelar el contrato antes de la liberación de
  los fondos. Las diferencias se resolverán mediante el mecanismo de disputas y
  arbitraje de Zaas.
</p>

<h3>9. Aceptación digital</h3>
<p>
  Las partes aceptan los términos mediante el botón de aceptación de la
  plataforma. La aceptación se registra con fecha, hora, dirección IP y folio
  de verificación (hash).
</p>

{_FIRMAS_Y_NOTAS}
""".strip()


PLANTILLA_SOPORTE_V1 = f"""
<h2>Contrato de Soporte y Mantenimiento</h2>
<p>
  <strong>Contrato No.:</strong> {{{{contrato_id}}}}<br>
  <strong>Fecha de creación:</strong> {{{{fecha}}}}
</p>

<h3>1. Partes</h3>
<p>
  <strong>Proveedor:</strong> {{{{desarrollador_nombre}}}} ({{{{desarrollador_email}}}})<br>
  <strong>Cliente:</strong> {{{{cliente_nombre}}}} ({{{{cliente_email}}}})
</p>

<h3>2. Objeto</h3>
<p>
  El Proveedor prestará servicios de soporte, mantenimiento correctivo y
  actualizaciones sobre <strong>{{{{objeto}}}}</strong>, conforme al alcance y a
  los niveles de servicio pactados en la plataforma.
</p>

<h3>3. Alcance de los servicios</h3>
<p>
  Los servicios incluyen la atención de incidencias, corrección de errores,
  mantenimiento preventivo y las actualizaciones expresamente acordadas. No
  incluyen desarrollos nuevos, integraciones adicionales ni cambios de alcance
  que no hayan sido cotizados por separado.
</p>

<h3>4. Contraprestación y custodia de fondos</h3>
<p>
  El Cliente pagará la cantidad de <strong>${{{{costo}}}} MXN</strong> por el
  periodo o alcance pactado. El monto se retendrá en escrow y se liberará
  conforme a la aceptación de los servicios o entregables definidos.
</p>

<h3>5. Niveles de servicio</h3>
<p>
  El Proveedor atenderá las incidencias dentro de los plazos acordados en la
  plataforma. Los tiempos de respuesta podrán ajustarse por causas imputables
  al Cliente, dependencias de terceros o casos de fuerza mayor.
</p>

<h3>6. Obligaciones del Cliente</h3>
<p>
  El Cliente proporcionará acceso a la información, entornos y usuarios
  necesarios para prestar el servicio, y reportará las incidencias con el
  detalle suficiente para su diagnóstico y atención.
</p>

<h3>7. Propiedad intelectual</h3>
<p>
  El software preexistente y las herramientas del Proveedor conservan su
  titularidad y licencias. Las mejoras o desarrollos nuevos creados para este
  contrato se regirán por lo que las partes acuerden por escrito.
</p>

<h3>8. Confidencialidad</h3>
<p>
  Las partes mantendrán confidencial la información técnica, comercial y
  operativa conocida con motivo del servicio y la usarán únicamente para
  cumplir con este contrato.
</p>

<h3>9. Vigencia, cancelación y disputas</h3>
<p>
  El contrato tendrá la vigencia pactada. Cualquiera de las partes podrá
  cancelarlo conforme a las condiciones de la plataforma. Las diferencias se
  resolverán mediante el mecanismo de disputas y arbitraje de Zaas.
</p>

<h3>10. Aceptación digital</h3>
<p>
  Las partes aceptan los términos mediante el botón de aceptación de la
  plataforma. La aceptación se registra con fecha, hora, dirección IP y folio
  de verificación (hash).
</p>

{_FIRMAS_Y_NOTAS}
""".strip()


TIPOS_CONTRATO = (
    {
        'clave': 'desarrollo',
        'etiqueta': 'Desarrollo de software a medida',
        'nombre': NOMBRE_DESARROLLO,
        'descripcion': 'Para encargos de desarrollo con entregables y propiedad intelectual cedida al liberar el pago.',
        'html': PLANTILLA_DESARROLLO_V1,
        'alias': (NOMBRE_PLANTILLA_LEGACY, 'Contrato Estándar'),
    },
    {
        'clave': 'licencia_software',
        'etiqueta': 'Licencia de uso del software',
        'nombre': NOMBRE_LICENCIA,
        'descripcion': 'Para vender el derecho de uso de un SaaS o software existente sin transferir el código fuente.',
        'html': PLANTILLA_LICENCIA_V1,
        'alias': (),
    },
    {
        'clave': 'compra_codigo',
        'etiqueta': 'Compra del código fuente',
        'nombre': NOMBRE_CODIGO_FUENTE,
        'descripcion': 'Para transferir el código fuente, la documentación y los derechos patrimoniales al comprador.',
        'html': PLANTILLA_CODIGO_FUENTE_V1,
        'alias': (),
    },
    {
        'clave': 'soporte_mantenimiento',
        'etiqueta': 'Soporte y mantenimiento',
        'nombre': NOMBRE_SOPORTE,
        'descripcion': 'Para servicios recurrentes de soporte, corrección de errores y actualizaciones.',
        'html': PLANTILLA_SOPORTE_V1,
        'alias': (),
    },
)

# Compatibilidad con imports anteriores (seed y pruebas).
PLANTILLA_BASE_V1 = PLANTILLA_DESARROLLO_V1


def info_plantilla(nombre: str) -> dict:
    """Devuelve el tipo y la etiqueta legible de una plantilla por su nombre."""
    for spec in TIPOS_CONTRATO:
        if spec['nombre'] == nombre:
            return {
                'tipo': spec['clave'],
                'etiqueta': spec['etiqueta'],
                'descripcion': spec['descripcion'],
            }
    return {
        'tipo': 'personalizada',
        'etiqueta': nombre or 'Plantilla personalizada',
        'descripcion': 'Plantilla configurada por la administración.',
    }


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


def _buscar_plantilla(nombre: str):
    return db.session.execute(
        db.select(PlantillaContrato).filter_by(nombre=nombre)
    ).scalars().first()


def ensure_plantillas() -> list[PlantillaContrato]:
    """Crea las plantillas base de cada tipo sin sobrescribir las existentes."""
    for spec in TIPOS_CONTRATO:
        existente = _buscar_plantilla(spec['nombre'])
        if existente is None:
            for alias in spec.get('alias', ()):
                candidato = _buscar_plantilla(alias)
                if candidato is None:
                    continue
                contenido = candidato.contenido_html or ''
                # No convertir plantillas personalizadas que casualmente se
                # llamen "Contrato Estándar"; solo el seed de ejemplo.
                if alias == 'Contrato Estándar' and 'Términos estándar' not in contenido:
                    continue
                existente = candidato
                existente.nombre = spec['nombre']
                if (
                    'Términos estándar' in contenido
                    or 'Contrato de Prestación de Servicios de Desarrollo de Software' in contenido
                ):
                    existente.contenido_html = spec['html']
                break
        if existente is None:
            db.session.add(PlantillaContrato(
                nombre=spec['nombre'],
                contenido_html=spec['html'],
            ))
    db.session.commit()
    return db.session.execute(
        db.select(PlantillaContrato).order_by(PlantillaContrato.id)
    ).scalars().all()


def ensure_default_plantilla() -> PlantillaContrato:
    """Devuelve la plantilla de desarrollo, creándola si aún no existe."""
    plantilla = _buscar_plantilla(NOMBRE_DESARROLLO)
    if plantilla is not None:
        return plantilla
    ensure_plantillas()
    plantilla = _buscar_plantilla(NOMBRE_DESARROLLO)
    if plantilla is None:
        plantilla = PlantillaContrato(
            nombre=NOMBRE_DESARROLLO,
            contenido_html=PLANTILLA_DESARROLLO_V1,
        )
        db.session.add(plantilla)
        db.session.commit()
    return plantilla
