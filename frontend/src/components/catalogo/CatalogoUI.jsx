import { Link } from 'react-router-dom';

/**
 * Insignia genérica accesible para etiquetas informativas.
 */
export function Badge({ variant = 'secondary', children, className = '' }) {
  return <span className={`badge badge-${variant} ${className}`}>{children}</span>;
}

/**
 * Insignia de estado semántica con iconos de apoyo para reducir carga cognitiva (WCAG y Nielsen Heuristic #1).
 */
export function BadgeEstado({ estado }) {
  if (!estado) return null;

  const config = {
    abierto: {
      variante: 'success',
      label: 'Abierto',
      icono: <span className="status-indicator status-indicator--green" aria-hidden="true" />,
    },
    activo: {
      variante: 'success',
      label: 'Activo',
      icono: <span className="status-indicator status-indicator--green" aria-hidden="true" />,
    },
    aceptada: {
      variante: 'success',
      label: 'Aceptada',
      icono: <span className="status-indicator status-indicator--green" aria-hidden="true" />,
    },
    en_progreso: {
      variante: 'warning',
      label: 'En progreso',
      icono: <span className="status-indicator status-indicator--amber" aria-hidden="true" />,
    },
    pendiente: {
      variante: 'warning',
      label: 'Pendiente',
      icono: <span className="status-indicator status-indicator--amber" aria-hidden="true" />,
    },
    cerrado: {
      variante: 'danger',
      label: 'Cerrado',
      icono: <span className="status-indicator status-indicator--gray" aria-hidden="true" />,
    },
    rechazada: {
      variante: 'danger',
      label: 'Rechazada',
      icono: <span className="status-indicator status-indicator--gray" aria-hidden="true" />,
    },
  };

  const item = config[estado] || {
    variante: 'secondary',
    label: estado.replaceAll('_', ' '),
    icono: null,
  };

  return (
    <span
      className={`badge badge-${item.variante}`}
      role="status"
      aria-label={`Estado: ${item.label}`}
    >
      {item.icono}
      <span>{item.label}</span>
    </span>
  );
}

/**
 * Paginación accesible con soporte de teclado y roles ARIA.
 */
export function Pagination({ pagina, totalPaginas, onCambiarPagina }) {
  if (totalPaginas <= 1) return null;

  return (
    <nav className="catalogo-pagination" aria-label="Navegación entre páginas de resultados">
      {pagina > 1 && (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => onCambiarPagina(pagina - 1)}
          aria-label="Ir a la página anterior"
        >
          ← Anterior
        </button>
      )}
      <span className="catalogo-pagination-label" aria-current="page">
        Página {pagina} de {totalPaginas}
      </span>
      {pagina < totalPaginas && (
        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={() => onCambiarPagina(pagina + 1)}
          aria-label="Ir a la página siguiente"
        >
          Siguiente →
        </button>
      )}
    </nav>
  );
}

/**
 * Grupo de campo con etiqueta accesible y vinculación for/id.
 */
export function FormField({ label, name, error, hint, children }) {
  return (
    <div className="form-group">
      <label htmlFor={name}>{label}</label>
      {children}
      {hint && <small className="form-hint" id={`${name}-hint`}>{hint}</small>}
      {error && <small className="field-error" id={`${name}-error`} role="alert">{error}</small>}
    </div>
  );
}

export function EmptyCard({ children }) {
  return (
    <div className="card zaas-empty-card" role="status">
      <p>{children}</p>
    </div>
  );
}

export function Cargando() {
  return (
    <div className="card zaas-loading-card" role="status" aria-live="polite">
      <div className="zaas-spinner" aria-hidden="true" />
      <p>Cargando información...</p>
    </div>
  );
}

/**
 * Error de la API con enlace para reintentar o volver.
 */
export function ErrorCard({ error, volverA = '/', volverTexto = 'Volver al catálogo' }) {
  return (
    <div className="card zaas-error-card" role="alert">
      <div className="alert alert-danger">{error?.message || 'Ocurrió un error inesperado.'}</div>
      <Link to={volverA} className="btn btn-secondary">{volverTexto}</Link>
    </div>
  );
}

export function AlertaError({ children }) {
  if (!children) return null;
  return <div className="alert alert-danger" role="alert">{children}</div>;
}
