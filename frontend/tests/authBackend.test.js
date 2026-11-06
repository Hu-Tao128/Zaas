import { afterEach, test } from 'node:test';
import assert from 'node:assert/strict';
import { syncWithBackend } from '../src/services/authBackend.js';

const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });
const ok = id => Response.json({ user: { id, email: 'prueba@example.com' } });

test('formulario y observador comparten una sola petición simultánea', async () => {
  let calls = 0;
  let complete;
  globalThis.fetch = async (url, options) => {
    calls++;
    assert.equal(url, '/auth/callback');
    assert.equal(options.credentials, 'include');
    assert.deepEqual(JSON.parse(options.body), { id_token: 'same-token' });
    return new Promise(resolve => { complete = resolve; });
  };
  const fromForm = syncWithBackend('same-token');
  const fromObserver = syncWithBackend('same-token');
  assert.equal(fromForm, fromObserver);
  await Promise.resolve();
  complete(ok(1));
  const results = await Promise.all([fromForm, fromObserver]);
  assert.equal(calls, 1);
  assert.equal(results[0].user.id, 1);
});

test('un fallo se muestra a ambos consumidores y permite un reintento posterior', async () => {
  let calls = 0;
  globalThis.fetch = async () => {
    calls++;
    return calls === 1 ? Response.json({ error: 'No se pudo sincronizar.' }, { status: 409 }) : ok(2);
  };
  const first = syncWithBackend('retry-token');
  const second = syncWithBackend('retry-token');
  const results = await Promise.allSettled([first, second]);
  assert.equal(results[0].status, 'rejected');
  assert.equal(results[1].status, 'rejected');
  assert.match(results[0].reason.message, /No se pudo sincronizar/);
  assert.equal((await syncWithBackend('retry-token')).user.id, 2);
  assert.equal(calls, 2);
});

test('al cambiar de cuenta la segunda sesión se sincroniza después de la primera', async () => {
  const calls = [];
  let complete;
  globalThis.fetch = async (url, options) => {
    const token = JSON.parse(options.body).id_token;
    calls.push(token);
    if (token === 'old-account') return new Promise(resolve => { complete = resolve; });
    return ok(3);
  };
  const oldSession = syncWithBackend('old-account');
  const newSession = syncWithBackend('new-account');
  await Promise.resolve();
  assert.deepEqual(calls, ['old-account']);
  complete(ok(1));
  await Promise.all([oldSession, newSession]);
  assert.deepEqual(calls, ['old-account', 'new-account']);
});

test('una respuesta HTML no se acepta como una sesión exitosa', async () => {
  globalThis.fetch = async () => new Response('<html>Error</html>', { status: 500 });
  await assert.rejects(syncWithBackend('html-token'), /No se pudo iniciar/);
});
