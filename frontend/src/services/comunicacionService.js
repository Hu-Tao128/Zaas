const BASE = '/api/comunicacion';

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    ...options,
    headers: { Accept: 'application/json', ...options.headers },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.error || `No se pudo completar la solicitud (${response.status}).`);
  }
  if (!body) throw new Error('El servidor no devolvió una respuesta válida.');
  return body;
}

export function consultar(path) {
  return request(path);
}

export async function guardar(path, data, method = 'POST') {
  // Obtener el token de la sesión actual evita reutilizarlo al cambiar de cuenta.
  const { csrf_token } = await request('/sesion');
  return request(path, {
    method,
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf_token },
    body: JSON.stringify(data ?? {}),
  });
}
