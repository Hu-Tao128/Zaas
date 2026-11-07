import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, BadgeEstado, Cargando, EmptyCard, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { CalendarIcon, ShieldCheckIcon } from '../../components/icons';
import { formatDinero, formatFecha, formatFechaHora } from './catalogoUtils';

/**
 * Extrae los requerimientos del texto libre de la oferta.
 * Si el cliente separó los puntos con saltos de línea o viñetas se respetan;
 * en caso contrario se dividen las frases para mostrarlas como lista legible.
 */
function extraerRequerimientos(texto) {
  if (!texto) return [];
  return texto
    .split(/\n|•|;/)
    .flatMap((linea) => linea.split(/(?<=\.)\s+/))
    .map((item) => item.trim())
    .filter(Boolean);
}

export default function DetalleOfertaPage() {
  const { id } = useParams();
  const { usuario } = useCatalogo();
  const navigate = useNavigate();
  const location = useLocation();
  const { data, loading, error } = useApi(() => catalogoApi.oferta(id), [id]);
  const [errorAccion, setErrorAccion] = useState('');

  if (loading) return <Cargando />;
  if (error) return <ErrorCard error={error} volverA="/ofertas" volverTexto="Volver a las ofertas" />;

  const { oferta, es_dueno: esDueno, mi_postulacion: miPostulacion } = data;
  const recibidas = data.postulaciones || [];
  const esDesarrollador = usuario.tipo_usuario === 'desarrollador';
  const requerimientos = extraerRequerimientos(oferta.descripcion_requerimientos);

  async function handleCerrar() {
    const confirmacion = oferta.estado === 'en_progreso'
      ? '¿Cerrar esta oferta en progreso? Solo es posible si no tiene un contrato activo.'
      : '¿Cerrar esta oferta? Dejará de aparecer en el listado público y no recibirá más postulaciones.';
    if (!window.confirm(confirmacion)) return;
    setErrorAccion('');
    try {
      const respuesta = await catalogoApi.cerrarOferta(oferta.id);
      navigate('/mis-ofertas', { state: { mensaje: respuesta.mensaje } });
    } catch (err) {
      setErrorAccion(err.message);
    }
  }

  return (
    <div className="proyecto-detalle-container">
      {location.state?.mensaje && (
        <div className="alert alert-success" role="status">
          {location.state.mensaje}
        </div>
      )}
      <AlertaError>{errorAccion}</AlertaError>

      <nav aria-label="Migas de pan" className="proyecto-breadcrumbs">
        <Link to="/">Catálogo</Link>
        <span aria-hidden="true">/</span>
        <Link to="/ofertas">Ofertas</Link>
        <span aria-hidden="true">/</span>
        <span className="current" aria-current="page">{oferta.titulo}</span>
      </nav>

      <div className="proyecto-detalle-layout">
        {/* Columna principal: información estructurada de la oferta */}
        <section className="proyecto-detalle-main" aria-label="Información de la oferta">
          <div className="card proyecto-header-block">
            <div className="proyecto-status-row">
              <BadgeEstado estado={oferta.estado} />
              <span className="zaas-badge zaas-badge--escrow-inline">
                <ShieldCheckIcon size={13} />
                <span>Contrato Escrow</span>
              </span>
            </div>

            <h1 className="proyecto-detalle-title">{oferta.titulo}</h1>

            <p className="oferta-header-meta">
              Publicada por{' '}
              <strong>{oferta.cliente.nombres} {oferta.cliente.apellido_paterno}</strong>
              {' · '}
              <span>{formatFecha(oferta.fecha_publicacion)}</span>
            </p>
          </div>

          <article className="card proyecto-description-card oferta-description-card">
            <h2 className="proyecto-card-subtitle">Descripción del Proyecto</h2>
            <div className="proyecto-description-text">
              {oferta.descripcion_requerimientos ? (
                oferta.descripcion_requerimientos.split('\n').map((parrafo, i) =>
                  parrafo.trim() ? <p key={i}>{parrafo}</p> : null,
                )
              ) : (
                <p className="catalogo-muted">El cliente no agregó una descripción detallada.</p>
              )}
            </div>

            <h2 className="proyecto-card-subtitle oferta-section-heading">Requerimientos Técnicos</h2>
            {requerimientos.length > 1 ? (
              <ul className="oferta-requerimientos-list">
                {requerimientos.map((requerimiento, i) => (
                  <li key={i}>{requerimiento}</li>
                ))}
              </ul>
            ) : (
              <p className="catalogo-muted">
                Los requerimientos técnicos se detallan en la descripción del proyecto.
                Puedes consultarlos con el cliente antes de postularte.
              </p>
            )}

            <h2 className="proyecto-card-subtitle oferta-section-heading">Entregables Esperados</h2>
            <p className="catalogo-muted">
              Los entregables se acordarán con el cliente al aceptar la propuesta y se
              documentarán en el contrato Escrow.
            </p>
          </article>
        </section>

        {/* Columna lateral: presupuesto, cliente y acciones */}
        <aside className="proyecto-detalle-sidebar" aria-label="Resumen y acciones de la oferta">
          <div className="card proyecto-summary-card">
            <div className="proyecto-price-section">
              <span className="proyecto-price-caption">Presupuesto Escrow</span>
              <div
                className="proyecto-price-highlight oferta-price-highlight"
                aria-label={`Presupuesto: ${oferta.presupuesto ? formatDinero(oferta.presupuesto) : 'por convenir'}`}
              >
                {oferta.presupuesto ? formatDinero(oferta.presupuesto) : 'Por convenir'}
              </div>

              <div className="escrow-guarantee-badge">
                <ShieldCheckIcon size={16} />
                <span>Fondos protegidos hasta la entrega</span>
              </div>
              <p className="escrow-guarantee-hint">
                El pago se libera al desarrollador cuando el cliente valida los entregables.
              </p>
            </div>

            <hr className="proyecto-sidebar-divider" />

            <div className="proyecto-meta-section">
              <div className="meta-item">
                <span className="sidebar-meta-label">Cliente</span>
                <span className="sidebar-meta-value">
                  {oferta.cliente.nombres} {oferta.cliente.apellido_paterno}
                </span>
              </div>
              <div className="meta-item">
                <span className="sidebar-meta-label">Publicación</span>
                <span className="sidebar-meta-value">
                  <CalendarIcon size={14} />
                  <span>{formatFecha(oferta.fecha_publicacion)}</span>
                </span>
              </div>
              {oferta.fecha_entrega && (
                <div className="meta-item">
                  <span className="sidebar-meta-label">Fecha de entrega</span>
                  <span className="sidebar-meta-value">
                    <CalendarIcon size={14} />
                    <span>{formatFecha(oferta.fecha_entrega)}</span>
                  </span>
                </div>
              )}
            </div>

            <hr className="proyecto-sidebar-divider" />

            <div className="proyecto-sidebar-actions">
              {esDesarrollador && (
                <>
                  {miPostulacion ? (
                    <Link
                      to={`/postulacion/${miPostulacion.id}`}
                      className="btn btn-secondary btn-contratar-cta"
                    >
                      Ya te postulaste ({miPostulacion.estado})
                    </Link>
                  ) : oferta.estado === 'abierto' ? (
                    <Link
                      to={`/oferta/${oferta.id}/postular`}
                      className="btn btn-primary btn-contratar-cta"
                    >
                      Postularme
                    </Link>
                  ) : oferta.estado === 'en_progreso' ? (
                    <div className="alert alert-info">
                      Esta oferta está en progreso: ya tiene un desarrollador aceptado.
                    </div>
                  ) : (
                    <div className="alert alert-warning">
                      Esta oferta está cerrada y no acepta postulaciones.
                    </div>
                  )}
                </>
              )}

              {esDueno && (
                <div className="proyecto-owner-actions">
                  {oferta.estado === 'abierto' && (
                    <Link
                      to={`/oferta/${oferta.id}/editar`}
                      className="btn btn-secondary btn-sm"
                    >
                      Editar oferta
                    </Link>
                  )}
                  {['abierto', 'en_progreso'].includes(oferta.estado) && (
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={handleCerrar}
                    >
                      Cerrar oferta
                    </button>
                  )}
                  <Link to="/mis-ofertas" className="btn btn-secondary btn-sm">
                    Mis ofertas
                  </Link>
                </div>
              )}

              <Link to="/ofertas" className="oferta-back-link">
                ← Volver a Ofertas
              </Link>
            </div>
          </div>
        </aside>
      </div>

      {esDueno && (
        <section className="oferta-postulaciones-section" aria-label="Postulaciones recibidas">
          <h2 className="oferta-postulaciones-title">
            Postulaciones recibidas ({recibidas.length})
          </h2>
          {recibidas.length > 0 ? (
            <div className="oferta-postulaciones-grid">
              {recibidas.map((postulacion) => (
                <article key={postulacion.id} className="card oferta-postulacion-card">
                  <div className="catalogo-title-row">
                    <strong>
                      {postulacion.desarrollador.nombres} {postulacion.desarrollador.apellido_paterno}
                    </strong>
                    <BadgeEstado estado={postulacion.estado} />
                  </div>
                  <p>{postulacion.detalles}</p>
                  <p>
                    <strong>Costo propuesto:</strong>{' '}
                    {formatDinero(postulacion.costo_propuesto)}
                  </p>
                  <small>{formatFechaHora(postulacion.fecha_hora)}</small>
                  <div className="catalogo-actions">
                    <Link
                      to={`/postulacion/${postulacion.id}`}
                      className="btn btn-secondary btn-sm"
                    >
                      Ver propuesta / gestionar
                    </Link>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyCard>Aún no has recibido postulaciones.</EmptyCard>
          )}
        </section>
      )}
    </div>
  );
}
