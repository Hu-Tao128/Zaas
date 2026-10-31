import { Link, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { logout } from '../../services/authService';

export default function CatalogoLayout() {
  const { user } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <div className="catalogo-app">
      <nav className="catalogo-navbar" aria-label="Navegación principal">
        <div className="catalogo-nav-group">
          <Link to="/catalogo" className="catalogo-brand">Zaas</Link>
          <Link to="/catalogo">Catálogo</Link>
          <Link to="/catalogo/ofertas">Ofertas</Link>
        </div>
        <div className="catalogo-nav-group catalogo-nav-user">
          <span>{user?.displayName || user?.email}</span>
          <button type="button" onClick={handleLogout}>Salir</button>
        </div>
      </nav>
      <main className="catalogo-container">
        <Outlet />
      </main>
    </div>
  );
}
