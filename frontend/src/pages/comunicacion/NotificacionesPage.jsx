import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { comunicacionApi } from '../../services/comunicacionApi';
import { Cargando, ErrorCard, Pagination } from '../../components/catalogo/CatalogoUI';
import { formatFechaHora } from '../catalogo/catalogoUtils';

export default function NotificacionesPage() {
  const [pagina, setPagina] = useState(1);
  const [soloNoLeidas, setSoloNoLeidas] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [errorAccion, setErrorAccion] = useState('');
  const { data, loading, error, recargar } = useApi(
    () => comunicacionApi.notificaciones(pagina, soloNoLeidas),
    [pagina, soloNoLeidas],
  );

  async function marcarLeidas(accion) {
    setGuardando(true);
    setErrorAccion('');
    try {
      await accion();
      if (soloNoLeidas) setPagina(1);
      recargar();
    } catch (err) {
      setErrorAccion(err.message || 'No se pudo marcar la notificación como leída.');
    } finally {
      setGuardando(false);
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
          <h1 className="catalogo-page-title">Notificaciones</h1>
          <p className="catalogo-page-subtitle">
            Actividad reciente de contratos, mensajes, calificaciones e incidencias.
          </p>
        </div>
        <div className="catalogo-actions-group">
          <label>
            <input type="checkbox" checked={soloNoLeidas} onChange={event => {
              setSoloNoLeidas(event.target.checked);
              setPagina(1);
            }} />{' '}Solo sin leer
          </label>
          <button type="button" className="btn btn-secondary" disabled={guardando || !data?.no_leidas}
            onClick={() => marcarLeidas(comunicacionApi.marcarNotificacionesLeidas)}>
            Marcar todas como leídas
          </button>
        </div>
      </header>
      {errorAccion && <p className="alert alert-danger" role="alert">{errorAccion}</p>}

      {items.length === 0 ? (
        <div className="card contrato-empty">
          <h2 className="contrato-empty-title">Sin notificaciones</h2>
          <p className="contrato-empty-text">{soloNoLeidas ? 'Estás al día con tus notificaciones.'
            : 'Aquí aparecerá la actividad de tus contratos.'}</p>
        </div>
      ) : (
        <div className="contratos-grid">
          {items.map((notificacion) => (
            <article
              key={notificacion.id}
              className={`card contrato-card ${notificacion.leido ? 'is-read' : ''}`}
            >
              <div className="contrato-card-top">
                <span className="contrato-id">#{notificacion.id}</span>
                {!notificacion.leido && (
                  <span className="contrato-badge contrato-badge--pendiente">Nueva</span>
                )}
              </div>
              <h2 className="contrato-card-title">{notificacion.asunto}</h2>
              {notificacion.mensaje && (
                <p className="contrato-card-party">{notificacion.mensaje}</p>
              )}
              <div className="contrato-card-meta">
                <span>{formatFechaHora(notificacion.fecha_hora_creacion)}</span>
              </div>
              <div className="catalogo-actions-group">
                {notificacion.link && (
                  <Link to={notificacion.link} className="btn btn-secondary">Abrir</Link>
                )}
                {!notificacion.leido && (
                  <button type="button" className="btn btn-secondary" disabled={guardando}
                    onClick={() => marcarLeidas(() => comunicacionApi.marcarNotificacionLeida(notificacion.id))}>
                    Marcar como leída
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
      {data?.meta && <Pagination pagina={data.meta.page} totalPaginas={data.meta.pages} onCambiarPagina={setPagina} />}
    </div>
  );
}
