import { Link, useLocation } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { BadgeEstado, Cargando, EmptyCard, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { formatDinero, formatFecha } from './catalogoUtils';

export default function MisPostulacionesPage() {
  const location = useLocation();
  const { data, loading, error } = useApi(() => catalogoApi.misPostulaciones(), []);

  if (loading) return <Cargando />;
  if (error) return <ErrorCard error={error} />;
  const misPostulaciones = data.items;

  return (
    <>
      <h1>Mis postulaciones</h1>
      {location.state?.mensaje && <div className="alert alert-success">{location.state.mensaje}</div>}
      <div className="catalogo-actions">
        <Link to="/catalogo/ofertas" className="btn btn-primary">Buscar ofertas</Link>
      </div>

      {misPostulaciones.length > 0 ? (
        <div className="card catalogo-table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Oferta</th>
                <th>Costo propuesto</th>
                <th>Estado</th>
                <th>Oferta</th>
                <th>Enviada</th>
                <th><span className="catalogo-sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {misPostulaciones.map((postulacion) => (
                <tr key={postulacion.id}>
                  <td><Link to={`/catalogo/oferta/${postulacion.oferta.id}`}>{postulacion.oferta.titulo}</Link></td>
                  <td>{formatDinero(postulacion.costo_propuesto)}</td>
                  <td><BadgeEstado estado={postulacion.estado} /></td>
                  <td><BadgeEstado estado={postulacion.oferta.estado} /></td>
                  <td>{formatFecha(postulacion.fecha_hora)}</td>
                  <td><Link to={`/catalogo/postulacion/${postulacion.id}`} className="btn btn-secondary btn-sm">Ver</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyCard>Aún no te has postulado a ninguna oferta.</EmptyCard>
      )}
    </>
  );
}
