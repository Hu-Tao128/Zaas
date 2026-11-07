import { useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useCatalogo } from '../context/CatalogoContext';
import { logout } from '../services/authService';

/**
 * Componente Navbar con navegación accesible, estados de foco limpios (:focus-visible),
 * semántica ARIA, soporte para roles y distintivo de garantía Escrow.
 */
export default function Navbar() {
  const { user } = useAuth();
  const { usuario } = useCatalogo();
  const navigate = useNavigate();
  const [menuAbierto, setMenuAbierto] = useState(false);

  async function handleLogout() {
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Error al cerrar sesión:', err);
    }
  }

  function toggleMenu() {
    setMenuAbierto((prev) => !prev);
  }

  function cerrarMenu() {
    setMenuAbierto(false);
  }

  const tipoUsuarioLabel = usuario?.tipo_usuario === 'desarrollador'
    ? 'Desarrollador'
    : usuario?.tipo_usuario === 'cliente'
    ? 'Cliente'
    : null;

  return (
    <header className="catalogo-header" role="banner">
      <nav className="catalogo-navbar" aria-label="Navegación principal">
        {/* Marca / Logo y distintivo Escrow */}
        <div className="catalogo-nav-brand-group">
          <Link
            to="/"
            className="catalogo-brand"
            onClick={cerrarMenu}
            aria-label="Zaas - Inicio y plataforma de SaaS y talento con Escrow"
          >
            <span className="brand-name">Zaas</span>
            <span className="brand-dot" aria-hidden="true">.</span>
          </Link>

          <div
            className="navbar-escrow-badge"
            title="Garantía Zaas: Pagos y contratos custodiados por sistema Escrow"
            tabIndex={0}
            role="note"
            aria-label="Garantía Zaas: Pagos y contratos custodiados por sistema Escrow"
          >
            <svg
              className="navbar-escrow-icon"
              aria-hidden="true"
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="m9 12 2 2 4-4" />
            </svg>
            <span className="navbar-escrow-text">Escrow Protegido</span>
          </div>
        </div>

        {/* Botón hamburguesa accesible para dispositivos móviles */}
        <button
          type="button"
          className="catalogo-nav-toggle"
          onClick={toggleMenu}
          aria-expanded={menuAbierto}
          aria-controls="navegacion-principal"
          aria-label={menuAbierto ? 'Cerrar menú de navegación' : 'Abrir menú de navegación'}
        >
          <svg
            aria-hidden="true"
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            {menuAbierto ? (
              <>
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </>
            ) : (
              <>
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </>
            )}
          </svg>
        </button>

        {/* Enlaces de navegación y zona de usuario */}
        <div
          id="navegacion-principal"
          className={`catalogo-nav-content ${menuAbierto ? 'is-open' : ''}`}
        >
          <ul className="catalogo-nav-links" role="list">
            <li>
              <NavLink
                to="/"
                end
                onClick={cerrarMenu}
                className={({ isActive }) =>
                  `catalogo-nav-link ${isActive ? 'catalogo-nav-link--active' : ''}`
                }
              >
                Catálogo
              </NavLink>
            </li>
            <li>
              <NavLink
                to="/ofertas"
                onClick={cerrarMenu}
                className={({ isActive }) =>
                  `catalogo-nav-link ${isActive ? 'catalogo-nav-link--active' : ''}`
                }
              >
                Ofertas
              </NavLink>
            </li>
          </ul>

          <div className="catalogo-nav-user">
            <Link
              to="/perfil"
              onClick={cerrarMenu}
              className="catalogo-nav-profile-link"
              title="Ver mi perfil y configuración"
              aria-label="Ir a mi perfil"
            >
              {tipoUsuarioLabel && (
                <span
                  className={`navbar-role-badge navbar-role-badge--${usuario?.tipo_usuario}`}
                  title={`Has iniciado sesión como ${tipoUsuarioLabel}`}
                  aria-label={`Tipo de cuenta: ${tipoUsuarioLabel}`}
                >
                  {tipoUsuarioLabel}
                </span>
              )}
              <span
                className="catalogo-nav-username"
                title={user?.email || 'Usuario autenticado'}
              >
                {user?.displayName || user?.email}
              </span>
            </Link>
            <button
              type="button"
              onClick={handleLogout}
              className="catalogo-nav-logout-btn"
              aria-label="Cerrar sesión de la cuenta"
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
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              <span>Salir</span>
            </button>
          </div>
        </div>
      </nav>
    </header>
  );
}
