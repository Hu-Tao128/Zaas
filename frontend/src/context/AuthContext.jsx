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
  const syncEnCurso = useRef(null);

  // Sincroniza el usuario de Firebase con la sesión (cookie) de Flask.
  // Deduplica llamadas concurrentes: onAuthStateChanged y el login manual
  // pueden dispararse al mismo tiempo y provocar altas duplicadas/integrity errors.
  const sincronizar = useCallback((firebaseUser, forzarToken = false) => {
    if (!firebaseUser) return Promise.resolve(null);
    if (syncEnCurso.current) return syncEnCurso.current;

    const promesa = (async () => {
      const idToken = await firebaseUser.getIdToken(forzarToken);
      return syncWithBackend(idToken);
    })().finally(() => {
      syncEnCurso.current = null;
    });

    syncEnCurso.current = promesa;
    return promesa;
  }, []);

  useEffect(() => {
    const unsubscribe = onAuthChange(async (firebaseUser) => {
      if (firebaseUser) {
        // La autenticación con Firebase es la fuente de verdad para el guard de rutas.
        setUser(firebaseUser);
        try {
          await sincronizar(firebaseUser);
        } catch (error) {
          // Si el backend no responde, el usuario sigue autenticado en Firebase
          // y CatalogoProvider reintentará crear la sesión (cookie) más adelante.
          console.error('Error syncing with backend:', error);
        }
      } else {
        setUser(null);
      }
      setLoading(false);
    });

    return () => unsubscribe();
  }, [sincronizar]);

  // Permite a Login/Registro marcar la sesión como activa en cuanto Firebase
  // confirma el acceso, evitando el rebote a /login por una condición de carrera.
  const marcarAutenticado = useCallback((firebaseUser) => {
    if (firebaseUser) setUser(firebaseUser);
    setLoading(false);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, sincronizar, marcarAutenticado }}>
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
