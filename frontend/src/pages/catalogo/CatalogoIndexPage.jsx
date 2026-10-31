import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { Badge, Cargando, EmptyCard, ErrorCard, Pagination } from '../../components/catalogo/CatalogoUI';
import { formatDinero, formatFecha, recortar } from './catalogoUtils';

export default function CatalogoIndexPage() {
  const { categorias, usuario } = useCatalogo();
  const [searchParams, setSearchParams] = useSearchParams();
  const busquedaParam = searchParams.get('q') || '';
  const categoriaParam = searchParams.get('categoria') || '';
  const paginaParam = Number(searchParams.get('page')) || 1;
  const [busqueda, setBusqueda] = useState(busquedaParam);
  const [categoria, setCategoria] = useState(categoriaParam);

  useEffect(() => {
    setBusqueda(busquedaParam);
    setCategoria(categoriaParam);
  }, [busquedaParam, categoriaParam]);

  const { data, loading, error } = useApi(
    () => catalogoApi.proyectos({ q: busquedaParam, categoria: categoriaParam, page: paginaParam }),
    [busquedaParam, categoriaParam, paginaParam],
  );

  function handleSubmit(event) {
    event.preventDefault();
    const params = new URLSearchParams();
    if (busqueda.trim()) params.set('q', busqueda.trim());
    if (categoria) params.set('categoria', categoria);
    setSearchParams(params);
  }

  function cambiarPagina(nuevaPagina) {
    const params = new URLSearchParams(searchParams);
    params.set('page', String(nuevaPagina));
    setSearchParams(params);
  }

  const visibles = data?.items || [];

  return (
    <>
      <h1>Catálogo de Proyectos</h1>

      <form className="card catalogo-search" onSubmit={handleSubmit}>
        <input
          type="search"
          value={busqueda}
          onChange={(event) => setBusqueda(event.target.value)}
          placeholder="Buscar..."
          aria-label="Buscar proyectos"
        />
        <select value={categoria} onChange={(event) => setCategoria(event.target.value)} aria-label="Filtrar por categoría">
          <option value="">Todas las categorías</option>
          {categorias.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
        </select>
        <button type="submit" className="btn btn-primary">Buscar</button>
      </form>

      <div className="catalogo-actions">
        {usuario.tipo_usuario === 'desarrollador' ? (
          <>
            <Link to="/catalogo/proyecto/nuevo" className="btn btn-primary">+ Nuevo Proyecto</Link>
            <Link to="/catalogo/mis-productos" className="btn btn-secondary">Mis productos</Link>
            <Link to="/catalogo/mis-postulaciones" className="btn btn-secondary">Mis postulaciones</Link>
          </>
        ) : (
          <>
            <Link to="/catalogo/oferta/nueva" className="btn btn-secondary">+ Nueva Oferta</Link>
            <Link to="/catalogo/mis-ofertas" className="btn btn-secondary">Mis ofertas</Link>
          </>
        )}
      </div>

      {loading && <Cargando />}
      {error && <ErrorCard error={error} />}

      {!loading && !error && (visibles.length > 0 ? (
        <div className="catalogo-grid catalogo-grid-3">
          {visibles.map((proyecto) => (
            <article key={proyecto.id} className="card">
              <h4><Link to={`/catalogo/proyecto/${proyecto.id}`}>{proyecto.titulo}</Link></h4>
              <p>{recortar(proyecto.descripcion, 120) || 'Sin descripción.'}</p>
              <p>
                {proyecto.categorias.map((item) => <Badge key={`c-${item.id}`} variant="info">{item.nombre}</Badge>)}
                {proyecto.tecnologias.map((item) => <Badge key={`t-${item.id}`}>{item.nombre}</Badge>)}
              </p>
              <div className="catalogo-card-footer">
                <strong>{formatDinero(proyecto.precio)}</strong>
                {proyecto.demo_habilitada && <Badge variant="success">Demo</Badge>}
              </div>
              <small>{formatFecha(proyecto.fecha_publicacion)}</small>
            </article>
          ))}
        </div>
      ) : (
        <EmptyCard>No hay proyectos disponibles.</EmptyCard>
      ))}

      {data && <Pagination pagina={data.page} totalPaginas={data.pages} onCambiarPagina={cambiarPagina} />}
    </>
  );
}
