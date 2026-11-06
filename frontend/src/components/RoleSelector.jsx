/**
 * Componente Selector de Rol para el paso intermedio de registro.
 * Permite al usuario elegir entre 'cliente' o 'desarrollador' antes de sincronizar con el backend.
 *
 * Cumple con accesibilidad (role="radiogroup", role="radio", aria-checked)
 * y resalta la selección con borde en Rojo Oscuro (#991B1B).
 */
export default function RoleSelector({
  rolSeleccionado,
  onSeleccionarRol,
  onConfirmar,
  onVolver,
  cargando = false,
  error = '',
}) {
  return (
    <div className="zaas-role-selector-container">
      <div className="zaas-role-header">
        <h2 className="zaas-role-title">¿Cómo deseas usar Zaas?</h2>
        <p className="zaas-role-subtitle">
          Selecciona tu rol principal para personalizar tu experiencia en el marketplace con protección Escrow.
        </p>
      </div>

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
        </div>
      )}

      {/* Selector de roles con radiogroup accesible */}
      <div
        className="zaas-role-cards-grid"
        role="radiogroup"
        aria-label="Selecciona tu tipo de cuenta en Zaas"
      >
        {/* Opción 1: Cliente */}
        <button
          type="button"
          role="radio"
          aria-checked={rolSeleccionado === 'cliente'}
          tabIndex={0}
          className={`zaas-role-card ${
            rolSeleccionado === 'cliente' ? 'zaas-role-card--selected' : ''
          }`}
          onClick={() => onSeleccionarRol('cliente')}
          onKeyDown={(e) => {
            if (e.key === ' ' || e.key === 'Enter') {
              e.preventDefault();
              onSeleccionarRol('cliente');
            }
          }}
        >
          <div className="zaas-role-card-header">
            <div className="zaas-role-icon-wrapper zaas-role-icon--cliente" aria-hidden="true">
              {/* Icono de Maletín / Edificio corporativo */}
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
                <circle cx="12" cy="12" r="1" />
              </svg>
            </div>
            {rolSeleccionado === 'cliente' && (
              <span className="zaas-role-checked-badge" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </span>
            )}
          </div>

          <h3 className="zaas-role-card-title">Cliente</h3>
          <p className="zaas-role-card-tagline">Busco talento y soluciones SaaS</p>
          <p className="zaas-role-card-description">
            Adquiere plataformas SaaS verificadas, publica ofertas de empleo y contrata desarrolladores con pagos custodiados en garantía Escrow.
          </p>
        </button>

        {/* Opción 2: Desarrollador */}
        <button
          type="button"
          role="radio"
          aria-checked={rolSeleccionado === 'desarrollador'}
          tabIndex={0}
          className={`zaas-role-card ${
            rolSeleccionado === 'desarrollador' ? 'zaas-role-card--selected' : ''
          }`}
          onClick={() => onSeleccionarRol('desarrollador')}
          onKeyDown={(e) => {
            if (e.key === ' ' || e.key === 'Enter') {
              e.preventDefault();
              onSeleccionarRol('desarrollador');
            }
          }}
        >
          <div className="zaas-role-card-header">
            <div className="zaas-role-icon-wrapper zaas-role-icon--dev" aria-hidden="true">
              {/* Icono de Código / Terminal */}
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="16 18 22 12 16 6" />
                <polyline points="8 6 2 12 8 18" />
                <line x1="14" y1="4" x2="10" y2="20" />
              </svg>
            </div>
            {rolSeleccionado === 'desarrollador' && (
              <span className="zaas-role-checked-badge" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </span>
            )}
          </div>

          <h3 className="zaas-role-card-title">Desarrollador</h3>
          <p className="zaas-role-card-tagline">Ofrezco mis servicios y desarrollo SaaS</p>
          <p className="zaas-role-card-description">
            Vende tus micro-SaaS en el catálogo, postúlate a encargos de desarrollo y asegura tus cobros por hitos mediante contratos Escrow.
          </p>
        </button>
      </div>

      {/* Botones de Confirmación y Retorno */}
      <div className="zaas-role-actions">
        {onVolver && (
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onVolver}
            disabled={cargando}
          >
            ← Volver
          </button>
        )}

        <button
          type="button"
          className="btn btn-primary btn-confirm-role"
          onClick={onConfirmar}
          disabled={!rolSeleccionado || cargando}
          aria-busy={cargando}
        >
          {cargando ? (
            <>
              <span className="zaas-button-spinner" aria-hidden="true" />
              <span>Creando cuenta en Zaas...</span>
            </>
          ) : (
            <span>
              Continuar como {rolSeleccionado === 'desarrollador' ? 'Desarrollador' : 'Cliente'} →
            </span>
          )}
        </button>
      </div>
    </div>
  );
}
