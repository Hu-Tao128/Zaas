import { Link, Navigate, useSearchParams } from 'react-router-dom';
import Navbar from '../components/Navbar';
import AdminCatalogo from './AdminCatalogo';
import AdminRegistros from './AdminRegistros';
import { useComunicacionResource } from '../hooks/useComunicacionResource';
import './catalogo/catalogo.css';
import './admin.css';

const modules = [
  { title: 'Incidencias', description: 'Consulta y resuelve los reportes de la plataforma.',
    to: '/incidencias', action: 'Gestionar incidencias' },
  { title: 'Comunicación', description: 'Consulta mensajes, solicitudes de demo y calificaciones.',
    to: '/comunicacion', action: 'Ir a Comunicación' },
  { title: 'Usuarios y permisos', description: 'Consulta las cuentas registradas y sus roles.',
    to: '?modulo=usuarios', action: 'Ver usuarios y roles' },
  { title: 'Catálogo y ofertas', description: 'Consulta los proyectos y ofertas de toda la plataforma.',
    to: '#catalogo-admin', action: 'Ver catálogo y ofertas' },
  { title: 'Contratos y entregables', description: 'Consulta los acuerdos y el avance de sus entregables.',
    to: '?modulo=contratos', action: 'Ver contratos' },
  { title: 'Pagos y disputas', description: 'Consulta los pagos en Escrow y atiende las disputas.',
    to: '?modulo=pagos', action: 'Ver pagos y disputas' },
];

export default function AdminPage() {
  const resource = useComunicacionResource('/admin/resumen');
  const summary = resource.result?.data;
  const [params] = useSearchParams();
  const modulo = params.get('modulo');
  const esListado = ['contratos', 'pagos', 'disputas', 'usuarios'].includes(modulo);
  if (resource.status === 401) return <Navigate to="/login" replace />;
  return <div className="catalogo-app admin-app">
    <Navbar usuario={summary?.usuario} />
    <main className="catalogo-container admin-container">
      {resource.loading && <p role="status">Comprobando acceso al panel…</p>}
      {resource.status === 403 && <section className="card admin-access" role="alert">
        <span className="admin-eyebrow">Acceso restringido</span>
        <h1>Este espacio es para administradores</h1>
        <p>Tu cuenta no tiene permisos para ingresar al panel administrativo.</p>
        <Link className="btn btn-primary" to="/">Volver al catálogo</Link>
      </section>}
      {resource.error && resource.status !== 403 && <section className="card" role="alert">
        <h1>No se pudo cargar el panel</h1><p>{resource.error}</p>
        <button className="btn btn-primary" type="button" onClick={resource.reload}>Reintentar</button>
      </section>}
      {summary && <>
        <header className="admin-heading">
          <div><span className="admin-eyebrow">Gestión de Zaas</span>
            <h1>Panel administrativo</h1>
          </div>
        </header>
        {esListado ? <AdminRegistros modulo={modulo} /> : <>
          <section className="admin-stats" aria-label="Resumen de incidencias">
            {[['Reportes totales', summary.incidencias.total], ['Por atender', summary.incidencias.pendientes],
              ['Resueltos o cerrados', summary.incidencias.resueltas]].map(([label, value]) =>
              <article className="card admin-stat" key={label}><span>{label}</span><strong>{value}</strong></article>)}
          </section>
          <div className="admin-section-heading"><h2>Espacios de administración</h2></div>
          <section className="admin-modules" aria-label="Módulos administrativos">
            {modules.map(module => <article className="card admin-module" key={module.title}>
              <h3>{module.title}</h3><p>{module.description}</p>
              {module.to.startsWith('#') ? <a href={module.to} className="btn btn-primary">{module.action}</a>
                : <Link to={module.to} className="btn btn-primary">{module.action}</Link>}
            </article>)}
          </section>
          <AdminCatalogo />
          <section className="card admin-reports" id="incidencias" aria-labelledby="admin-reports-title">
            <div className="admin-reports-heading"><div><h2 id="admin-reports-title">Incidencias recientes</h2>
              <p>Últimos cinco reportes.</p></div>
              <button className="btn btn-secondary" type="button" onClick={resource.reload}>Actualizar resumen</button></div>
            {summary.recientes.length ? <ul className="admin-report-list">{summary.recientes.map(incident =>
              <li key={incident.id}><div><strong>#{incident.id} · {incident.tipo}</strong><p>{incident.descripcion}</p>
                <small>{new Date(incident.fecha_hora).toLocaleString('es-MX')}</small></div>
                <span className="admin-status">{incident.estado?.replaceAll('_', ' ') || 'Sin estado'}</span></li>)}</ul>
              : <p className="admin-empty">No hay incidencias registradas.</p>}
          </section>
        </>}
      </>}
    </main>
  </div>;
}
