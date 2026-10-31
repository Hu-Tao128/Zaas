import { Link } from 'react-router-dom';

export function Badge({ variant = 'secondary', children }) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}

export function BadgeEstado({ estado }) {
  const variantes = {
    abierto: 'success',
    activo: 'success',
    aceptada: 'success',
    en_progreso: 'info',
    pendiente: 'warning',
    cerrado: 'danger',
    rechazada: 'danger',
  };
  return <Badge variant={variantes[estado] || 'secondary'}>{estado.replaceAll('_', ' ')}</Badge>;
}

export function Pagination({ pagina, totalPaginas, onCambiarPagina }) {
  if (totalPaginas <= 1) return null;

  return (
    <div className="pagination">
      {pagina > 1 && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => onCambiarPagina(pagina - 1)}>
          ← Anterior
        </button>
      )}
      <span className="pagination-label">Página {pagina} de {totalPaginas}</span>
      {pagina < totalPaginas && (
        <button type="button" className="btn btn-secondary btn-sm" onClick={() => onCambiarPagina(pagina + 1)}>
          Siguiente →
        </button>
      )}
    </div>
  );
}

export function FormField({ label, name, error, hint, children }) {
  return (
    <div className="form-group">
      <label htmlFor={name}>{label}</label>
      {children}
      {hint && <small className="form-hint">{hint}</small>}
      {error && <small className="field-error">{error}</small>}
    </div>
  );
}

export function EmptyCard({ children }) {
  return <div className="card"><p>{children}</p></div>;
}

export function Cargando() {
  return <div className="card" role="status"><p>Cargando...</p></div>;
}

/** Error de la API (404, 403, red caída...) con un enlace para volver. */
export function ErrorCard({ error, volverA = '/catalogo', volverTexto = 'Volver al catálogo' }) {
  return (
    <div className="card">
      <div className="alert alert-danger">{error?.message || 'Ocurrió un error inesperado.'}</div>
      <Link to={volverA} className="btn btn-secondary">{volverTexto}</Link>
    </div>
  );
}

export function AlertaError({ children }) {
  if (!children) return null;
  return <div className="alert alert-danger" role="alert">{children}</div>;
}
