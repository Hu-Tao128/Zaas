import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { Cargando, ErrorCard, Pagination } from '../../components/catalogo/CatalogoUI';
import CatalogControls from '../../components/CatalogControls';
import ZaasCard from '../../components/ZaasCard';
import EmptyState from '../../components/EmptyState';

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
  const tieneFiltros = Boolean(busquedaParam || busqueda);

  function handleSubmit(event) {
    if (event?.preventDefault) event.preventDefault();
    const params = new URLSearchParams();
    if (busqueda.trim()) params.set('q', busqueda.trim());
    setSearchParams(params);
  }

  function handleLimpiar() {
    setBusqueda('');
    setSearchParams(new URLSearchParams());
  }

  function cambiarPagina(nuevaPagina) {
    const params = new URLSearchParams(searchParams);
    params.set('page', String(nuevaPagina));
    setSearchParams(params);
  }

  return (
    <div className="catalogo-page-container">
      {/* Encabezado descriptivo de la vista de ofertas */}
      <div className="catalogo-view-header">
        <h1 className="catalogo-page-title">Ofertas de Trabajo y Proyectos</h1>
        <p className="catalogo-page-subtitle">
          Contrata desarrolladores o postúlate a encargos protegidos con contratos y pagos en garantía Escrow.
        </p>
      </div>

      {/* Controles accesibles: búsqueda, filtros y botonera unificada */}
      <CatalogControls
        tipo="ofertas"
        busqueda={busqueda}
        onBusquedaChange={setBusqueda}
        onSubmit={handleSubmit}
        onLimpiar={handleLimpiar}
        tieneFiltros={tieneFiltros}
        usuario={usuario}
        totalResultados={data?.total}
      />

      {/* Indicadores de carga y error */}
      {loading && <Cargando />}
      {error && <ErrorCard error={error} />}

      {/* Grid accesible de tarjetas de ofertas con espaciado amplio */}
      {!loading && !error && (
        visibles.length > 0 ? (
          <div className="catalogo-grid catalogo-grid-3">
            {visibles.map((oferta) => (
              <ZaasCard
                key={oferta.id}
                variant="oferta"
                data={oferta}
                usuario={usuario}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            title={tieneFiltros ? 'No encontramos ofertas para tu búsqueda' : 'No hay ofertas abiertas'}
            description={
              tieneFiltros
                ? `No se encontraron ofertas de trabajo abiertas para "${busquedaParam}". Intenta con otros requerimientos o restablece la búsqueda.`
                : 'No hay ofertas abiertas por el momento. ¡Publica una nueva oferta para iniciar!'
            }
            onReset={tieneFiltros ? handleLimpiar : undefined}
            resetText="Limpiar búsqueda y ver todas"
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
