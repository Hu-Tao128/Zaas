import { Link, Navigate } from 'react-router-dom';
import Navbar from '../components/Navbar';
import { useComunicacionResource } from '../hooks/useComunicacionResource';
import './catalogo/catalogo.css';
import './admin.css';

const modules = [
  { icon: '01', title: 'Incidencias', description: 'Consulta los reportes recientes y el estado de atención.',
    label: 'Disponible', to: '#incidencias', action: 'Ver reportes recientes' },
  { icon: '02', title: 'Comunicación', description: 'Accede a tus mensajes, notificaciones y seguimiento de proyectos.',
    label: 'Disponible', to: '/comunicacion', action: 'Ir a Comunicación' },
  { icon: '03', title: 'Usuarios y permisos', description: 'Un espacio para la futura gestión de cuentas y roles del equipo.' },
  { icon: '04', title: 'Catálogo y ofertas', description: 'La administración del catálogo se integrará con el módulo de proyectos.' },
  { icon: '05', title: 'Contratos y entregables', description: 'Aquí se incorporará el seguimiento administrativo de los contratos.' },
  { icon: '06', title: 'Pagos y disputas', description: 'El control administrativo de pagos se habilitará al integrar ese módulo.' },
];

export default function AdminPage() {
  const resource = useComunicacionResource('/admin/resumen');
  const summary = resource.result?.data;
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
            <p>Hola, {summary.usuario.nombre}. Este es el estado de los reportes y los espacios de gestión.</p>
          </div>
          <span className="admin-provisional">Vista provisional</span>
        </header>
        <section className="admin-stats" aria-label="Resumen de incidencias">
          {[['Reportes totales', summary.incidencias.total], ['Por atender', summary.incidencias.pendientes],
            ['Resueltos o cerrados', summary.incidencias.resueltas]].map(([label, value]) =>
            <article className="card admin-stat" key={label}><span>{label}</span><strong>{value}</strong>
              <small>Incidencias registradas en Zaas</small></article>)}
        </section>
        <div className="admin-section-heading"><h2>Espacios de administración</h2>
          <p>Las herramientas pendientes se habilitarán conforme se integren los módulos del equipo.</p></div>
        <section className="admin-modules" aria-label="Módulos administrativos">
          {modules.map(module => <article className={`card admin-module ${module.to ? '' : 'admin-module-pending'}`} key={module.title}>
            <div className="admin-module-top"><span className="admin-module-icon" aria-hidden="true">{module.icon}</span>
              <span className={`admin-status ${module.to ? 'available' : ''}`}>{module.label || 'Próximamente'}</span></div>
            <h3>{module.title}</h3><p>{module.description}</p>
            {module.to?.startsWith('#') ? <a href={module.to} className="btn btn-primary">{module.action}</a>
              : module.to ? <Link to={module.to} className="btn btn-primary">{module.action}</Link>
                : <button className="btn btn-secondary" type="button" disabled>Pendiente de integración</button>}
          </article>)}
        </section>
        <section className="card admin-reports" id="incidencias" aria-labelledby="admin-reports-title">
          <div className="admin-reports-heading"><div><h2 id="admin-reports-title">Incidencias recientes</h2>
            <p>Últimos cinco reportes. La gestión completa se incorporará en una próxima etapa.</p></div>
            <button className="btn btn-secondary" type="button" onClick={resource.reload}>Actualizar resumen</button></div>
          {summary.recientes.length ? <ul className="admin-report-list">{summary.recientes.map(incident =>
            <li key={incident.id}><div><strong>#{incident.id} · {incident.tipo}</strong><p>{incident.descripcion}</p>
              <small>{new Date(incident.fecha_hora).toLocaleString('es-MX')}</small></div>
              <span className="admin-status">{incident.estado.replaceAll('_', ' ')}</span></li>)}</ul>
            : <div className="admin-empty"><strong>No hay incidencias registradas</strong>
              <p>Los reportes enviados por los usuarios aparecerán aquí.</p></div>}
        </section>
      </>}
    </main>
  </div>;
}
