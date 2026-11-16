// Cliente de la API JSON de comunicación (`/api/comunicacion`).
// Usa la sesión de Flask-Login creada por /auth/firebase-login.
const BASE = '/api/comunicacion';

let csrfToken = null;

export class ComunicacionApiError extends Error {
  constructor(mensaje, status, errores = {}, codigo = null) {
    super(mensaje);
    this.status = status;
    this.errores = errores || {};
    this.codigo = codigo || null;
  }
}

const CODIGOS_GENERALES = {
  sin_conexion: 'No se pudo conectar con el servidor. Verifica tu conexión e inténtalo de nuevo.',
  no_autenticado: 'Tu sesión no es válida o ha expirado. Inicia sesión nuevamente.',
  sesion_vencida: 'Tu sesión ha expirado. Inicia sesión nuevamente para continuar.',
  permiso_denegado: 'No tienes permiso para realizar esta acción.',
  error_interno: 'Ocurrió un problema al procesar tu solicitud. Inténtalo de nuevo más tarde.',
};

const CODIGOS_INCIDENCIA = {
  incidencia_tipo_invalido: 'Selecciona un tipo de incidencia válido.',
  incidencia_contrato_requerido: 'Debes seleccionar un contrato para este tipo de incidencia.',
  incidencia_contrato_ajeno: 'No tienes acceso al contrato seleccionado.',
  incidencia_detalle_requerido: 'Indica qué tipo de incidencia es cuando eliges "Otro".',
  incidencia_descripcion_invalida: 'La descripción debe tener entre 10 y 1000 caracteres.',
};

function mensajeGenerico(codigo) {
  return CODIGOS_GENERALES[codigo] || 'Ocurrió un problema. Inténtalo de nuevo.';
}

function mensajeSeguro(err) {
  if (!err) return mensajeGenerico('error_interno');
  const codigo = err.codigo;
  if (codigo && CODIGOS_GENERALES[codigo]) return CODIGOS_GENERALES[codigo];
  if (err.status === 401) return CODIGOS_GENERALES.no_autenticado;
  if (err.status === 403) return CODIGOS_GENERALES.permiso_denegado;
  if (err.status === 0) return CODIGOS_GENERALES.sin_conexion;
  if (typeof err.message === 'string' && err.message.trim()) {
    if (/Error del servidor|\(\d{3}\)|undefined|JSON|Traceback/i.test(err.message)) {
      return mensajeGenerico('error_interno');
    }
    return err.message;
  }
  return mensajeGenerico('error_interno');
}

/**
 * Mensaje en lenguaje natural para errores de incidencias.
 * Prioriza el código, usa el mensaje del backend como respaldo y nunca expone detalles técnicos.
 */
export function mensajeErrorIncidencia(err) {
  if (!err) return mensajeGenerico('error_interno');
  const codigo = err.codigo;
  if (codigo && CODIGOS_INCIDENCIA[codigo]) return CODIGOS_INCIDENCIA[codigo];
  return mensajeSeguro(err);
}

async function obtenerCsrf() {
  if (!csrfToken) {
    const respuesta = await fetch(`${BASE}/csrf`, { credentials: 'include' });
    if (!respuesta.ok) {
      throw new ComunicacionApiError('No se pudo iniciar la sesión con el servidor.', respuesta.status, {}, 'error_interno');
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
    throw new ComunicacionApiError('No se pudo conectar con el servidor.', 0, {}, 'sin_conexion');
  }

  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    // Token CSRF caducado: renovar y reintentar una vez.
    if (metodo !== 'GET' && respuesta.status === 400 && !datos.mensaje && !datos.codigo && puedeReintentar) {
      csrfToken = null;
      return peticion(metodo, ruta, cuerpo, false);
    }
    throw new ComunicacionApiError(
      datos.mensaje || 'No se pudo completar la operación.',
      respuesta.status,
      datos.errores || {},
      datos.codigo || null,
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
  incidenciasContratos: () => peticion('GET', '/incidencias/contratos'),
  incidencia: (id) => peticion('GET', `/incidencias/${id}`),
  crearIncidencia: (datos) => peticion('POST', '/incidencias', datos),
  resolverIncidencia: (id, resolucion) =>
    peticion('POST', `/incidencias/${id}/resolver`, { resolucion }),
};
