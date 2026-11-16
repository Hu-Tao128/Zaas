import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { useCatalogo } from '../../context/CatalogoContext';
import { comunicacionApi, mensajeErrorIncidencia } from '../../services/comunicacionApi';
import { Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { formatFechaHora } from '../catalogo/catalogoUtils';

const TIPOS = [
  { value: 'acoso', label: 'Acoso' },
  { value: 'fraude', label: 'Fraude' },
  { value: 'incumplimiento', label: 'Incumplimiento' },
  { value: 'bug', label: 'Bug del sistema' },
  { value: 'otro', label: 'Otro' },
];

function etiquetaTipo(tipo) {
  return TIPOS.find((item) => item.value === tipo)?.label || 'Incidencia';
}

export default function IncidenciasPage() {
  const { usuario } = useCatalogo();
  const esAdmin = usuario?.tipo_usuario === 'admin';
  const location = useLocation();
  const { data, loading, error, recargar } = useApi(
    () => comunicacionApi.incidencias(),
    [],
  );

  const [mensaje, setMensaje] = useState(location.state?.mensaje || '');
  const [errorGeneral, setErrorGeneral] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [resoluciones, setResoluciones] = useState({});

  if (loading) return <Cargando />;
  if (error) {
    return <ErrorCard error={{ message: mensajeErrorIncidencia(error) }} volverA="/" volverTexto="Volver al catálogo" />;
  }

  const items = data?.items || [];

  async function resolverIncidencia(id) {
    if (enviando) return;
    setEnviando(true);
    setMensaje('');
    setErrorGeneral('');
    try {
      await comunicacionApi.resolverIncidencia(id, resoluciones[id] || '');
      setMensaje('Incidencia resuelta.');
      setResoluciones((actual) => ({ ...actual, [id]: '' }));
      recargar();
    } catch (err) {
      setErrorGeneral(mensajeErrorIncidencia(err));
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="contratos-page">
      <header className="contratos-header">
        <div>
          <h1 className="catalogo-page-title">Incidencias</h1>
          <p className="catalogo-page-subtitle">
            Reporta problemas de conducta, fraude, incumplimiento o bugs del sistema.
          </p>
        </div>
        <div className="catalogo-actions-group">
          <Link to="/incidencias/nueva" className="btn btn-primary">
            Reportar incidencia
          </Link>
        </div>
      </header>

      {mensaje && <div className="alert alert-success" role="status">{mensaje}</div>}
      {errorGeneral && <div className="alert alert-danger" role="alert">{errorGeneral}</div>}

      {items.length === 0 ? (
        <div className="card contrato-empty">
          <h2 className="contrato-empty-title">Sin incidencias</h2>
          <p className="contrato-empty-text">
            No hay incidencias registradas. Si necesitas reportar un problema, usa el botón
            &quot;Reportar incidencia&quot;.
          </p>
          <Link to="/incidencias/nueva" className="btn btn-primary">
            Reportar incidencia
          </Link>
        </div>
      ) : (
        <div className="contratos-grid">
          {items.map((incidencia) => (
            <article key={incidencia.id} className="card contrato-card">
              <div className="contrato-card-top">
                <span className="contrato-badge contrato-badge--neutral">
                  {incidencia.tipo_etiqueta || etiquetaTipo(incidencia.tipo)}
                </span>
                <span className="contrato-badge contrato-badge--neutral">
                  {incidencia.estado_etiqueta || incidencia.estado}
                </span>
              </div>
              <h2 className="contrato-card-title">{incidencia.descripcion}</h2>
              {incidencia.contrato_etiqueta && (
                <p className="contrato-card-party">{incidencia.contrato_etiqueta}</p>
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
                  <textarea
                    rows="2"
                    placeholder="Resolución"
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
    </div>
  );
}
