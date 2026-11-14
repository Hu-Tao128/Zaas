// Cliente de la API JSON de Pagos (`/pagos/api`).
const BASE = '/pagos/api';

let csrfToken = null;

export class PagoApiError extends Error {
  constructor(mensaje, status, errores = {}, codigo = null) {
    super(mensaje);
    this.status = status;
    this.errores = errores || {};
    this.codigo = codigo || null;
  }
}

async function obtenerCsrf() {
  if (!csrfToken) {
    const respuesta = await fetch(`${BASE}/csrf`, { credentials: 'include' });
    if (!respuesta.ok) {
      throw new PagoApiError('No se pudo iniciar la sesión con el servidor.', respuesta.status, {}, 'error_interno');
    }
    csrfToken = (await respuesta.json()).csrf_token;
  }
  return csrfToken;
}

async function peticion(metodo, ruta, cuerpo, puedeReintentar = true, headersExtra = {}) {
  const opciones = { method: metodo, credentials: 'include', headers: { ...headersExtra } };

  if (metodo !== 'GET') {
    opciones.headers['Content-Type'] = 'application/json';
    opciones.headers['X-CSRFToken'] = await obtenerCsrf();
    opciones.body = JSON.stringify(cuerpo ?? {});
  }

  let respuesta;
  try {
    respuesta = await fetch(`${BASE}${ruta}`, opciones);
  } catch {
    throw new PagoApiError('No se pudo conectar con el servidor.', 0, {}, 'sin_conexion');
  }

  const datos = await respuesta.json().catch(() => ({}));

  if (!respuesta.ok) {
    if (metodo !== 'GET' && respuesta.status === 400 && puedeReintentar && !datos.mensaje && !datos.codigo) {
      csrfToken = null;
      return peticion(metodo, ruta, cuerpo, false);
    }
    throw new PagoApiError(
      datos.mensaje || 'No se pudo completar la operación.',
      respuesta.status,
      datos.errores || {},
      datos.codigo || null,
    );
  }

  return datos;
}

export const pagosApi = {
  csrf: () => peticion('GET', '/csrf'),
  listarPorContrato: (idContrato) => peticion('GET', `/contrato/${idContrato}`),
  resumenContrato: (idContrato) => peticion('GET', `/contrato/${idContrato}/resumen`),
  obtener: (id) => peticion('GET', `/${id}`),
  crear: (datos, idempotencyKey) => peticion('POST', '/crear', datos, true, idempotencyKey ? { 'Idempotency-Key': idempotencyKey } : {}),
  verificar: (id, codigo) => peticion('POST', `/pagos/${id}/verificar`, { codigo }),

  liberaciones: (idPago) => peticion('GET', `/pagos/${idPago}/liberaciones`),
  crearLiberacion: (datos) => peticion('POST', '/liberaciones/crear', datos),

  recibo: (idPago) => peticion('GET', `/pagos/${idPago}/recibo`),

  disputas: () => peticion('GET', '/disputas'),
  obtenerDisputa: (id) => peticion('GET', `/disputas/${id}`),
  crearDisputa: (datos) => peticion('POST', '/disputas/crear', datos),

  crearArbitraje: (idDisputa, datos) => peticion('POST', `/disputas/${idDisputa}/arbitraje`, datos),
  obtenerArbitraje: (id) => peticion('GET', `/disputas/${id}/arbitraje`),
};
