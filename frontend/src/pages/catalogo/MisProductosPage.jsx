import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, Badge, BadgeEstado, Cargando, EmptyCard, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { PlusIcon } from '../../components/icons';
import { formatDinero, formatFecha } from './catalogoUtils';

export default function MisProductosPage() {
  const location = useLocation();
  const { data, loading, error, recargar } = useApi(() => catalogoApi.misProductos(), []);
  const [mensaje, setMensaje] = useState(location.state?.mensaje);
  const [errorAccion, setErrorAccion] = useState('');

  async function handleCerrar(id) {
    if (!window.confirm('¿Cerrar este proyecto? Dejará de aparecer en el catálogo público.')) return;
    setErrorAccion('');
    try {
      const respuesta = await catalogoApi.cerrarProyecto(id);
      setMensaje(respuesta.mensaje);
      recargar();
    } catch (err) {
      setMensaje('');
      setErrorAccion(err.message);
    }
  }

  if (loading && !data) return <Cargando />;
  if (error) return <ErrorCard error={error} />;
  const misProyectos = data.items;

  return (
    <>
      <div className="catalogo-view-header">
        <h1 className="catalogo-page-title">Mis productos</h1>
        <p className="catalogo-page-subtitle">
          Gestiona los SaaS que tienes publicados en el catálogo.
        </p>
      </div>
      {mensaje && <div className="alert alert-success">{mensaje}</div>}
      <AlertaError>{errorAccion}</AlertaError>
      <div className="catalogo-actions-bar">
        <div className="catalogo-actions-group">
          <Link to="/proyecto/nuevo" className="btn btn-primary">
            <PlusIcon />
            <span>Nuevo Proyecto</span>
          </Link>
          <Link to="/" className="btn btn-secondary">Ver catálogo</Link>
        </div>
      </div>

      {misProyectos.length > 0 ? (
        <div className="card catalogo-table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Título</th>
                <th>Categorías / Tecnologías</th>
                <th>Precio</th>
                <th>Estado</th>
                <th>Publicado</th>
                <th>Acciones</th>
              </tr>
            </thead>
            <tbody>
              {misProyectos.map((proyecto) => (
                <tr key={proyecto.id}>
                  <td><Link to={`/proyecto/${proyecto.id}`}>{proyecto.titulo}</Link></td>
                  <td>
                    {proyecto.categorias.map((item) => <Badge key={`c-${item.id}`} variant="info">{item.nombre}</Badge>)}
                    {proyecto.tecnologias.map((item) => <Badge key={`t-${item.id}`}>{item.nombre}</Badge>)}
                  </td>
                  <td>{formatDinero(proyecto.precio)}</td>
                  <td><BadgeEstado estado={proyecto.estado} /></td>
                  <td>{formatFecha(proyecto.fecha_publicacion)}</td>
                  <td>
                    <div className="catalogo-table-actions">
                      <Link to={`/proyecto/${proyecto.id}/editar`} className="btn btn-secondary btn-sm">Editar</Link>
                      {proyecto.estado === 'activo' && (
                        <button type="button" className="btn btn-danger btn-sm" onClick={() => handleCerrar(proyecto.id)}>Cerrar</button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyCard>Aún no has publicado proyectos.</EmptyCard>
      )}
    </>
  );
}
