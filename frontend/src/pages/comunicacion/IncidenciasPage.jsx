import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { useCatalogo } from '../../context/CatalogoContext';
import { comunicacionApi } from '../../services/comunicacionApi';
import { Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { formatFechaHora } from '../catalogo/catalogoUtils';

export default function IncidenciasPage() {
  const { usuario } = useCatalogo();
  const { state } = useLocation();
  const esAdmin = usuario.tipo_usuario === 'admin';
  const [pagina, setPagina] = useState(1);
  const [estado, setEstado] = useState('');
  const { data, loading, error, recargar } = useApi(
    () => comunicacionApi.incidencias(esAdmin, pagina, estado),
    [esAdmin, pagina, estado],
  );

  const [resoluciones, setResoluciones] = useState({});
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState(state?.mensaje || '');
  const [errorAccion, setErrorAccion] = useState('');

  async function resolverIncidencia(id) {
    if (enviando) return;
    setEnviando(true);
    setMensaje('');
    setErrorAccion('');
    try {
      await comunicacionApi.resolverIncidencia(id, resoluciones[id] || '');
      setMensaje('Incidencia resuelta.');
      setResoluciones((actual) => ({ ...actual, [id]: '' }));
      recargar();
    } catch (err) {
      setErrorAccion(err.message || 'No se pudo resolver la incidencia.');
    } finally {
      setEnviando(false);
    }
  }

  if (loading) return <Cargando />;
  if (error) {
    return <ErrorCard error={error} volverA="/" volverTexto="Volver al catálogo" />;
  }

  const items = data?.items || [];

  return (
    <div className="contratos-page">
      <header className="contratos-header">
        <div>
          <h1 className="catalogo-page-title">Incidencias</h1>
          <p className="catalogo-page-subtitle">
            {esAdmin ? 'Revisa los reportes de los usuarios y registra su resolución.'
              : 'Reporta problemas de conducta, fraude, incumplimiento o bugs del sistema.'}
          </p>
        </div>
        {esAdmin ? <Link to="/admin" className="btn btn-secondary">Volver al panel</Link>
          : <Link to="/incidencias/nueva" className="btn btn-primary">Reportar incidencia</Link>}
      </header>

      {mensaje && <div className="alert alert-success" role="status">{mensaje}</div>}
      {errorAccion && <div className="alert alert-danger" role="alert">{errorAccion}</div>}

      {esAdmin && <div className="form-group">
        <label htmlFor="incidencia-estado">Estado</label>
        <select id="incidencia-estado" value={estado} onChange={event => {
          setEstado(event.target.value);
          setPagina(1);
        }}>
          <option value="">Todos los estados</option>
          <option value="abierta">Abierta</option>
          <option value="en_proceso">En proceso</option>
          <option value="resuelta">Resuelta</option>
          <option value="cerrada">Cerrada</option>
        </select>
      </div>}

      {items.length === 0 ? (
        <div className="card contrato-empty">
          <h2 className="contrato-empty-title">Sin incidencias</h2>
          <p className="contrato-empty-text">{esAdmin ? 'No hay incidencias en esta página para el filtro seleccionado.'
            : 'No hay incidencias registradas.'}</p>
        </div>
      ) : (
        <div className="contratos-grid">
          {items.map((incidencia) => (
            <article key={incidencia.id} className="card contrato-card">
              <div className="contrato-card-top">
                <span className="contrato-id">Incidencia #{incidencia.id}</span>
                <span className="contrato-badge contrato-badge--neutral">{incidencia.estado}</span>
              </div>
              <h2 className="contrato-card-title">{incidencia.tipo_etiqueta}</h2>
              <p className="contrato-card-party">{incidencia.descripcion}</p>
              {incidencia.contrato_objeto && (
                <p className="contrato-card-party">
                  Contrato: {esAdmin ? <Link to={`/contratos/${incidencia.id_contrato}`}>{incidencia.contrato_objeto}</Link>
                    : <strong>{incidencia.contrato_objeto}</strong>}
                </p>
              )}
              <div className="contrato-card-meta">
                <span>{formatFechaHora(incidencia.fecha_hora)}</span>
              </div>
              {incidencia.resolucion && (
                <p className="contrato-card-party">
                  <strong>Resolución:</strong> {incidencia.resolucion}
                </p>
              )}
              {esAdmin && ['abierta', 'en_proceso'].includes(incidencia.estado) && (
                <div className="form-group">
                  <label htmlFor={`resolucion-${incidencia.id}`}>Resolución</label>
                  <textarea
                    id={`resolucion-${incidencia.id}`}
                    rows="2"
                    value={resoluciones[incidencia.id] || ''}
                    onChange={(e) => setResoluciones((actual) => ({
                      ...actual,
                      [incidencia.id]: e.target.value,
                    }))}
                  />
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={enviando || !(resoluciones[incidencia.id] || '').trim()}
                    onClick={() => resolverIncidencia(incidencia.id)}
                  >
                    Resolver
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
      {esAdmin && (data?.meta?.pages > 1 || pagina > 1) && (
        <nav className="contratos-header" aria-label="Páginas de incidencias">
          <button className="btn btn-secondary" type="button" disabled={pagina === 1}
            onClick={() => setPagina(pagina - 1)}>Anterior</button>
          <span>Página {pagina}</span>
          <button className="btn btn-secondary" type="button" disabled={!data?.meta?.has_next}
            onClick={() => setPagina(pagina + 1)}>Siguiente</button>
        </nav>
      )}
    </div>
  );
}
