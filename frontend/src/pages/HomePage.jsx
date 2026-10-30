import { useAuth } from '../context/AuthContext';
import { logout } from '../services/authService';
import { useNavigate } from 'react-router-dom';

export default function HomePage() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  if (loading) return <div>Cargando...</div>;

  return (
    <div className="home">
      <header>
        <h1>Zaas</h1>
        {user ? (
          <div>
            <span>{user.email}</span>
            <button onClick={handleLogout}>Cerrar Sesión</button>
          </div>
        ) : (
          <button onClick={() => navigate('/login')}>Iniciar Sesión</button>
        )}
      </header>
      
      <main>
        <h2>Bienvenido a Zaas</h2>
        <p>Plataforma de desarrollo y contratación</p>
      </main>
    </div>
  );
}
