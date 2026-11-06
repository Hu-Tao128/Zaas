import { afterEach, test } from 'node:test';
import assert from 'node:assert/strict';
import { consultar, guardar } from '../src/services/comunicacionService.js';

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });

test('las consultas usan la sesión y devuelven el JSON de la API', async () => {
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/comunicacion/notificaciones');
    assert.equal(options.credentials, 'include');
    return Response.json({ data: [], no_leidas: 0 });
  };
  assert.equal((await consultar('/notificaciones')).no_leidas, 0);
});

test('las escrituras piden CSRF de la sesión actual antes de enviar el contenido', async () => {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push(url);
    if (url.endsWith('/sesion')) return Response.json({ csrf_token: 'token-actual' });
    assert.equal(options.method, 'PATCH');
    assert.equal(options.headers['X-CSRFToken'], 'token-actual');
    assert.equal(options.headers['Content-Type'], 'application/json');
    assert.equal(options.body, JSON.stringify({ leido: true }));
    return Response.json({ data: { id: 2 } });
  };
  assert.equal((await guardar('/notificaciones/2/leer', { leido: true }, 'PATCH')).data.id, 2);
  assert.deepEqual(calls, ['/api/comunicacion/sesion', '/api/comunicacion/notificaciones/2/leer']);
});

test('muestra el rechazo del servidor y no sigue escribiendo sin sesión', async () => {
  let count = 0;
  globalThis.fetch = async () => {
    count++;
    return Response.json({ error: 'Debes iniciar sesión.' }, { status: 401 });
  };
  await assert.rejects(guardar('/incidencias', {}), /Debes iniciar sesión/);
  assert.equal(count, 1);
});

test('maneja errores HTML y rechazos de validación sin presentar éxito', async () => {
  globalThis.fetch = async () => new Response('<html>Error</html>', { status: 500 });
  await assert.rejects(consultar('/notificaciones'), /500/);
  globalThis.fetch = async () => Response.json({ error: 'Ya calificaste este contrato.' }, { status: 409 });
  await assert.rejects(consultar('/calificaciones'), /Ya calificaste/);
});
