// Cliente de la API del agente conversacional (`/api/agente`).
// Usa la sesión de Flask-Login creada por /auth/firebase-login y el token CSRF
// de Flask-WTF, igual que el resto de APIs JSON del proyecto.
const BASE = '/api/agente';

let csrfToken = null;

export class AgenteApiError extends Error {
  constructor(mensaje, status = 0) {
    super(mensaje);
    this.status = status;
  }
}

export async function obtenerSesionAgente() {
  const respuesta = await fetch(`${BASE}/sesion`, { credentials: 'include' });
  const datos = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    throw new AgenteApiError(datos?.error || 'No se pudo iniciar sesión con el agente.', respuesta.status);
  }
  csrfToken = datos.csrf_token;
  return datos;
}

export async function enviarMensaje(mensaje) {
  if (!csrfToken) await obtenerSesionAgente();

  let respuesta;
  try {
    respuesta = await fetch(`${BASE}/chat`, {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken,
      },
      body: JSON.stringify({ mensaje }),
    });
  } catch {
    throw new AgenteApiError('No se pudo conectar con el servidor.', 0);
  }

  const datos = await respuesta.json().catch(() => null);
  if (!respuesta.ok) {
    throw new AgenteApiError(datos?.error || 'El agente no pudo responder.', respuesta.status);
  }
  return datos;
}
