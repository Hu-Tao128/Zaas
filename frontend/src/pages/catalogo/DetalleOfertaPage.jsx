import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, BadgeEstado, Cargando, EmptyCard, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { formatDinero, formatFecha, formatFechaHora } from './catalogoUtils';

export default function DetalleOfertaPage() {
  const { id } = useParams();
  const { usuario } = useCatalogo();
  const navigate = useNavigate();
  const location = useLocation();
  const { data, loading, error } = useApi(() => catalogoApi.oferta(id), [id]);
  const [errorAccion, setErrorAccion] = useState('');

  if (loading) return <Cargando />;
  if (error) return <ErrorCard error={error} volverA="/catalogo/ofertas" volverTexto="Volver a las ofertas" />;

  const { oferta, es_dueno: esDueno, mi_postulacion: miPostulacion } = data;
  const recibidas = data.postulaciones || [];

  async function handleCerrar() {
    const confirmacion = oferta.estado === 'en_progreso'
      ? '¿Cerrar esta oferta en progreso? Solo es posible si no tiene un contrato activo.'
      : '¿Cerrar esta oferta? Dejará de aparecer en el listado público y no recibirá más postulaciones.';
    if (!window.confirm(confirmacion)) return;
    setErrorAccion('');
    try {
      const respuesta = await catalogoApi.cerrarOferta(oferta.id);
      navigate('/catalogo/mis-ofertas', { state: { mensaje: respuesta.mensaje } });
    } catch (err) {
      setErrorAccion(err.message);
    }
  }

  return (
    <>
      {location.state?.mensaje && <div className="alert alert-success">{location.state.mensaje}</div>}
      <AlertaError>{errorAccion}</AlertaError>
      <article className="card">
        <h1>
          {oferta.titulo}
          {oferta.estado === 'cerrado' && <span className="catalogo-inline-status"><BadgeEstado estado="cerrado" /></span>}
        </h1>
        <p><strong>Cliente:</strong> {oferta.cliente.nombres} {oferta.cliente.apellido_paterno}</p>
        <p><strong>Estado:</strong> <BadgeEstado estado={oferta.estado} /></p>
        <p><strong>Presupuesto:</strong> {oferta.presupuesto ? formatDinero(oferta.presupuesto) : 'No especificado'}</p>
        {oferta.fecha_entrega && <p><strong>Fecha de entrega:</strong> {formatFecha(oferta.fecha_entrega)}</p>}

        <h3 className="catalogo-section-title">Requerimientos</h3>
        <p>{oferta.descripcion_requerimientos || 'Sin descripción.'}</p>

        <div className="catalogo-actions">
          {usuario.tipo_usuario === 'desarrollador' && (
            <>
              {miPostulacion ? (
                <Link to={`/catalogo/postulacion/${miPostulacion.id}`} className="btn btn-secondary">
                  Ya te postulaste ({miPostulacion.estado})
                </Link>
              ) : oferta.estado === 'abierto' ? (
                <Link to={`/catalogo/oferta/${oferta.id}/postular`} className="btn btn-primary">Postularme</Link>
              ) : oferta.estado === 'en_progreso' ? (
                <div className="alert alert-info">Esta oferta está en progreso: ya tiene un desarrollador aceptado.</div>
              ) : (
                <div className="alert alert-warning">Esta oferta está cerrada y no acepta postulaciones.</div>
              )}
              <Link to="/catalogo/mis-postulaciones" className="btn btn-secondary btn-sm">Mis postulaciones</Link>
            </>
          )}
          {esDueno && (
            <>
              {['abierto', 'en_progreso'].includes(oferta.estado) && (
                <button type="button" className="btn btn-danger btn-sm" onClick={handleCerrar}>Cerrar oferta</button>
              )}
              <Link to="/catalogo/mis-ofertas" className="btn btn-secondary btn-sm">Mis ofertas</Link>
            </>
          )}
          <Link to="/catalogo/ofertas" className="btn btn-secondary btn-sm">Ver ofertas</Link>
        </div>
      </article>

      {esDueno && (
        <section>
          <h3>Postulaciones recibidas ({recibidas.length})</h3>
          {recibidas.length > 0 ? recibidas.map((postulacion) => (
            <article key={postulacion.id} className="card">
              <p>
                <strong>{postulacion.desarrollador.nombres} {postulacion.desarrollador.apellido_paterno}</strong>{' '}
                <BadgeEstado estado={postulacion.estado} />
              </p>
              <p>{postulacion.detalles}</p>
              <p><strong>Costo propuesto:</strong> {formatDinero(postulacion.costo_propuesto)}</p>
              <small>{formatFechaHora(postulacion.fecha_hora)}</small>
              <div className="catalogo-actions catalogo-section-title">
                <Link to={`/catalogo/postulacion/${postulacion.id}`} className="btn btn-secondary btn-sm">Ver propuesta / gestionar</Link>
              </div>
            </article>
          )) : <EmptyCard>Aún no has recibido postulaciones.</EmptyCard>}
        </section>
      )}
    </>
  );
}
