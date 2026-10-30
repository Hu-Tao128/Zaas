import { signInWithEmailAndPassword, signInWithPopup, GoogleAuthProvider, signOut, onAuthStateChanged } from 'firebase/auth';
import { auth, analytics } from '../firebase';
import { logEvent } from 'firebase/analytics';

const googleProvider = new GoogleAuthProvider();

/**
 * Login con email y contraseña
 */
export async function loginWithEmail(email, password) {
  const result = await signInWithEmailAndPassword(auth, email, password);
  const idToken = await result.user.getIdToken();
  
  // Log Analytics
  if (analytics) {
    logEvent(analytics, 'login', { method: 'email' });
  }
  
  return { user: result.user, idToken };
}

/**
 * Login con Google
 */
export async function loginWithGoogle() {
  const result = await signInWithPopup(auth, googleProvider);
  const idToken = await result.user.getIdToken();
  
  // Log Analytics
  if (analytics) {
    logEvent(analytics, 'login', { method: 'google' });
  }
  
  return { user: result.user, idToken };
}

/**
 * Registro con email y contraseña
 */
export async function registerWithEmail(email, password) {
  // El registro se maneja con loginWithEmail ya que Firebase crea el usuario
  return await loginWithEmail(email, password);
}

/**
 * Logout
 */
export async function logout() {
  if (analytics) {
    logEvent(analytics, 'logout');
  }
  await signOut(auth);
}

/**
 * Suscribirse a cambios de autenticación
 */
export function onAuthChange(callback) {
  return onAuthStateChanged(auth, callback);
}

/**
 * Enviar token al backend para crear sesión
 */
export async function syncWithBackend(idToken) {
  const response = await fetch('/auth/callback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token: idToken })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Error de autenticación');
  }
  
  return await response.json();
}
