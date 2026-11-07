import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { Cargando, ErrorCard, Pagination } from '../../components/catalogo/CatalogoUI';
import CatalogControls from '../../components/CatalogControls';
import ZaasCard from '../../components/ZaasCard';
import EmptyState from '../../components/EmptyState';

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
    if (event?.preventDefault) event.preventDefault();
    const params = new URLSearchParams();
    if (busqueda.trim()) params.set('q', busqueda.trim());
    if (categoria) params.set('categoria', categoria);
    setSearchParams(params);
  }

  function handleLimpiar() {
    setBusqueda('');
    setCategoria('');
    setSearchParams(new URLSearchParams());
  }

  function cambiarPagina(nuevaPagina) {
    const params = new URLSearchParams(searchParams);
    params.set('page', String(nuevaPagina));
    setSearchParams(params);
  }

  const visibles = data?.items || [];
  const tieneFiltros = Boolean(busquedaParam || categoriaParam || busqueda || categoria);

  return (
    <div className="catalogo-page-container">
      {/* Encabezado contextual de la vista */}
      <div className="catalogo-view-header">
        <h1 className="catalogo-page-title">Catálogo de Proyectos SaaS</h1>
        <p className="catalogo-page-subtitle">
          Descubre software validado y listo para transferir con pagos custodiados en Escrow.
        </p>
      </div>

      {/* Controles de búsqueda, filtros y botonera con flexbox/grid */}
      <CatalogControls
        tipo="proyectos"
        busqueda={busqueda}
        onBusquedaChange={setBusqueda}
        categoria={categoria}
        onCategoriaChange={setCategoria}
        categorias={categorias}
        onSubmit={handleSubmit}
        onLimpiar={handleLimpiar}
        tieneFiltros={tieneFiltros}
        usuario={usuario}
        totalResultados={data?.total}
      />

      {/* Estado de Carga y Errores */}
      {loading && <Cargando />}
      {error && <ErrorCard error={error} />}

      {/* Grid accesible de tarjetas SaaS con espaciado generoso */}
      {!loading && !error && (
        visibles.length > 0 ? (
          <div className="catalogo-grid catalogo-grid-3">
            {visibles.map((proyecto) => (
              <ZaasCard
                key={proyecto.id}
                variant="proyecto"
                data={proyecto}
                usuario={usuario}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            title={tieneFiltros ? 'No encontramos proyectos para tu búsqueda' : 'No hay proyectos disponibles'}
            description={
              tieneFiltros
                ? `No se encontraron proyectos SaaS que coincidan con "${busquedaParam || 'el filtro seleccionado'}". Puedes intentar con otras palabras clave o restablecer los filtros.`
                : 'Actualmente no hay proyectos publicados en el catálogo.'
            }
            onReset={tieneFiltros ? handleLimpiar : undefined}
            resetText="Limpiar filtros y ver todos"
          />
        )
      )}

      {/* Paginación accesible */}
      {data && (
        <Pagination
          pagina={data.page}
          totalPaginas={data.pages}
          onCambiarPagina={cambiarPagina}
        />
      )}
    </div>
  );
}
