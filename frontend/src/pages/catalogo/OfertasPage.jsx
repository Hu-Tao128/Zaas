import { Link, useSearchParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { BadgeEstado, Cargando, EmptyCard, ErrorCard, Pagination } from '../../components/catalogo/CatalogoUI';
import { formatDinero, formatFecha, recortar } from './catalogoUtils';

export default function OfertasPage() {
  const { usuario } = useCatalogo();
  const [searchParams, setSearchParams] = useSearchParams();
  const paginaParam = Number(searchParams.get('page')) || 1;
  const { data, loading, error } = useApi(() => catalogoApi.ofertas({ page: paginaParam }), [paginaParam]);
  const visibles = data?.items || [];

  return (
    <>
      <h1>Ofertas de Trabajo</h1>
      <div className="catalogo-actions">
        {usuario.tipo_usuario === 'cliente' ? (
          <>
            <Link to="/catalogo/oferta/nueva" className="btn btn-primary">+ Nueva Oferta</Link>
            <Link to="/catalogo/mis-ofertas" className="btn btn-secondary">Mis ofertas</Link>
          </>
        ) : (
          <Link to="/catalogo/mis-postulaciones" className="btn btn-secondary">Mis postulaciones</Link>
        )}
      </div>

      {loading && <Cargando />}
      {error && <ErrorCard error={error} />}

      {!loading && !error && (visibles.length > 0 ? (
        <div className="catalogo-grid catalogo-grid-2">
          {visibles.map((oferta) => (
            <article key={oferta.id} className="card">
              <h4><Link to={`/catalogo/oferta/${oferta.id}`}>{oferta.titulo}</Link></h4>
              <p>{recortar(oferta.descripcion_requerimientos, 120) || 'Sin descripción'}</p>
              {oferta.presupuesto && <p><strong>Presupuesto:</strong> {formatDinero(oferta.presupuesto)}</p>}
              {oferta.fecha_entrega && <p><strong>Entrega:</strong> {formatFecha(oferta.fecha_entrega)}</p>}
              <div className="catalogo-actions">
                <BadgeEstado estado={oferta.estado} />
                {usuario.tipo_usuario === 'desarrollador' && (
                  <Link to={`/catalogo/oferta/${oferta.id}/postular`} className="btn btn-primary btn-sm">Postularme</Link>
                )}
              </div>
              <small>{formatFecha(oferta.fecha_publicacion)}</small>
            </article>
          ))}
        </div>
      ) : (
        <EmptyCard>No hay ofertas abiertas por el momento.</EmptyCard>
      ))}

      {data && (
        <Pagination
          pagina={data.page}
          totalPaginas={data.pages}
          onCambiarPagina={(nuevaPagina) => setSearchParams({ page: String(nuevaPagina) })}
        />
      )}
    </>
  );
}
