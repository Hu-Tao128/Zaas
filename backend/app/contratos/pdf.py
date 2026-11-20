"""Generación del PDF descargable de un contrato.

El PDF es una representación imprimible del documento que ya vive en
``contrato.terminos_condiciones`` más un resumen de las partes, el estado
actual y el registro de firmas/aceptaciones. Se puede descargar en cualquier
estado del contrato.
"""

import html
from datetime import datetime, timezone

from weasyprint import HTML

from app.contratos.plantillas import info_plantilla

ESTADOS = {
    'borrador': 'Borrador',
    'pendiente': 'Pendiente de firma',
    'aceptado': 'Aceptado',
    'en_progreso': 'En progreso',
    'entregado': 'Entregado',
    'finalizado': 'Finalizado',
    'cancelado': 'Cancelado',
}

ESTADOS_ESCROW = {
    'pendiente': 'Pendiente',
    'fallido': 'Fallido',
    'retenido': 'En custodia',
    'liberado': 'Liberado',
    'reembolsado': 'Reembolsado',
    'dividido': 'Dividido',
    'sin_deposito': 'Sin depósito',
}

CSS = """
@page {
  size: A4;
  margin: 20mm 17mm 18mm;
  @bottom-center {
    content: "Zaas · Contrato escrow · Documento generado electrónicamente";
    color: #6b7280;
    font-size: 8pt;
  }
}
* { box-sizing: border-box; }
body {
  font-family: "DejaVu Sans", Arial, sans-serif;
  color: #111827;
  font-size: 10.2pt;
  line-height: 1.45;
}
.brand-bar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  border-bottom: 3px solid #dc2626;
  padding-bottom: 0.6rem;
  margin-bottom: 1rem;
}
.brand { color: #dc2626; font-weight: 800; font-size: 13pt; letter-spacing: 0.04em; }
.brand small { display: block; color: #6b7280; font-weight: 500; font-size: 8pt; letter-spacing: 0; }
.doc-type { text-align: right; font-size: 9pt; color: #374151; }
.doc-type strong { display: block; font-size: 10.5pt; color: #111827; }
h1 { font-size: 17pt; margin: 0 0 0.35rem; color: #111827; }
h2 { font-size: 13.5pt; margin: 1.1rem 0 0.45rem; color: #111827; }
h3 { font-size: 10.8pt; margin: 0.9rem 0 0.25rem; color: #111827; }
p { margin: 0.35rem 0; }
table { width: 100%; border-collapse: collapse; margin: 0.5rem 0 0.9rem; }
th, td { border: 1px solid #d1d5db; padding: 5px 7px; text-align: left; vertical-align: top; font-size: 9.2pt; }
th { background: #f3f4f6; color: #374151; }
.resumen { margin-bottom: 1rem; }
.resumen p { margin: 0.15rem 0; }
.documento { border-top: 1px solid #e5e7eb; padding-top: 0.6rem; }
.documento .firmas { display: flex; gap: 2.5rem; margin-top: 2rem; }
.documento .firma { flex: 1; text-align: center; }
.documento .firma p { margin: 0.2rem 0; }
.firmas-registro { page-break-before: always; }
.folio { font-family: "DejaVu Sans Mono", monospace; font-size: 7.8pt; word-break: break-all; }
.aviso { margin-top: 1rem; padding: 0.7rem 0.85rem; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; color: #7f1d1d; font-size: 9pt; }
.muted { color: #6b7280; font-size: 8.5pt; }
"""


def _e(valor):
    return html.escape(str(valor if valor is not None else ''))


def _fecha(valor):
    if not valor:
        return 'No disponible'
    if hasattr(valor, 'strftime'):
        return valor.strftime('%d/%m/%Y %H:%M')
    return str(valor)


def _dinero(valor):
    try:
        return f'${float(valor or 0):,.2f}'
    except (TypeError, ValueError):
        return '$0.00'


def _tipo_contrato(contrato):
    if contrato.plantilla is None:
        return 'Contrato de servicios'
    return info_plantilla(contrato.plantilla.nombre)['etiqueta']


def _firmas_contrato(contrato):
    return [
        ('Cliente', contrato.cliente, contrato.firma_cliente),
        ('Desarrollador', contrato.desarrollador, contrato.firma_desarrollador),
    ]


