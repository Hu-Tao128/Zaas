import { Link } from 'react-router-dom';

/**
 * Componente de Controles de la Vista Principal (Búsqueda, Filtros y Botonera).
 * Aplica Flexbox y Grid para una alineación equilibrada, espaciado generoso
 * y garantiza la consistencia de estilos de acuerdo a las heurísticas de Nielsen.
 *
 * @param {Object} props
 * @param {'proyectos' | 'ofertas'} props.tipo - Tipo de vista ('proyectos' o 'ofertas')
 * @param {string} props.busqueda - Valor actual de búsqueda
 * @param {Function} props.onBusquedaChange - Manejador de cambio del texto de búsqueda
 * @param {string} [props.categoria] - Categoría seleccionada (solo para proyectos)
 * @param {Function} [props.onCategoriaChange] - Manejador de cambio de categoría
 * @param {Array<{id: string|number, nombre: string}>} [props.categorias] - Lista de categorías disponibles
 * @param {Function} props.onSubmit - Manejador al enviar la búsqueda
 * @param {Function} props.onLimpiar - Manejador para reiniciar los filtros
 * @param {boolean} props.tieneFiltros - Indica si hay filtros o búsqueda activos
 * @param {Object} props.usuario - Objeto de usuario autenticado con tipo_usuario
 * @param {number} [props.totalResultados] - Total opcional de resultados encontrados
 */
export default function CatalogControls({
  tipo = 'proyectos',
  busqueda,
  onBusquedaChange,
  categoria = '',
  onCategoriaChange,
  categorias = [],
  onSubmit,
  onLimpiar,
  tieneFiltros = false,
  usuario,
  totalResultados,
}) {
  const esProyectos = tipo === 'proyectos';
  const esDesarrollador = usuario?.tipo_usuario === 'desarrollador';
  const esCliente = usuario?.tipo_usuario === 'cliente';

  return (
    <section className="catalog-controls-section" aria-label="Controles de búsqueda, filtros y acciones">
      {/* Contenedor principal de Búsqueda y Filtros con diseño en Grid/Flexbox */}
      <form
        className="card catalog-controls-card"
        onSubmit={onSubmit}
        role="search"
        aria-label={esProyectos ? 'Buscar y filtrar proyectos SaaS' : 'Buscar y filtrar ofertas de empleo'}
      >
        <div className="catalog-search-grid">
          {/* Campo de búsqueda con Label accesible */}
          <div className="catalog-field-group catalog-field-group--search">
            <label htmlFor="catalog-search-input" className="catalog-field-label">
              Buscar {esProyectos ? 'proyectos SaaS' : 'ofertas de trabajo'}
            </label>
            <div className="catalog-input-wrapper">
              <svg
                className="catalog-input-icon"
                aria-hidden="true"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <input
                id="catalog-search-input"
                type="search"
                className="catalog-input-text"
                value={busqueda}
                onChange={(e) => onBusquedaChange(e.target.value)}
                placeholder={
                  esProyectos
                    ? 'Buscar SaaS por título, tecnología o descripción...'
                    : 'Buscar ofertas por título, requerimientos o stack...'
                }
                aria-label={
                  esProyectos
                    ? 'Buscar proyectos SaaS por nombre o tecnología'
                    : 'Buscar ofertas de trabajo por requerimientos'
                }
              />
            </div>
          </div>

          {/* Filtro por Categoría (para vista de proyectos) */}
          {esProyectos && (
            <div className="catalog-field-group catalog-field-group--filter">
              <label htmlFor="catalog-category-select" className="catalog-field-label">
                Filtrar por categoría
              </label>
              <div className="catalog-select-wrapper">
                <select
                  id="catalog-category-select"
                  className="catalog-select"
                  value={categoria}
                  onChange={(e) => onCategoriaChange?.(e.target.value)}
                  aria-label="Seleccionar categoría de proyectos SaaS"
                >
                  <option value="">Todas las categorías</option>
                  {categorias.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.nombre}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}

          {/* Botones de acción del formulario (Buscar y Limpiar) */}
          <div className="catalog-form-buttons">
            <button
              type="submit"
              className="btn btn-primary catalog-btn-submit"
              aria-label="Ejecutar búsqueda"
            >
              <svg
                aria-hidden="true"
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <circle cx="11" cy="11" r="8" />
                <line x1="21" y1="21" x2="16.65" y2="16.65" />
              </svg>
              <span>Buscar</span>
            </button>

            {tieneFiltros && (
              <button
                type="button"
                onClick={onLimpiar}
                className="btn btn-secondary catalog-btn-clear"
                aria-label="Limpiar filtros y restablecer lista completa"
              >
                <svg
                  aria-hidden="true"
                  width="15"
                  height="15"
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
                <span>Limpiar filtros</span>
              </button>
            )}
          </div>
        </div>
      </form>

      {/* Botonera de acciones unificada y consistente (Heurística Nielsen #4) */}
      <div
        className="catalog-actions-bar"
        role="toolbar"
        aria-label="Acciones rápidas de usuario"
      >
        <div className="catalog-actions-group">
          {esProyectos && esDesarrollador && (
            <>
              {/* Botón primario consistente en rojo #DC2626 */}
              <Link to="/proyecto/nuevo" className="btn btn-primary">
                <svg
                  aria-hidden="true"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                <span>Nuevo Proyecto</span>
              </Link>

              {/* Botones secundarios con fondo blanco, borde y texto #404040 */}
              <Link to="/mis-productos" className="btn btn-secondary">
                Mis productos
              </Link>
            </>
          )}
          {!esProyectos && esCliente && (
            <>
              <Link to="/oferta/nueva" className="btn btn-primary">
                <svg
                  aria-hidden="true"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                <span>Nueva Oferta</span>
              </Link>

              {/* 'Mis ofertas' siempre botón secundario (#FFFFFF bg, #404040 border/text) */}
              <Link to="/mis-ofertas" className="btn btn-secondary">
                Mis ofertas
              </Link>
            </>
          )}
          {!esProyectos && esDesarrollador && (
            <Link to="/mis-postulaciones" className="btn btn-secondary">Mis postulaciones</Link>
          )}

          {/* En la vista de ofertas se ofrece volver al catálogo de productos SaaS */}
          {!esProyectos && (
            <Link to="/" className="btn btn-secondary">
              Ver catálogo
            </Link>
          )}
        </div>

        {/* Indicador de resultados activos cuando corresponda */}
        {typeof totalResultados === 'number' && (
          <div className="catalog-results-count" aria-live="polite">
            <span className="results-badge">
              {totalResultados === 1 ? '1 resultado disponible' : `${totalResultados} resultados disponibles`}
            </span>
          </div>
        )}
      </div>
    </section>
  );
}
