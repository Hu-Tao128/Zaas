// Compartido por los formularios y el observador de Firebase.
// Una petición simultánea con el mismo token reutiliza la promesa en curso.
const pendingByToken = new Map();
let lastRequest = Promise.resolve();

export function syncWithBackend(idToken) {
  if (pendingByToken.has(idToken)) return pendingByToken.get(idToken);
  // Serializar identidades distintas evita que una respuesta antigua reemplace
  // la cookie de sesión de una cuenta que acaba de iniciar sesión.
  const pending = lastRequest.then(async () => {
    const response = await fetch('/auth/callback', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id_token: idToken }),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error(data?.error || 'No se pudo iniciar la sesión en el servidor.');
    if (!data?.user) throw new Error('El servidor no devolvió una sesión válida.');
    return data;
  });
  pendingByToken.set(idToken, pending);
  const cleanup = () => pendingByToken.delete(idToken);
  pending.then(cleanup, cleanup);
  lastRequest = pending.catch(() => {});
  return pending;
}