def _estado_escrow(contrato):
    pagos = list(contrato.pagos or [])
    if not pagos:
        return 'Sin depósito'
    estados = {p.estado_escrow for p in pagos}
    if len(estados) == 1:
        return ESTADOS_ESCROW.get(next(iter(estados)), 'Sin depósito')
    if 'retenido' in estados:
        return 'En custodia (parcial)'
    return 'Mixto'


def generar_pdf_contrato(contrato) -> bytes:
    """Construye y devuelve el PDF del contrato en cualquier estado."""
    estado = ESTADOS.get(contrato.estado, contrato.estado or 'Sin estado')
    tipo = _tipo_contrato(contrato)
    objeto = contrato.objeto
    escrow = _estado_escrow(contrato)

    firmas_html = ''.join(
        f"""
        <tr>
          <td>{_e(parte)}</td>
          <td>{_e(usuario.nombre_completo if usuario else 'No disponible')}</td>
          <td>{'Firmado' if folio else 'Pendiente'}</td>
          <td class="folio">{_e(folio or '—')}</td>
        </tr>
        """
        for parte, usuario, folio in _firmas_contrato(contrato)
    )

    aceptaciones = list(contrato.aceptaciones or [])
    aceptaciones_html = ''.join(
        f"""
        <tr>
          <td>{_e(aceptacion.usuario.nombre_completo if aceptacion.usuario else 'Usuario')}</td>
          <td>{_e(_fecha(aceptacion.fecha_hora))}</td>
          <td>{_e(aceptacion.ip or 'No disponible')}</td>
        </tr>
        """
        for aceptacion in aceptaciones
    )
    if not aceptaciones_html:
        aceptaciones_html = (
            '<tr><td colspan="3" class="muted">'
            'Aún no hay aceptaciones digitales registradas.'
            '</td></tr>'
        )

    documento = contrato.terminos_condiciones or (
        '<p class="muted">Este contrato todavía no tiene términos generados.</p>'
    )

    contenido = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Contrato #{contrato.id}</title>
  <style>{CSS}</style>
</head>
<body>
  <div class="brand-bar">
    <div class="brand">ZAAS<small>Contratos con protección Escrow</small></div>
    <div class="doc-type">
      <strong>{_e(tipo)}</strong>
      Contrato #{contrato.id}<br>
      {_e(estado)}
    </div>
  </div>

  <h1>{_e(objeto)}</h1>
  <p class="muted">
    Documento generado el {_e(datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M'))} UTC
    · Estado del contrato: {_e(estado)}
  </p>

  <section class="resumen">
    <h2>Resumen del acuerdo</h2>
    <table>
      <tr><th>Cliente</th><td>{_e(contrato.cliente.nombre_completo if contrato.cliente else 'No disponible')}</td></tr>
      <tr><th>Desarrollador</th><td>{_e(contrato.desarrollador.nombre_completo if contrato.desarrollador else 'No disponible')}</td></tr>
      <tr><th>Tipo de contrato</th><td>{_e(tipo)}</td></tr>
      <tr><th>Objeto</th><td>{_e(objeto)}</td></tr>
      <tr><th>Costo acordado</th><td>{_e(_dinero(contrato.costo_acordado))} MXN</td></tr>
      <tr><th>Fecha de creación</th><td>{_e(_fecha(contrato.fecha_creacion))}</td></tr>
      <tr><th>Estado Escrow</th><td>{_e(escrow)}</td></tr>
      <tr><th>Plantilla utilizada</th><td>{_e(contrato.plantilla.nombre if contrato.plantilla else 'Plantilla base')}</td></tr>
    </table>
  </section>

  <section class="documento">
    {documento}
  </section>

  <section class="firmas-registro">
    <h2>Registro de firmas</h2>
    <table>
      <thead>
        <tr><th>Parte</th><th>Nombre</th><th>Estado</th><th>Folio de verificación</th></tr>
      </thead>
      <tbody>{firmas_html}</tbody>
    </table>

    <h2>Registro de aceptaciones digitales</h2>
    <table>
      <thead>
        <tr><th>Usuario</th><th>Fecha y hora</th><th>Dirección IP</th></tr>
      </thead>
      <tbody>{aceptaciones_html}</tbody>
    </table>

    <p class="aviso">
      Este documento refleja el estado del contrato al momento de su descarga.
      La versión legalmente vinculante es la copia inmutable de los términos
      guardada por Zaas, junto con el registro de aceptaciones digitales.
    </p>
  </section>
</body>
</html>"""

    return HTML(string=contenido).write_pdf()
