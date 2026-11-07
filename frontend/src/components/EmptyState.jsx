import { Link } from 'react-router-dom';

/**
 * Componente EmptyState accesible y visualmente claro.
 * Ayuda al usuario a entender por qué no hay resultados y le provee
 * una acción inmediata para recuperarse (Heurística Nielsen #5 y #9).
 *
 * @param {Object} props
 * @param {string} [props.title] - Título principal del estado vacío
 * @param {string} [props.description] - Descripción explicativa y sugerencia
 * @param {Function} [props.onReset] - Función para reiniciar búsqueda/filtros
 * @param {string} [props.resetText] - Texto del botón de reset
 * @param {string} [props.actionLink] - Enlace opcional de acción
 * @param {string} [props.actionText] - Texto del enlace de acción
 */
export default function EmptyState({
  title = 'No se encontraron resultados',
  description = 'No encontramos elementos que coincidan con tus criterios de búsqueda o filtros.',
  onReset,
  resetText = 'Limpiar filtros y ver todos',
  actionLink,
  actionText,
}) {
  return (
    <div className="card zaas-empty-state" role="status" aria-live="polite">
      <div className="zaas-empty-state-icon-wrapper" aria-hidden="true">
        <svg
          className="zaas-empty-state-icon"
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
      </div>

      <h3 className="zaas-empty-state-title">{title}</h3>
      <p className="zaas-empty-state-description">{description}</p>

      <div className="zaas-empty-state-actions">
        {onReset && (
          <button
            type="button"
            onClick={onReset}
            className="btn btn-primary"
            aria-label={resetText}
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
              <polyline points="1 4 1 10 7 10" />
              <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
            </svg>
            <span>{resetText}</span>
          </button>
        )}

        {actionLink && actionText && (
          <Link to={actionLink} className="btn btn-secondary">
            {actionText}
          </Link>
        )}
      </div>
    </div>
  );
}
