import { Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { comunicacionApi } from '../../services/comunicacionApi';
import { Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { formatFechaHora } from '../catalogo/catalogoUtils';

export default function NotificacionesPage() {
  const { data, loading, error, recargar } = useApi(
    () => comunicacionApi.notificaciones(),
    [],
  );

  async function marcarLeidas() {
    try {
      await comunicacionApi.marcarNotificacionesLeidas();
      recargar();
    } catch {
      // Si falla, la lista se mantiene; el usuario puede reintentar.
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
          <button type="button" className="btn btn-secondary" onClick={marcarLeidas}>
            Marcar todas como leídas
          </button>
        </div>
      </header>

      {items.length === 0 ? (
        <div className="card contrato-empty">
          <h2 className="contrato-empty-title">Sin notificaciones</h2>
          <p className="contrato-empty-text">Aquí aparecerá la actividad de tus contratos.</p>
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
              {notificacion.link && (
                <Link to={notificacion.link} className="btn btn-secondary contrato-card-cta">
                  Abrir
                </Link>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
