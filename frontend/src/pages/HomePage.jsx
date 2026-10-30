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

  // Datos de prueba para mostrar la estructura
  const proyectos = [
    { id: 1, titulo: 'Sistema de Inventarios', descripcion: 'Aplicación web para gestión de inventarios con reportes.', precio: 5000, autor: 'Ana Garcia' },
    { id: 2, titulo: 'API REST de Pagos', descripcion: 'API para procesamiento de pagos con Stripe.', precio: 8000, autor: 'Ana Garcia' },
    { id: 3, titulo: 'Dashboard Analytics', descripcion: 'Panel de análisis de datos con gráficos interactivos.', precio: 3500, autor: 'Luis Martinez' },
  ];

  const ofertas = [
    { id: 1, titulo: 'Desarrollo de E-commerce', descripcion: 'Necesito una tienda en línea con carrito de compras y pasarela de pago.', presupuesto: 15000, estado: 'abierto' },
    { id: 2, titulo: 'App de Tareas', descripcion: 'Aplicación de gestión de tareas con notificaciones.', presupuesto: 5000, estado: 'abierto' },
  ];

  if (loading) return <div>Cargando...</div>;

  return (
    <div className="home">
      <header>
        <h1>Zaas</h1>
        <nav>
          <a href="#proyectos">Proyectos</a>
          <a href="#ofertas">Ofertas</a>
          {user ? (
            <>
              <span>{user.email}</span>
              <button onClick={handleLogout}>Cerrar Sesión</button>
            </>
          ) : (
            <button onClick={() => navigate('/login')}>Iniciar Sesión</button>
          )}
        </nav>
      </header>
      
      <main>
        <section id="hero" className="hero">
          <h2>Plataforma de Desarrollo y Contratación</h2>
          <p>Conecta clientes con desarrolladores para proyectos de software</p>
        </section>

        <section id="proyectos" className="section">
          <h3>Proyectos Destacados</h3>
          <div className="grid">
            {proyectos.map(p => (
              <div key={p.id} className="card">
                <h4>{p.titulo}</h4>
                <p>{p.descripcion}</p>
                <div className="card-footer">
                  <span className="precio">${p.precio.toLocaleString()}</span>
                  <span className="autor">por {p.autor}</span>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section id="ofertas" className="section">
          <h3>Ofertas de Trabajo</h3>
          <div className="grid">
            {ofertas.map(o => (
              <div key={o.id} className="card">
                <h4>{o.titulo}</h4>
                <p>{o.descripcion}</p>
                <div className="card-footer">
                  <span className="presupuesto">Presupuesto: ${o.presupuesto.toLocaleString()}</span>
                  <span className={`estado ${o.estado}`}>{o.estado}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
