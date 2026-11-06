import { createUserWithEmailAndPassword, signInWithEmailAndPassword, signInWithPopup, GoogleAuthProvider, signOut, onAuthStateChanged } from 'firebase/auth';
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
  const result = await createUserWithEmailAndPassword(auth, email, password);
  const idToken = await result.user.getIdToken();
  return { user: result.user, idToken };
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
export { syncWithBackend } from './authBackend';
