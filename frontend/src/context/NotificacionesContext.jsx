import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { useAuth } from './AuthContext';
import { comunicacionApi } from '../services/comunicacionApi';

const NotificacionesContext = createContext(null);

export function NotificacionesProvider({ children }) {
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [noLeidas, setNoLeidas] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const enCurso = useRef(new Set());

  useEffect(() => {
    if (!user) {
      setItems([]);
      setNoLeidas(0);
      setLoading(false);
      setError('');
    }
  }, [user]);

  const cargar = useCallback(async ({ silencioso = false } = {}) => {
    if (!silencioso) setLoading(true);
    setError('');
    try {
      const { items: lista, no_leidas } = await comunicacionApi.notificaciones(1, false);
      setItems(lista || []);
      setNoLeidas(no_leidas || 0);
      return true;
    } catch {
      setError('No se pudieron cargar las notificaciones.');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  const marcarLeida = useCallback(async (notificacion) => {
    if (!notificacion || notificacion.leido) return true;

    const id = notificacion.id;
    if (enCurso.current.has(id)) return true;
    enCurso.current.add(id);

    setItems((prev) => prev.map((item) => (
      item.id === id ? { ...item, leido: true } : item
    )));
    setNoLeidas((prev) => Math.max(0, prev - 1));

    try {
      await comunicacionApi.marcarNotificacionLeida(id);
      return true;
    } catch {
      await cargar({ silencioso: true });
      return false;
    } finally {
      enCurso.current.delete(id);
    }
  }, [cargar]);

  const marcarTodas = useCallback(async () => {
    setItems((prev) => prev.map((item) => ({ ...item, leido: true })));
    setNoLeidas(0);

    try {
      await comunicacionApi.marcarNotificacionesLeidas();
      return true;
    } catch {
      await cargar({ silencioso: true });
      return false;
    }
  }, [cargar]);

  const value = useMemo(() => ({
    notificaciones: items,
    noLeidas,
    loading,
    error,
    cargar,
    marcarLeida,
    marcarTodas,
  }), [items, noLeidas, loading, error, cargar, marcarLeida, marcarTodas]);

  return (
    <NotificacionesContext.Provider value={value}>
      {children}
    </NotificacionesContext.Provider>
  );
}

export function useNotificaciones() {
  const context = useContext(NotificacionesContext);
  if (!context) {
    throw new Error('useNotificaciones debe usarse dentro de NotificacionesProvider');
  }
  return context;
}
