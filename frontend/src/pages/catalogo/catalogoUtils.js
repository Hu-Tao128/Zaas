export function formatFecha(valor) {
  if (!valor) return '';
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(new Date(valor));
}

export function formatFechaHora(valor) {
  if (!valor) return '';
  return new Intl.DateTimeFormat('es-ES', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(valor));
}

export function formatDinero(valor) {
  return `$${new Intl.NumberFormat('es-MX', { maximumFractionDigits: 2 }).format(Number(valor))}`;
}

export function recortar(texto, limite) {
  const contenido = texto || '';
  return contenido.length > limite ? `${contenido.slice(0, limite)}...` : contenido;
}

export function fechaMinimaLocal() {
  const ahora = new Date();
  ahora.setMinutes(ahora.getMinutes() - ahora.getTimezoneOffset() + 1);
  return ahora.toISOString().slice(0, 16);
}

// El módulo de contratos sigue en Flask: se enlaza con una navegación normal (no con <Link>).
// Ajusta la ruta base si tu blueprint de contratos usa otra.
const CONTRATOS_NUEVO = '/contratos/nuevo';

export function urlContratarProyecto(proyecto) {
  const params = new URLSearchParams({
    id_producto: proyecto.id,
    id_desarrollador: proyecto.id_usuario,
  });
  return `${CONTRATOS_NUEVO}?${params}`;
}

export function urlContratarPostulacion(postulacion) {
  const params = new URLSearchParams({
    id_cliente: postulacion.oferta.id_cliente,
    id_desarrollador: postulacion.id_desarrollador,
    id_encargo: postulacion.oferta.id,
    costo_acordado: postulacion.costo_propuesto,
  });
  return `${CONTRATOS_NUEVO}?${params}`;
}
