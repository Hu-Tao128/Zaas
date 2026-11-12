// Cliente de la API JSON de Pagos (`/pagos/api`).
const BASE = '/pagos/api';

let csrfToken = null;

export class PagoApiError extends Error {
  constructor(mensaje, status, errores = {}) {
    super(mensaje);
    this.status = status;
    this.errores = errores;
  }
}

async function obtenerCsrf() {
  if (!csrfToken) {
    const respuesta = await fetch(`${BASE}/csrf`, { credentials: 'include' });
    if (!respuesta.ok) {
      throw new PagoApiError('No se pudo iniciar la sesión con el servidor.', respuesta.status);
    }
    csrfToken = (await respuesta.json()).csrf_token;
  }
  return csrfToken;
}

async function peticion(metodo, ruta, cuerpo, puedeReintentar = true) {
  const opciones = { method: metodo, credentials: 'include', headers: {} };

  if (metodo !== 'GET') {
    opciones.headers['Content-Type'] = 'application/json';
    opciones.headers['X-CSRFToken'] = await obtenerCsrf();
    opciones.body = JSON.stringify(cuerpo ?? {});
  }

  let respuesta;
  try {
    respuesta = await fetch(`${BASE}${ruta}`, opciones);
  } catch {
    throw new PagoApiError('No se pudo conectar con el servidor.', 0);
  }

  const datos = await respuesta.json().catch(() => ({}));

  if (!respuesta.ok) {
    if (metodo !== 'GET' && respuesta.status === 400 && puedeReintentar && !datos.mensaje) {
      csrfToken = null;
      return peticion(metodo, ruta, cuerpo, false);
    }
    throw new PagoApiError(
      datos.mensaje || `Error del servidor (${respuesta.status}).`,
      respuesta.status,
      datos.errores || {},
    );
  }

  return datos;
}

export const pagosApi = {
  csrf: () => peticion('GET', '/csrf'),
  listarPorContrato: (idContrato) => peticion('GET', `/contrato/${idContrato}`),
  obtener: (id) => peticion('GET', `/${id}`),
  crear: (datos) => peticion('POST', '/crear', datos),

  liberaciones: (idPago) => peticion('GET', `/pagos/${idPago}/liberaciones`),
  crearLiberacion: (datos) => peticion('POST', '/liberaciones/crear', datos),

  recibo: (idPago) => peticion('GET', `/pagos/${idPago}/recibo`),

  disputas: () => peticion('GET', '/disputas'),
  obtenerDisputa: (id) => peticion('GET', `/disputas/${id}`),
  crearDisputa: (datos) => peticion('POST', '/disputas/crear', datos),

  crearArbitraje: (idDisputa, datos) => peticion('POST', `/disputas/${idDisputa}/arbitraje`, datos),
  obtenerArbitraje: (id) => peticion('GET', `/disputas/${id}/arbitraje`),
};
