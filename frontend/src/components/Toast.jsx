import { useEffect } from 'react';

/**
 * Componente Toast accesible para confirmaciones y notificaciones de estado.
 * Cumple con WCAG (aria-live="polite", role="status") y Heurística de Nielsen #1.
 */
export default function Toast({ mensaje, tipo = 'success', onClose, duracion = 4000 }) {
  useEffect(() => {
    if (!mensaje) return;
    const timer = setTimeout(() => {
      onClose?.();
    }, duracion);
    return () => clearTimeout(timer);
  }, [mensaje, duracion, onClose]);

  if (!mensaje) return null;

  const esExito = tipo === 'success';

  return (
    <div
      className={`zaas-toast zaas-toast--${tipo}`}
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="zaas-toast-icon-wrapper" aria-hidden="true">
        {esExito ? (
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        )}
      </div>

      <div className="zaas-toast-content">
        <p className="zaas-toast-message">{mensaje}</p>
      </div>

      <button
        type="button"
        className="zaas-toast-close"
        onClick={onClose}
        aria-label="Cerrar notificación"
      >
        <svg
          aria-hidden="true"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>
  );
}
