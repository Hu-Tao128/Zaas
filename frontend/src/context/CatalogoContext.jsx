import { createContext, useContext, useEffect, useState } from 'react';
import { catalogoApi } from '../services/catalogoApi';
import { Cargando, ErrorCard } from '../components/catalogo/CatalogoUI';

const CatalogoContext = createContext(null);

/**
 * Carga una sola vez el usuario del backend (id, nombre, rol) y las opciones de
 * categorías/tecnologías. El resto de datos los pide cada página a catalogoApi.
 */
export function CatalogoProvider({ children }) {
  const [estado, setEstado] = useState({ cargando: true, error: null, valor: null });

  useEffect(() => {
    let vigente = true;
    Promise.all([catalogoApi.me(), catalogoApi.opciones()])
      .then(([sesion, opciones]) => {
        if (!vigente) return;
        setEstado({
          cargando: false,
          error: null,
          valor: {
            usuario: sesion.usuario,
            categorias: opciones.categorias,
            tecnologias: opciones.tecnologias,
          },
        });
      })
      .catch((error) => { if (vigente) setEstado({ cargando: false, error, valor: null }); });
    return () => { vigente = false; };
  }, []);

  if (estado.cargando) return <Cargando />;
  if (estado.error) {
    const sinSesion = estado.error.status === 401;
    return (
      <ErrorCard
        error={sinSesion ? new Error('El servidor no reconoce tu sesión. Vuelve a iniciar sesión.') : estado.error}
        volverA="/login"
        volverTexto="Ir a iniciar sesión"
      />
    );
  }
  return <CatalogoContext.Provider value={estado.valor}>{children}</CatalogoContext.Provider>;
}

export function useCatalogo() {
  const context = useContext(CatalogoContext);
  if (!context) throw new Error('useCatalogo debe usarse dentro de CatalogoProvider');
  return context;
}
