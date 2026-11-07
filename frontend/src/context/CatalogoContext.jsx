import { createContext, useContext, useEffect, useState } from 'react';
import { auth } from '../firebase';
import { syncWithBackend } from '../services/authService';
import { catalogoApi } from '../services/catalogoApi';
import { Cargando, ErrorCard } from '../components/catalogo/CatalogoUI';

const CatalogoContext = createContext(null);

/**
 * Carga una sola vez el usuario del backend (id, nombre, rol) y las opciones de
 * categorías/tecnologías. El resto de datos los pide cada página a catalogoApi.
 *
 * Si el backend responde 401 (por ejemplo, porque la cookie de sesión de Flask
 * se perdió pero Firebase sigue autenticado), se re-sincroniza la sesión con
 * el idToken actual y se reintenta una vez.
 */
export function CatalogoProvider({ children }) {
  const [estado, setEstado] = useState({ cargando: true, error: null, valor: null });

  useEffect(() => {
    let vigente = true;

    async function cargarDatos(reintento = false) {
      try {
        const [sesion, opciones] = await Promise.all([
          catalogoApi.me(),
          catalogoApi.opciones(),
        ]);
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
      } catch (error) {
        if (!vigente) return;

        // La cookie de sesión desapareció: recrearla con el token de Firebase.
        if (error.status === 401 && !reintento && auth.currentUser) {
          try {
            const idToken = await auth.currentUser.getIdToken(true);
            await syncWithBackend(idToken);
            if (vigente) return cargarDatos(true);
            return;
          } catch (syncError) {
            console.error('No se pudo restablecer la sesión del servidor:', syncError);
          }
        }

        if (vigente) setEstado({ cargando: false, error, valor: null });
      }
    }

    cargarDatos();
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
