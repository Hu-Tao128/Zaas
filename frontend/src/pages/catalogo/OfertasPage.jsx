import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { BadgeEstado, Cargando, EmptyCard, ErrorCard, Pagination } from '../../components/catalogo/CatalogoUI';
import { formatDinero, formatFecha, recortar } from './catalogoUtils';

export default function OfertasPage() {
  const { usuario } = useCatalogo();
  const [searchParams, setSearchParams] = useSearchParams();
  const busquedaParam = searchParams.get('q') || '';
  const paginaParam = Number(searchParams.get('page')) || 1;
  const [busqueda, setBusqueda] = useState(busquedaParam);

  useEffect(() => {
    setBusqueda(busquedaParam);
  }, [busquedaParam]);

  const { data, loading, error } = useApi(
    () => catalogoApi.ofertas({ q: busquedaParam, page: paginaParam }),
    [busquedaParam, paginaParam],
  );
  const visibles = data?.items || [];

  function handleSubmit(event) {
    event.preventDefault();
    const params = new URLSearchParams();
    if (busqueda.trim()) params.set('q', busqueda.trim());
    setSearchParams(params);
  }

  function cambiarPagina(nuevaPagina) {
    const params = new URLSearchParams(searchParams);
    params.set('page', String(nuevaPagina));
    setSearchParams(params);
  }

  return (
    <>
      <h1>Ofertas de Trabajo</h1>

      <form className="card catalogo-search" onSubmit={handleSubmit}>
        <input
          type="search"
          value={busqueda}
          onChange={(event) => setBusqueda(event.target.value)}
          placeholder="Buscar por título o requerimientos..."
          aria-label="Buscar ofertas"
        />
        <button type="submit" className="btn btn-primary">Buscar</button>
        {busquedaParam && <Link to="/ofertas" className="btn btn-secondary">Limpiar</Link>}
      </form>

      <div className="catalogo-actions">
        {usuario.tipo_usuario === 'cliente' ? (
          <>
            <Link to="/oferta/nueva" className="btn btn-primary">+ Nueva Oferta</Link>
            <Link to="/mis-ofertas" className="btn btn-secondary">Mis ofertas</Link>
          </>
        ) : (
          <Link to="/mis-postulaciones" className="btn btn-secondary">Mis postulaciones</Link>
        )}
      </div>

      {loading && <Cargando />}
      {error && <ErrorCard error={error} />}

      {!loading && !error && (visibles.length > 0 ? (
        <div className="catalogo-grid catalogo-grid-2">
          {visibles.map((oferta) => (
            <article key={oferta.id} className="card">
              <h4><Link to={`/oferta/${oferta.id}`}>{oferta.titulo}</Link></h4>
              <p>{recortar(oferta.descripcion_requerimientos, 120) || 'Sin descripción'}</p>
              {oferta.presupuesto && <p><strong>Presupuesto:</strong> {formatDinero(oferta.presupuesto)}</p>}
              {oferta.fecha_entrega && <p><strong>Entrega:</strong> {formatFecha(oferta.fecha_entrega)}</p>}
              <div className="catalogo-actions">
                <BadgeEstado estado={oferta.estado} />
                {usuario.tipo_usuario === 'desarrollador' && (
                  <Link to={`/oferta/${oferta.id}/postular`} className="btn btn-primary btn-sm">Postularme</Link>
                )}
              </div>
              <small>{formatFecha(oferta.fecha_publicacion)}</small>
            </article>
          ))}
        </div>
      ) : (
        <EmptyCard>
          {busquedaParam
            ? `No se encontraron ofertas abiertas para "${busquedaParam}".`
            : 'No hay ofertas abiertas por el momento.'}
        </EmptyCard>
      ))}

      {data && <Pagination pagina={data.page} totalPaginas={data.pages} onCambiarPagina={cambiarPagina} />}
    </>
  );
}
