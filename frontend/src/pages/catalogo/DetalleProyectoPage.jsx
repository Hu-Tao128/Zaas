import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, Badge, BadgeEstado, Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { formatDinero, formatFecha, urlContratarProyecto } from './catalogoUtils';

export default function DetalleProyectoPage() {
  const { id } = useParams();
  const { usuario } = useCatalogo();
  const navigate = useNavigate();
  const location = useLocation();
  const { data, loading, error } = useApi(() => catalogoApi.proyecto(id), [id]);
  const [errorAccion, setErrorAccion] = useState('');

  if (loading) return <Cargando />;
  if (error) return <ErrorCard error={error} />;

  const { proyecto, es_dueno: esDueno } = data;

  async function handleCerrar() {
    if (!window.confirm('¿Cerrar este proyecto? Dejará de aparecer en el catálogo público.')) return;
    setErrorAccion('');
    try {
      const respuesta = await catalogoApi.cerrarProyecto(proyecto.id);
      navigate('/catalogo/mis-productos', { state: { mensaje: respuesta.mensaje } });
    } catch (err) {
      setErrorAccion(err.message);
    }
  }

  return (
    <>
      {location.state?.mensaje && <div className="alert alert-success">{location.state.mensaje}</div>}
      <AlertaError>{errorAccion}</AlertaError>
      <article className="card">
        <h1>
          {proyecto.titulo}
          {proyecto.estado !== 'activo' && <span className="catalogo-inline-status"><BadgeEstado estado="cerrado" /></span>}
        </h1>
        <p><strong>Autor:</strong> {proyecto.autor.nombres} {proyecto.autor.apellido_paterno}</p>
        <p><strong>Fecha:</strong> {formatFecha(proyecto.fecha_publicacion)}</p>
        <p><strong>Precio:</strong> {formatDinero(proyecto.precio)}</p>
        {proyecto.categorias.length > 0 && (
          <p><strong>Categorías:</strong> {proyecto.categorias.map((item) => <Badge key={item.id} variant="info">{item.nombre}</Badge>)}</p>
        )}
        {proyecto.tecnologias.length > 0 && (
          <p><strong>Tecnologías:</strong> {proyecto.tecnologias.map((item) => <Badge key={item.id}>{item.nombre}</Badge>)}</p>
        )}
        {proyecto.demo_habilitada && <Badge variant="success">Demo habilitada</Badge>}

        <h3 className="catalogo-section-title">Descripción</h3>
        <p>{proyecto.descripcion || 'Sin descripción.'}</p>

        <div className="catalogo-actions">
          {proyecto.estado !== 'activo' ? (
            <div className="alert alert-warning">Este proyecto está cerrado y no está disponible.</div>
          ) : !esDueno && (
            <>
              {proyecto.demo_habilitada && (
                <Link to={`/catalogo/proyecto/${proyecto.id}/demo`} className="btn btn-primary">Solicitar Demo</Link>
              )}
              {usuario.tipo_usuario === 'cliente' && (
                <a href={urlContratarProyecto(proyecto)} className="btn btn-secondary">Contratar</a>
              )}
            </>
          )}
          {esDueno && (
            <>
              <Link to={`/catalogo/proyecto/${proyecto.id}/editar`} className="btn btn-secondary btn-sm">Editar</Link>
              {proyecto.estado === 'activo' && (
                <button type="button" className="btn btn-danger btn-sm" onClick={handleCerrar}>Cerrar proyecto</button>
              )}
              <Link to="/catalogo/mis-productos" className="btn btn-secondary btn-sm">Mis productos</Link>
            </>
          )}
          <Link to="/catalogo" className="btn btn-secondary btn-sm">Ver catálogo</Link>
        </div>
      </article>
    </>
  );
}
