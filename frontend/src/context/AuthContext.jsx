import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
  useEffect,
} from 'react';
import { onAuthChange, syncWithBackend } from '../services/authService';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const registroEnCurso = useRef(false);
  const version = useRef(0);

  // Sincroniza el usuario de Firebase con la sesión (cookie) de Flask.
  // Deduplica llamadas concurrentes: onAuthStateChanged y el login manual
  // pueden dispararse al mismo tiempo y provocar altas duplicadas/integrity errors.
  const sincronizar = useCallback(async (firebaseUser, forzarToken = false) => {
    if (!firebaseUser) return null;
    return syncWithBackend(await firebaseUser.getIdToken(forzarToken));
  }, []);

  const iniciarRegistro = useCallback(() => {
    registroEnCurso.current = true;
    version.current++;
    setUser(null);
    setLoading(false);
  }, []);

  const finalizarRegistro = useCallback(() => {
    registroEnCurso.current = false;
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthChange(async (firebaseUser) => {
      const actual = ++version.current;
      if (registroEnCurso.current) return;
      setLoading(true);
      setUser(firebaseUser);
      if (firebaseUser) {
        try {
          const token = await firebaseUser.getIdToken();
          if (actual !== version.current || registroEnCurso.current) return;
          await syncWithBackend(token);
        } catch (error) {
          // Si el backend no responde, el usuario sigue autenticado en Firebase
          // y CatalogoProvider reintentará crear la sesión (cookie) más adelante.
          console.error('Error syncing with backend:', error);
        }
      }
      if (actual === version.current) setLoading(false);
    });

    return () => { version.current++; unsubscribe(); };
  }, []);

  // Permite a Login/Registro marcar la sesión como activa en cuanto Firebase
  // confirma el acceso, evitando el rebote a /login por una condición de carrera.
  const marcarAutenticado = useCallback((firebaseUser) => {
    registroEnCurso.current = false;
    version.current++;
    if (firebaseUser) setUser(firebaseUser);
    setLoading(false);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, sincronizar, marcarAutenticado, iniciarRegistro, finalizarRegistro }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}
