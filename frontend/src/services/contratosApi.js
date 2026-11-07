// Cliente de la API JSON de Contratos Escrow (`/contratos/api`).
// Usa la sesión de Flask-Login creada por /auth/callback y el token CSRF de Flask-WTF.
const BASE = '/contratos/api';

let csrfToken = null;

export class ContratoApiError extends Error {
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
      throw new ContratoApiError('No se pudo iniciar la sesión con el servidor.', respuesta.status);
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
    throw new ContratoApiError('No se pudo conectar con el servidor.', 0);
  }

  const datos = await respuesta.json().catch(() => ({}));

  if (!respuesta.ok) {
    // El token CSRF pudo caducar: renovarlo y reintentar una vez.
    if (metodo !== 'GET' && respuesta.status === 400 && puedeReintentar && !datos.mensaje) {
      csrfToken = null;
      return peticion(metodo, ruta, cuerpo, false);
    }
    throw new ContratoApiError(
      datos.mensaje || `Error del servidor (${respuesta.status}).`,
      respuesta.status,
      datos.errores || {},
    );
  }

  return datos;
}

export const contratosApi = {
  opciones: () => peticion('GET', '/opciones'),
  listar: ({ estado } = {}) => {
    const params = new URLSearchParams();
    if (estado) params.set('estado', estado);
    const query = params.toString();
    return peticion('GET', query ? `/?${query}` : '/');
  },
  detalle: (id) => peticion('GET', `/${id}`),
  crear: (datos) => peticion('POST', '/crear', datos),
  aceptar: (id) => peticion('POST', `/${id}/aceptar`, { acepto: true }),
  cancelar: (id) => peticion('POST', `/${id}/cancelar`, { confirmar: true }),
};
