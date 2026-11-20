import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { comunicacionApi } from '../../services/comunicacionApi';
import { useNotificaciones } from '../../context/NotificacionesContext';
import { Cargando, ErrorCard, Pagination } from '../../components/catalogo/CatalogoUI';
import { formatFechaHora } from '../catalogo/catalogoUtils';

export default function NotificacionesPage() {
  const navigate = useNavigate();
  const { noLeidas, marcarLeida, marcarTodas } = useNotificaciones();
  const [pagina, setPagina] = useState(1);
  const [soloNoLeidas, setSoloNoLeidas] = useState(false);
  const [guardando, setGuardando] = useState(false);
  const [errorAccion, setErrorAccion] = useState('');
  const [leidasLocal, setLeidasLocal] = useState(() => new Set());
  const { data, loading, error, recargar } = useApi(
    () => comunicacionApi.notificaciones(pagina, soloNoLeidas),
    [pagina, soloNoLeidas],
  );

  useEffect(() => {
    setLeidasLocal(new Set());
  }, [pagina, soloNoLeidas]);

  const items = (data?.items || []).map((notificacion) => (
    leidasLocal.has(notificacion.id)
      ? { ...notificacion, leido: true }
      : notificacion
  ));
  const hayNoLeidas = noLeidas > 0 || items.some((notificacion) => !notificacion.leido);

  async function marcarUna(notificacion) {
    if (notificacion.leido) return true;

    setErrorAccion('');
    setLeidasLocal((prev) => new Set(prev).add(notificacion.id));

    const ok = await marcarLeida(notificacion);
    if (!ok) {
      setLeidasLocal((prev) => {
        const siguiente = new Set(prev);
        siguiente.delete(notificacion.id);
        return siguiente;
      });
      setErrorAccion('No se pudo marcar la notificación como leída.');
    }
    return ok;
  }

  function abrirNotificacion(event, notificacion) {
    event.preventDefault();
    const destino = notificacion.link || '/notificaciones';
    if (!notificacion.leido) {
      marcarUna(notificacion);
    }
    navigate(destino);
  }

  async function marcarTodasLeidas() {
    setGuardando(true);
    setErrorAccion('');
    const idsPagina = items
      .filter((notificacion) => !notificacion.leido)
      .map((notificacion) => notificacion.id);
    setLeidasLocal((prev) => {
      const siguiente = new Set(prev);
      idsPagina.forEach((id) => siguiente.add(id));
      return siguiente;
    });

    const ok = await marcarTodas();
    if (!ok) {
      setLeidasLocal(new Set());
      setErrorAccion('No se pudieron marcar las notificaciones como leídas.');
      recargar();
    }
    setGuardando(false);
  }

  if (loading) return <Cargando />;
  if (error) {
    return <ErrorCard error={error} volverA="/" volverTexto="Volver al catálogo" />;
  }

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
          <button
            type="button"
            className="btn btn-secondary"
            disabled={guardando || !hayNoLeidas}
            onClick={marcarTodasLeidas}
          >
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
          {items.map((notificacion) => {
            const contenido = (
              <>
                <h2 className="contrato-card-title">{notificacion.asunto}</h2>
                {notificacion.mensaje && (
                  <p className="contrato-card-party">{notificacion.mensaje}</p>
                )}
                <div className="contrato-card-meta">
                  <span>{formatFechaHora(notificacion.fecha_hora_creacion)}</span>
                </div>
              </>
            );

            return (
              <article
                key={notificacion.id}
                className={`card contrato-card notificacion-card ${
                  notificacion.leido ? 'is-read' : ''
                }`}
              >
                <div className="contrato-card-top">
                  <span className="contrato-id">#{notificacion.id}</span>
                  {!notificacion.leido && (
                    <span className="contrato-badge contrato-badge--pendiente">Nueva</span>
                  )}
                </div>
                {notificacion.link ? (
                  <Link
                    to={notificacion.link}
                    className="notificacion-card-link"
                    onClick={(event) => abrirNotificacion(event, notificacion)}
                  >
                    {contenido}
                  </Link>
                ) : (
                  <div className="notificacion-card-link">{contenido}</div>
                )}
                <div className="catalogo-actions-group">
                  {notificacion.link && (
                    <Link
                      to={notificacion.link}
                      className="btn btn-secondary"
                      onClick={(event) => abrirNotificacion(event, notificacion)}
                    >
                      Abrir
                    </Link>
                  )}
                  {!notificacion.leido && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => marcarUna(notificacion)}
                    >
                      Marcar como leída
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
      {data?.meta && <Pagination pagina={data.meta.page} totalPaginas={data.meta.pages} onCambiarPagina={setPagina} />}
    </div>
  );
}
