import { useEffect, useRef } from 'react';

/**
 * Componente modal de confirmación accesible para sustituir window.confirm.
 */
export default function ConfirmDialog({
  abierto,
  titulo = 'Confirmar acción',
  mensaje,
  onConfirmar,
  onCancelar,
  textoConfirmar = 'Confirmar',
  textoCancelar = 'Cancelar',
  procesando = false,
}) {
  const panelRef = useRef(null);
  const triggerRef = useRef(null);

  useEffect(() => {
    if (!abierto) return undefined;
    triggerRef.current = document.activeElement;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !procesando) {
        e.stopPropagation();
        onCancelar();
      }
    };
    document.addEventListener('keydown', handleKeyDown, true);

    if (panelRef.current) {
      const primerBoton = panelRef.current.querySelector('button');
      if (primerBoton) primerBoton.focus();
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown, true);
      document.body.style.overflow = prevOverflow;
      if (triggerRef.current && typeof triggerRef.current.focus === 'function') {
        triggerRef.current.focus();
      }
    };
  }, [abierto, procesando, onCancelar]);

  if (!abierto) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={titulo}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1400,
        background: 'rgba(15,23,42,.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
      onClick={() => {
        if (!procesando) onCancelar();
      }}
    >
      <div
        ref={panelRef}
        className="card"
        style={{
          width: '100%',
          maxWidth: 440,
          margin: 'auto',
          padding: '1.25rem',
          outline: 'none',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <h3 style={{ margin: '0 0 .75rem 0', fontSize: '1.15rem' }}>{titulo}</h3>
        <p style={{ margin: '0 0 1.25rem 0', color: 'var(--zaas-text-muted, #64748b)', fontSize: '.95rem', lineHeight: 1.5 }}>
          {mensaje}
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary"
            disabled={procesando}
            onClick={onCancelar}
          >
            {textoCancelar}
          </button>
          <button
            type="button"
            className="btn btn-primary"
            disabled={procesando}
            onClick={onConfirmar}
          >
            {procesando ? 'Procesando...' : textoConfirmar}
          </button>
        </div>
      </div>
    </div>
  );
}
