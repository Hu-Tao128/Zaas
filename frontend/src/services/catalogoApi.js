// Cliente de la API JSON del catálogo (blueprint /api/catalogo del backend Flask).
// Usa la sesión de Flask-Login (cookie) creada por /auth/callback y el token CSRF de Flask-WTF.
const BASE = '/api/catalogo';

let csrfToken = null;

export class ApiError extends Error {
  constructor(mensaje, status, errores = {}) {
    super(mensaje);
    this.status = status;
    this.errores = errores;
  }
}

async function obtenerCsrf() {
  if (!csrfToken) {
    const respuesta = await fetch(`${BASE}/csrf`, { credentials: 'include' });
    if (!respuesta.ok) throw new ApiError('No se pudo iniciar la sesión con el servidor.', respuesta.status);
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
    throw new ApiError('No se pudo conectar con el servidor.', 0);
  }
  const datos = await respuesta.json().catch(() => ({}));

  if (!respuesta.ok) {
    // Flask-WTF rechaza un CSRF caducado con un 400 que no es JSON: pedimos token nuevo y reintentamos una vez.
    if (metodo !== 'GET' && respuesta.status === 400 && !datos.mensaje && puedeReintentar) {
      csrfToken = null;
      return peticion(metodo, ruta, cuerpo, false);
    }
    throw new ApiError(datos.mensaje || `Error del servidor (${respuesta.status}).`, respuesta.status, datos.errores || {});
  }
  return datos;
}

function consulta(parametros) {
  const params = new URLSearchParams();
  Object.entries(parametros).forEach(([clave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== '') params.set(clave, String(valor));
  });
  const texto = params.toString();
  return texto ? `?${texto}` : '';
}

const get = (ruta) => peticion('GET', ruta);
const post = (ruta, cuerpo) => peticion('POST', ruta, cuerpo);
const put = (ruta, cuerpo) => peticion('PUT', ruta, cuerpo);

export const catalogoApi = {
  me: () => get('/me'),
  opciones: () => get('/opciones'),

  proyectos: ({ page, q, categoria } = {}) => get(`/proyectos${consulta({ page, q, categoria })}`),
  proyecto: (id) => get(`/proyectos/${id}`),
  misProductos: () => get('/mis-productos'),
  crearProyecto: (datos) => post('/proyectos', datos),
  editarProyecto: (id, datos) => put(`/proyectos/${id}`, datos),
  cerrarProyecto: (id) => post(`/proyectos/${id}/cerrar`),
  solicitarDemo: (id, datos) => post(`/proyectos/${id}/demo`, datos),

  ofertas: ({ page } = {}) => get(`/ofertas${consulta({ page })}`),
  oferta: (id) => get(`/ofertas/${id}`),
  misOfertas: () => get('/mis-ofertas'),
  crearOferta: (datos) => post('/ofertas', datos),
  cerrarOferta: (id) => post(`/ofertas/${id}/cerrar`),

  postular: (idOferta, datos) => post(`/ofertas/${idOferta}/postular`, datos),
  misPostulaciones: () => get('/mis-postulaciones'),
  postulacion: (id) => get(`/postulaciones/${id}`),
  aceptarPostulacion: (id) => post(`/postulaciones/${id}/aceptar`),
  rechazarPostulacion: (id) => post(`/postulaciones/${id}/rechazar`),
};
