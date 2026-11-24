import { useEffect, useRef } from 'react';
import './pagos.css';

// Pila de modales abiertos (el último es el de más arriba) y control de bloqueo
// de scroll para que varios modales apilados no dejen el fondo bloqueado de más.
const pilaModales = [];
const registros = new Map();
let bloqueosScroll = 0;
let overflowAnterior = '';

/**
 * Modal compartido de las pantallas de pagos.
 *
 * - Solo el modal superior procesa las solicitudes de cierre por teclado.
 * - Mientras `procesando` sea verdadero, el cierre no hace nada.
 * - Foco inicial dentro del modal, Tab atrapado y restauración al cerrar.
 * - Bloquea el scroll de la página de fondo.
 * - El clic en el fondo solo cierra los modales informativos (`cerrarEnFondo`).
 * - Una única "X" visible; los formularios pueden añadir "Cancelar" en el pie.
 */
export default function ModalPagos({
  abierto,
  titulo,
  onCerrar,
  children,
  pie = null,
  mostrarCancelar = false,
  cerrarEnFondo = false,
  procesando = false,
  ancho = 560,
}) {
  const idRef = useRef(null);
  if (idRef.current === null) {
    idRef.current = `modal-${Math.random().toString(36).slice(2)}`;
  }
  const tituloId = `${idRef.current}-titulo`;
  const panelRef = useRef(null);
  const restaurarEnRef = useRef(null);
  const estadoRef = useRef({ onCerrar, cerrarEnFondo, procesando });
  estadoRef.current = { onCerrar, cerrarEnFondo, procesando };

  useEffect(() => {
    if (!abierto) return undefined;

    restaurarEnRef.current = document.activeElement;
    pilaModales.push(idRef.current);
    registros.set(idRef.current, { estadoRef });

    const manejarTeclado = (e) => {
      if (e.key !== 'Escape') return;
      const superiorId = pilaModales[pilaModales.length - 1];
      // Solo el modal de más arriba reacciona; los de abajo ignoran la tecla.
      if (superiorId !== idRef.current) return;
      e.stopPropagation();
      const registro = registros.get(superiorId);
      if (!registro) return;
      const estado = registro.estadoRef.current;
      if (estado.procesando) return;
      estado.onCerrar();
    };
    document.addEventListener('keydown', manejarTeclado, true);

    if (bloqueosScroll === 0) {
      overflowAnterior = document.body.style.overflow || '';
      document.body.style.overflow = 'hidden';
    }
    bloqueosScroll += 1;

    const panel = panelRef.current;
    if (panel) {
      const primerFoco = panel.querySelector(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      (primerFoco || panel).focus();
    }

    return () => {
      document.removeEventListener('keydown', manejarTeclado, true);
      const indice = pilaModales.lastIndexOf(idRef.current);
      if (indice >= 0) pilaModales.splice(indice, 1);
      registros.delete(idRef.current);
      bloqueosScroll = Math.max(0, bloqueosScroll - 1);
      if (bloqueosScroll === 0) {
        document.body.style.overflow = overflowAnterior;
      }
      const restaurar = restaurarEnRef.current;
      if (restaurar && typeof restaurar.focus === 'function') restaurar.focus();
      restaurarEnRef.current = null;
    };
  }, [abierto]);

  if (!abierto) return null;

  const estado = estadoRef.current;
  const cerrar = () => {
    if (estado.procesando) return;
    estado.onCerrar();
  };

  function manejarTab(e) {
    if (e.key !== 'Tab') return;
    const panel = panelRef.current;
    if (!panel) return;
    const focalizables = Array.from(
      panel.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ).filter((el) => el.getClientRects().length > 0);
    if (focalizables.length === 0) {
      e.preventDefault();
      return;
    }
    const primero = focalizables[0];
    const ultimo = focalizables[focalizables.length - 1];
    if (document.activeElement === panel) {
      e.preventDefault();
      (e.shiftKey ? ultimo : primero).focus();
      return;
    }
    if (e.shiftKey && document.activeElement === primero) {
      e.preventDefault();
      ultimo.focus();
    } else if (!e.shiftKey && document.activeElement === ultimo) {
      e.preventDefault();
      primero.focus();
    }
  }

  return (
    <div
      className="pagos-modal-fondo"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1200,
        background: 'rgba(15,23,42,.45)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        padding: '4vh 1rem',
        overflowY: 'auto',
      }}
      onClick={() => {
        if (estadoRef.current.cerrarEnFondo && !estadoRef.current.procesando) {
          estadoRef.current.onCerrar();
        }
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={tituloId}
        tabIndex={-1}
        className="card pagos-modal-panel"
        style={{
          width: '100%',
          maxWidth: ancho,
          margin: 'auto 0',
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
          outline: 'none',
        }}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={manejarTab}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '1rem',
            paddingBottom: '.75rem',
            borderBottom: '1px solid var(--zaas-border)',
          }}
        >
          <h2 id={tituloId} className="contrato-form-title" style={{ margin: 0, fontSize: '1.2rem' }}>
            {titulo}
          </h2>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            aria-label="Cerrar"
            disabled={estado.procesando}
            onClick={cerrar}
          >
            ✕
          </button>
        </div>

        <div style={{ overflowY: 'auto', paddingTop: '1rem' }}>{children}</div>

        {(pie || mostrarCancelar) && (
          <div className="pagos-modal-footer">
            {mostrarCancelar && (
              <button type="button" className="btn btn-secondary" disabled={estado.procesando} onClick={cerrar}>
                Cancelar
              </button>
            )}
            {pie}
          </div>
        )}
      </div>
    </div>
  );
}
