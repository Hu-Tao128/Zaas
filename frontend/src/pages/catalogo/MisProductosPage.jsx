import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, Badge, BadgeEstado, Cargando, EmptyCard, ErrorCard } from '../../components/catalogo/CatalogoUI';
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
      <h1>Mis productos</h1>
      {mensaje && <div className="alert alert-success">{mensaje}</div>}
      <AlertaError>{errorAccion}</AlertaError>
      <div className="catalogo-actions">
        <Link to="/catalogo/proyecto/nuevo" className="btn btn-primary">+ Nuevo Proyecto</Link>
        <Link to="/catalogo" className="btn btn-secondary">Ver catálogo</Link>
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
                  <td><Link to={`/catalogo/proyecto/${proyecto.id}`}>{proyecto.titulo}</Link></td>
                  <td>
                    {proyecto.categorias.map((item) => <Badge key={`c-${item.id}`} variant="info">{item.nombre}</Badge>)}
                    {proyecto.tecnologias.map((item) => <Badge key={`t-${item.id}`}>{item.nombre}</Badge>)}
                  </td>
                  <td>{formatDinero(proyecto.precio)}</td>
                  <td><BadgeEstado estado={proyecto.estado} /></td>
                  <td>{formatFecha(proyecto.fecha_publicacion)}</td>
                  <td>
                    <div className="catalogo-table-actions">
                      <Link to={`/catalogo/proyecto/${proyecto.id}/editar`} className="btn btn-secondary btn-sm">Editar</Link>
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
