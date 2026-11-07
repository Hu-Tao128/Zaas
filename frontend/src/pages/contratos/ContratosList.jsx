import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { contratosApi } from '../../services/contratosApi';
import { PlusIcon, ShieldCheckIcon } from '../../components/icons';
import { formatDinero, formatFecha } from '../catalogo/catalogoUtils';
import {
  CargandoContratos,
  ErrorContratos,
  EscrowBadge,
  EstadoContratoBadge,
  RolBadge,
} from './ContratoUI';

const FILTROS = [
  { id: 'todos', label: 'Todos' },
  { id: 'firma', label: 'Por firmar' },
  { id: 'activos', label: 'Activos' },
  { id: 'finalizados', label: 'Finalizados' },
];

function coincideFiltro(contrato, filtro) {
  if (filtro === 'firma') return ['borrador', 'pendiente'].includes(contrato.estado);
  if (filtro === 'activos') return ['aceptado', 'en_progreso', 'entregado'].includes(contrato.estado);
  if (filtro === 'finalizados') return ['finalizado', 'cancelado'].includes(contrato.estado);
  return true;
}

export default function ContratosList() {
  const { data, loading, error, recargar } = useApi(() => contratosApi.listar(), []);
  const [filtro, setFiltro] = useState('todos');

  const contratos = data?.items || [];

  const visibles = useMemo(
    () => contratos.filter((contrato) => coincideFiltro(contrato, filtro)),
    [contratos, filtro],
  );

  const resumen = useMemo(() => {
    const pendientes = contratos.filter((c) => ['borrador', 'pendiente'].includes(c.estado)).length;
    const enCustodia = contratos.reduce((total, c) => total + (c.escrow?.monto_retenido || 0), 0);
    const finalizados = contratos.filter((c) => c.estado === 'finalizado').length;
    return { total: contratos.length, pendientes, enCustodia, finalizados };
  }, [contratos]);

  return (
    <div className="contratos-page">
      <header className="contratos-header">
        <div>
          <h1 className="catalogo-page-title">Contratos Escrow</h1>
          <p className="catalogo-page-subtitle">
            Gestiona los acuerdos de compra de SaaS y encargos de desarrollo protegidos por la
            custodia de fondos de Zaas.
          </p>
        </div>

        <div className="catalogo-actions-group">
          <Link to="/contratos/nuevo" className="btn btn-primary">
            <PlusIcon />
            <span>Nuevo contrato</span>
          </Link>
        </div>
      </header>

      {loading && <CargandoContratos />}
      {error && <ErrorContratos error={error} onReintentar={recargar} />}

      {!loading && !error && (
        <>
          <section className="contratos-stats" aria-label="Resumen de contratos">
            <article className="contrato-stat">
              <span className="contrato-stat-label">Total</span>
              <strong className="contrato-stat-value">{resumen.total}</strong>
            </article>
            <article className="contrato-stat">
              <span className="contrato-stat-label">Por firmar</span>
              <strong className="contrato-stat-value contrato-stat-value--warning">{resumen.pendientes}</strong>
            </article>
            <article className="contrato-stat">
              <span className="contrato-stat-label">En custodia</span>
              <strong className="contrato-stat-value contrato-stat-value--brand">
                {formatDinero(resumen.enCustodia)}
              </strong>
            </article>
            <article className="contrato-stat">
              <span className="contrato-stat-label">Finalizados</span>
              <strong className="contrato-stat-value contrato-stat-value--success">{resumen.finalizados}</strong>
            </article>
          </section>

          <div className="contratos-toolbar" role="toolbar" aria-label="Filtrar contratos por estado">
            {FILTROS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`contratos-filter ${filtro === item.id ? 'is-active' : ''}`}
                aria-pressed={filtro === item.id}
                onClick={() => setFiltro(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>

          {visibles.length > 0 ? (
            <div className="contratos-grid">
              {visibles.map((contrato) => (
                <article key={contrato.id} className="card contrato-card">
                  <div className="contrato-card-top">
                    <div className="contrato-card-id">
                      <span className="contrato-id">Contrato #{contrato.id}</span>
                      <RolBadge rol={contrato.rol} />
                    </div>
                    <EstadoContratoBadge estado={contrato.estado} />
                  </div>

                  <h2 className="contrato-card-title">
                    <Link to={`/contratos/${contrato.id}`}>{contrato.objeto}</Link>
                  </h2>

                  <p className="contrato-card-party">
                    {contrato.rol === 'cliente' ? 'Desarrollador' : 'Cliente'}:{' '}
                    <strong>{contrato.contraparte?.nombre_completo || 'No disponible'}</strong>
                  </p>

                  <div className="contrato-card-escrow">
                    <div>
                      <span className="contrato-escrow-label">Monto Escrow</span>
                      <strong className="contrato-escrow-amount">
                        {formatDinero(contrato.costo_acordado)}
                      </strong>
                    </div>
                    <EscrowBadge estado={contrato.escrow?.estado} />
                  </div>

                  <div className="contrato-card-meta">
                    <span>
                      Firmas: {Number(contrato.firmas?.cliente) + Number(contrato.firmas?.desarrollador)}/2
                    </span>
                    <span>{formatFecha(contrato.fecha_creacion)}</span>
                  </div>

                  <Link
                    to={`/contratos/${contrato.id}`}
                    className="btn btn-secondary contrato-card-cta"
                  >
                    Ver contrato
                  </Link>
                </article>
              ))}
            </div>
          ) : (
            <div className="card contrato-empty">
              <div className="contrato-empty-icon" aria-hidden="true">
                <ShieldCheckIcon size={42} strokeWidth={1.5} />
              </div>
              <h2 className="contrato-empty-title">
                {contratos.length === 0 ? 'Aún no tienes contratos' : 'No hay contratos en este filtro'}
              </h2>
              <p className="contrato-empty-text">
                {contratos.length === 0
                  ? 'Crea una propuesta de contrato para comenzar a trabajar con fondos protegidos en Escrow.'
                  : 'Cambia el filtro para ver otros contratos.'}
              </p>
              {contratos.length === 0 && (
                <Link to="/contratos/nuevo" className="btn btn-primary">
                  <PlusIcon />
                  <span>Crear mi primer contrato</span>
                </Link>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
