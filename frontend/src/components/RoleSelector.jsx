/**
 * Componente Selector de Rol para el paso intermedio de registro.
 * Permite al usuario elegir entre 'cliente' o 'desarrollador' antes de sincronizar con el backend.
 *
 * Cumple estrictamente con WCAG (contraste >= 4.5:1, role="radiogroup", role="radio", aria-checked)
 * y garantiza la jerarquía visual de botones y tarjetas con fondo blanco.
 */
export default function RoleSelector({
  rolSeleccionado,
  onSeleccionarRol,
  onConfirmar,
  onVolver,
  cargando = false,
  error = '',
}) {
  const esCliente = rolSeleccionado === 'cliente';
  const esDesarrollador = rolSeleccionado === 'desarrollador';

  return (
    <div className="zaas-role-selector-container">
      {/* Encabezado */}
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

      {/* Grid de Tarjetas de Roles con radiogroup accesible */}
      <div
        className="zaas-role-cards-grid"
        role="radiogroup"
        aria-label="Selecciona tu tipo de cuenta en Zaas"
      >
        {/* Tarjeta 1: Cliente */}
        <button
          type="button"
          role="radio"
          aria-checked={esCliente}
          tabIndex={0}
          className={`zaas-role-card ${esCliente ? 'zaas-role-card--selected' : ''}`}
          onClick={() => onSeleccionarRol('cliente')}
          onKeyDown={(e) => {
            if (e.key === ' ' || e.key === 'Enter') {
              e.preventDefault();
              onSeleccionarRol('cliente');
            }
          }}
          aria-label="Rol Cliente: Busco talento y soluciones SaaS"
        >
          <div className="zaas-role-card-header">
            <div
              className={`zaas-role-icon-wrapper ${
                esCliente ? 'zaas-role-icon-wrapper--selected' : ''
              }`}
              aria-hidden="true"
            >
              {/* Icono de Maletín / Edificio */}
              <svg
                width="28"
                height="28"
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

            {/* Checkmark en esquina superior derecha si está seleccionado */}
            {esCliente ? (
              <span className="zaas-role-checked-badge" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </span>
            ) : (
              <span className="zaas-role-unchecked-circle" aria-hidden="true" />
            )}
          </div>

          <h3 className="zaas-role-card-title">Cliente</h3>
          <p className="zaas-role-card-tagline">Busco talento y soluciones SaaS</p>
          <p className="zaas-role-card-description">
            Adquiere plataformas SaaS verificadas, publica ofertas de empleo y contrata desarrolladores con pagos custodiados en garantía Escrow.
          </p>
        </button>

        {/* Tarjeta 2: Desarrollador */}
        <button
          type="button"
          role="radio"
          aria-checked={esDesarrollador}
          tabIndex={0}
          className={`zaas-role-card ${esDesarrollador ? 'zaas-role-card--selected' : ''}`}
          onClick={() => onSeleccionarRol('desarrollador')}
          onKeyDown={(e) => {
            if (e.key === ' ' || e.key === 'Enter') {
              e.preventDefault();
              onSeleccionarRol('desarrollador');
            }
          }}
          aria-label="Rol Desarrollador: Ofrezco mis servicios y desarrollo SaaS"
        >
          <div className="zaas-role-card-header">
            <div
              className={`zaas-role-icon-wrapper ${
                esDesarrollador ? 'zaas-role-icon-wrapper--selected' : ''
              }`}
              aria-hidden="true"
            >
              {/* Icono de Código / Terminal (< />) */}
              <svg
                width="28"
                height="28"
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

            {/* Checkmark en esquina superior derecha si está seleccionado */}
            {esDesarrollador ? (
              <span className="zaas-role-checked-badge" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="3">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              </span>
            ) : (
              <span className="zaas-role-unchecked-circle" aria-hidden="true" />
            )}
          </div>

          <h3 className="zaas-role-card-title">Desarrollador</h3>
          <p className="zaas-role-card-tagline">Ofrezco mis servicios y desarrollo SaaS</p>
          <p className="zaas-role-card-description">
            Vende tus micro-SaaS en el catálogo, postúlate a encargos de desarrollo y asegura tus cobros por hitos mediante contratos Escrow.
          </p>
        </button>
      </div>

      {/* Botones de Acción Inferiores con Jerarquía Visual Clara */}
      <div className="zaas-role-actions">
        {onVolver && (
          <button
            type="button"
            className="zaas-btn-back"
            onClick={onVolver}
            disabled={cargando}
            aria-label="Volver al formulario de credenciales"
          >
            ← Volver
          </button>
        )}

        {/* Botón Primario: Rojo Principal (#DC2626) con texto blanco en negrita */}
        <button
          type="button"
          className="zaas-btn-confirm"
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
              Continuar como {esDesarrollador ? 'Desarrollador' : 'Cliente'} →
            </span>
          )}
        </button>
      </div>
    </div>
  );
}
