import { Link, NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { logout } from '../services/authService';

export default function AppNavbar({ usuario }) {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  async function salir() {
    setPending(true);
    setError('');
    try { await logout(); navigate('/login'); }
    catch { setError('No se pudo cerrar la sesión. Intenta nuevamente.'); }
    finally { setPending(false); }
  }
  return <>
    <nav className="catalogo-navbar" aria-label="Navegación principal">
      <div className="catalogo-nav-group">
        <Link to="/" className="catalogo-brand">Zaas</Link>
        <NavLink to="/" end>Catálogo</NavLink>
        <NavLink to="/ofertas">Ofertas</NavLink>
        <NavLink to="/comunicacion">Comunicación</NavLink>
        {usuario?.tipo_usuario === 'admin' && <NavLink to="/admin">Administración</NavLink>}
      </div>
      <div className="catalogo-nav-group catalogo-nav-user">
        <span>{usuario?.nombre || usuario?.nombres || usuario?.email || 'Zaas'}</span>
        <button type="button" onClick={salir} disabled={pending}>{pending ? 'Saliendo…' : 'Salir'}</button>
      </div>
    </nav>
    {error && <p className="alert alert-danger" role="alert">{error}</p>}
  </>;
}
