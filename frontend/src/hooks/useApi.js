import { useCallback, useEffect, useState } from 'react';

/**
 * Ejecuta `cargar()` (una llamada a catalogoApi) cuando cambian las dependencias.
 * Si `cargar` es null no hace nada (útil para formularios de "crear" que no necesitan datos).
 * Devuelve { data, error, loading, recargar }.
 */
export function useApi(cargar, dependencias) {
  const [estado, setEstado] = useState({ data: null, error: null, loading: Boolean(cargar) });
  const [version, setVersion] = useState(0);

  useEffect(() => {
    if (!cargar) {
      setEstado({ data: null, error: null, loading: false });
      return undefined;
    }
    let vigente = true;
    setEstado((actual) => ({ ...actual, loading: true, error: null }));
    cargar()
      .then((data) => { if (vigente) setEstado({ data, error: null, loading: false }); })
      .catch((error) => { if (vigente) setEstado({ data: null, error, loading: false }); });
    return () => { vigente = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencias, version]);

  const recargar = useCallback(() => setVersion((v) => v + 1), []);
  return { ...estado, recargar };
}
