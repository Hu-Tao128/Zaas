import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useNotificaciones } from '../context/NotificacionesContext';
import { logout } from '../services/authService';
import { formatFechaHora } from '../pages/catalogo/catalogoUtils';

const ENLACES_PRINCIPALES = [
  { to: '/', label: 'Catálogo', end: true },
  { to: '/ofertas', label: 'Ofertas' },
  { to: '/contratos', label: 'Contratos' },
  { to: '/comunicacion', label: 'Comunicación' },
  { to: '/agente', label: 'Agente' },
];

const ENLACES_CUENTA = [
  { to: '/incidencias', label: 'Incidencias' },
  { to: '/disputas', label: 'Disputas' },
];

function claseEnlace({ isActive }) {
  return `catalogo-nav-link ${isActive ? 'catalogo-nav-link--active' : ''}`;
}

function IconoCampana({ size = 19 }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}

function IconoChevron({ size = 14 }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function IconoSalir({ size = 16 }) {
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
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
  );
}

function IconoMenu({ abierto }) {
  return (
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
      {abierto ? (
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
  );
}

export default function Navbar({ usuario }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const navRef = useRef(null);

  const [menuMovilAbierto, setMenuMovilAbierto] = useState(false);
  const [dropdownActivo, setDropdownActivo] = useState(null);
  const {
    notificaciones,
    noLeidas,
    loading: notificacionesLoading,
    error: notificacionesError,
    cargar: cargarNotificaciones,
    marcarLeida,
  } = useNotificaciones();

  const cerrarTodo = useCallback(() => {
    setMenuMovilAbierto(false);
    setDropdownActivo(null);
  }, []);

  const nombreCompleto =
    [usuario?.nombres, usuario?.apellido_paterno, usuario?.apellido_materno]
      .filter(Boolean)
      .join(' ')
      .trim() ||
    user?.displayName?.trim() ||
    user?.email ||
    'Usuario';

  const primerNombre =
    (usuario?.nombres || user?.displayName || nombreCompleto)
      .trim()
      .split(/\s+/)[0] || 'Usuario';

  const inicial =
    (usuario?.nombres || user?.displayName || user?.email || nombreCompleto)
      .trim()
      .charAt(0)
      .toUpperCase() || 'U';

  const tipoUsuario = usuario?.tipo_usuario;
  const rolLabel =
    tipoUsuario === 'desarrollador'
      ? 'Desarrollador'
      : tipoUsuario === 'cliente'
        ? 'Cliente'
        : tipoUsuario === 'admin'
          ? 'Administrador'
          : '';

  useEffect(() => {
    cargarNotificaciones();
  }, [cargarNotificaciones]);

  useEffect(() => {
    function manejarClickExterno(event) {
      if (navRef.current && !navRef.current.contains(event.target)) {
        cerrarTodo();
      }
    }

    function manejarTecla(event) {
      if (event.key === 'Escape') {
        cerrarTodo();
      }
    }

    document.addEventListener('mousedown', manejarClickExterno);
    document.addEventListener('keydown', manejarTecla);
    return () => {
      document.removeEventListener('mousedown', manejarClickExterno);
      document.removeEventListener('keydown', manejarTecla);
    };
  }, [cerrarTodo]);

  async function handleLogout() {
    cerrarTodo();
    try {
      await logout();
      navigate('/login');
    } catch (err) {
      console.error('Error al cerrar sesión:', err);
    }
  }

  function alternarDropdown(nombre) {
    setMenuMovilAbierto(false);
    const abriendo = dropdownActivo !== nombre;
    setDropdownActivo(abriendo ? nombre : null);
    if (abriendo && nombre === 'notificaciones') {
      cargarNotificaciones({ silencioso: notificaciones.length > 0 });
    }
  }

  function alternarMenuMovil() {
    setDropdownActivo(null);
    setMenuMovilAbierto((prev) => !prev);
  }

  function abrirNotificacion(event, notificacion) {
    event.preventDefault();
    cerrarTodo();
    const destino = notificacion.link || '/notificaciones';
    marcarLeida(notificacion);
    navigate(destino);
  }

  return (
    <header className="catalogo-header" role="banner">
      <nav ref={navRef} className="catalogo-navbar" aria-label="Navegación principal">
        <div className="catalogo-nav-brand-group">
          <Link
            to="/"
            className="catalogo-brand"
            onClick={cerrarTodo}
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

        <ul className="catalogo-nav-links catalogo-nav-links--desktop" role="list">
          {ENLACES_PRINCIPALES.map((enlace) => (
            <li key={enlace.to}>
              <NavLink
                to={enlace.to}
                end={enlace.end}
                onClick={cerrarTodo}
                className={claseEnlace}
              >
                {enlace.label}
              </NavLink>
            </li>
          ))}
        </ul>

        <div className="catalogo-nav-actions">
          <div className="navbar-menu">
            <button
              type="button"
              className="navbar-icon-btn"
              onClick={() => alternarDropdown('notificaciones')}
              aria-label={
                noLeidas > 0
                  ? `Notificaciones: ${noLeidas} sin leer`
                  : 'Notificaciones'
              }
              aria-haspopup="true"
              aria-expanded={dropdownActivo === 'notificaciones'}
              aria-controls="navbar-notificaciones-panel"
            >
              <IconoCampana />
              {noLeidas > 0 && (
                <span className="navbar-notification-count" aria-hidden="true">
                  {noLeidas > 99 ? '99+' : noLeidas}
                </span>
              )}
            </button>

            {dropdownActivo === 'notificaciones' && (
              <div
                id="navbar-notificaciones-panel"
                className="navbar-dropdown navbar-notifications-dropdown"
                role="dialog"
                aria-label="Notificaciones recientes"
              >
                <div className="navbar-dropdown-header">
                  <strong>Notificaciones</strong>
                  {noLeidas > 0 && (
                    <span className="navbar-dropdown-pill">
                      {noLeidas} sin leer
                    </span>
                  )}
                </div>

                <div className="navbar-notifications-list">
                  {notificacionesLoading && (
                    <p className="navbar-dropdown-empty">Cargando notificaciones...</p>
                  )}
                  {!notificacionesLoading && notificacionesError && (
                    <p className="navbar-dropdown-empty">{notificacionesError}</p>
                  )}
                  {!notificacionesLoading &&
                    !notificacionesError &&
                    notificaciones.length === 0 && (
                      <p className="navbar-dropdown-empty">No tienes notificaciones.</p>
                    )}
                  {!notificacionesLoading &&
                    !notificacionesError &&
                    notificaciones.map((notificacion) => (
                      <Link
                        key={notificacion.id}
                        to={notificacion.link || '/notificaciones'}
                        className={`navbar-notification-item ${
                          notificacion.leido ? 'is-read' : ''
                        }`}
                        onClick={(event) => abrirNotificacion(event, notificacion)}
                      >
                        <span className="navbar-notification-title">
                          {notificacion.asunto}
                        </span>
                        {notificacion.mensaje && (
                          <span className="navbar-notification-body">
                            {notificacion.mensaje}
                          </span>
                        )}
                        <span className="navbar-notification-date">
                          {formatFechaHora(notificacion.fecha_hora_creacion)}
                        </span>
                      </Link>
                    ))}
                </div>

                <Link
                  to="/notificaciones"
                  className="navbar-dropdown-footer"
                  onClick={cerrarTodo}
                >
                  Ver todas las notificaciones
                </Link>
              </div>
            )}
          </div>

          <div className="navbar-menu navbar-profile-wrapper">
            <button
              type="button"
              className="navbar-profile-trigger"
              onClick={() => alternarDropdown('perfil')}
              aria-haspopup="menu"
              aria-expanded={dropdownActivo === 'perfil'}
              aria-controls="navbar-perfil-panel"
              title={nombreCompleto}
            >
              <span className="navbar-profile-avatar" aria-hidden="true">
                {inicial}
              </span>
              {rolLabel && (
                <span className={`navbar-role-badge navbar-role-badge--${tipoUsuario}`}>
                  {rolLabel}
                </span>
              )}
              <span className="navbar-profile-name">{primerNombre}</span>
              <IconoChevron />
            </button>

            {dropdownActivo === 'perfil' && (
              <div
                id="navbar-perfil-panel"
                className="navbar-dropdown navbar-profile-dropdown"
                role="menu"
              >
                <Link
                  to="/perfil"
                  className="navbar-profile-summary navbar-profile-summary--link"
                  onClick={cerrarTodo}
                  aria-label="Ir a mi perfil"
                >
                  <span className="navbar-profile-avatar navbar-profile-avatar--lg" aria-hidden="true">
                    {inicial}
                  </span>
                  <div className="navbar-profile-summary-text">
                    <p className="navbar-profile-fullname">{nombreCompleto}</p>
                    {rolLabel && (
                      <span className={`navbar-role-badge navbar-role-badge--${tipoUsuario}`}>
                        {rolLabel}
                      </span>
                    )}
                  </div>
                </Link>

                <Link
                  to="/perfil"
                  className="navbar-dropdown-item"
                  role="menuitem"
                  onClick={cerrarTodo}
                >
                  Mi Perfil
                </Link>
                <Link
                  to="/incidencias"
                  className="navbar-dropdown-item"
                  role="menuitem"
                  onClick={cerrarTodo}
                >
                  Incidencias
                </Link>
                <Link
                  to="/disputas"
                  className="navbar-dropdown-item"
                  role="menuitem"
                  onClick={cerrarTodo}
                >
                  Disputas
                </Link>
                {tipoUsuario === 'admin' && (
                  <Link
                    to="/admin"
                    className="navbar-dropdown-item"
                    role="menuitem"
                    onClick={cerrarTodo}
                  >
                    Administración
                  </Link>
                )}

                <hr className="navbar-dropdown-divider" />

                <button
                  type="button"
                  className="navbar-dropdown-item navbar-dropdown-item--danger"
                  role="menuitem"
                  onClick={handleLogout}
                >
                  <IconoSalir />
                  Salir
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            className="catalogo-nav-toggle"
            onClick={alternarMenuMovil}
            aria-expanded={menuMovilAbierto}
            aria-controls="navegacion-principal"
            aria-label={
              menuMovilAbierto
                ? 'Cerrar menú de navegación'
                : 'Abrir menú de navegación'
            }
          >
            <IconoMenu abierto={menuMovilAbierto} />
          </button>
        </div>

        {menuMovilAbierto && (
          <div
            id="navegacion-principal"
            className="catalogo-nav-mobile-panel"
          >
            <div className="catalogo-nav-mobile-user">
              <span className="navbar-profile-avatar" aria-hidden="true">
                {inicial}
              </span>
              <div className="navbar-profile-summary-text">
                <p className="navbar-profile-fullname">{nombreCompleto}</p>
                {rolLabel && (
                  <span className={`navbar-role-badge navbar-role-badge--${tipoUsuario}`}>
                    {rolLabel}
                  </span>
                )}
              </div>
            </div>

            <ul className="catalogo-nav-links catalogo-nav-links--mobile" role="list">
              {ENLACES_PRINCIPALES.map((enlace) => (
                <li key={enlace.to}>
                  <NavLink
                    to={enlace.to}
                    end={enlace.end}
                    onClick={cerrarTodo}
                    className={claseEnlace}
                  >
                    {enlace.label}
                  </NavLink>
                </li>
              ))}
              <li>
                <NavLink
                  to="/perfil"
                  onClick={cerrarTodo}
                  className={claseEnlace}
                >
                  Mi Perfil
                </NavLink>
              </li>
              {ENLACES_CUENTA.map((enlace) => (
                <li key={enlace.to}>
                  <NavLink
                    to={enlace.to}
                    onClick={cerrarTodo}
                    className={claseEnlace}
                  >
                    {enlace.label}
                  </NavLink>
                </li>
              ))}
              {tipoUsuario === 'admin' && (
                <li>
                  <NavLink
                    to="/admin"
                    onClick={cerrarTodo}
                    className={claseEnlace}
                  >
                    Administración
                  </NavLink>
                </li>
              )}
            </ul>

            <button
              type="button"
              onClick={handleLogout}
              className="catalogo-nav-logout-btn catalogo-nav-logout-btn--full"
            >
              <IconoSalir />
              <span>Salir</span>
            </button>
          </div>
        )}
      </nav>
    </header>
  );
}
