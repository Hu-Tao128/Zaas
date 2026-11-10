// Cliente de la API JSON de comunicación (`/api/comunicacion`).
// Usa la sesión de Flask-Login creada por /auth/firebase-login.
const BASE = '/api/comunicacion';

let csrfToken = null;

export class ComunicacionApiError extends Error {
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
      throw new ComunicacionApiError('No se pudo iniciar la sesión con el servidor.', respuesta.status);
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
    throw new ComunicacionApiError('No se pudo conectar con el servidor.', 0);
  }

  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    // Token CSRF caducado: renovar y reintentar una vez.
    if (metodo !== 'GET' && respuesta.status === 400 && !datos.mensaje && puedeReintentar) {
      csrfToken = null;
      return peticion(metodo, ruta, cuerpo, false);
    }
    throw new ComunicacionApiError(
      datos.mensaje || `Error del servidor (${respuesta.status}).`,
      respuesta.status,
      datos.errores || {},
    );
  }
  return datos;
}

export const comunicacionApi = {
  notificaciones: () => peticion('GET', '/notificaciones'),
  marcarNotificacionesLeidas: () => peticion('POST', '/notificaciones/leer', {}),

  conversaciones: () => peticion('GET', '/conversaciones'),
  chat: (idContrato) => peticion('GET', `/contrato/${idContrato}`),
  enviarMensaje: (idContrato, contenido) =>
    peticion('POST', `/contrato/${idContrato}`, { contenido }),

  calificar: (idContrato, datos) =>
    peticion('POST', `/contrato/${idContrato}/calificar`, datos),

  incidencias: () => peticion('GET', '/incidencias'),
  incidencia: (id) => peticion('GET', `/incidencias/${id}`),
  crearIncidencia: (datos) => peticion('POST', '/incidencias', datos),
  resolverIncidencia: (id, resolucion) =>
    peticion('POST', `/incidencias/${id}/resolver`, { resolucion }),
};
