import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, BadgeEstado, Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { formatDinero, formatFechaHora, urlContratarPostulacion } from './catalogoUtils';

export default function DetallePostulacionPage() {
  const { id } = useParams();
  const { data, loading, error, recargar } = useApi(() => catalogoApi.postulacion(id), [id]);
  const [mensaje, setMensaje] = useState('');
  const [errorAccion, setErrorAccion] = useState('');
  const [procesando, setProcesando] = useState(false);

  if (loading && !data) return <Cargando />;
  if (error) return <ErrorCard error={error} volverA="/catalogo/mis-postulaciones" volverTexto="Volver a mis postulaciones" />;

  const { postulacion, es_cliente: esCliente } = data;

  async function resolver(accion, confirmacion) {
    if (!window.confirm(confirmacion)) return;
    setErrorAccion('');
    setMensaje('');
    setProcesando(true);
    try {
      const respuesta = await accion(postulacion.id);
      setMensaje(respuesta.mensaje);
    } catch (err) {
      setErrorAccion(err.message);
    } finally {
      setProcesando(false);
      recargar();
    }
  }

  const aceptar = () => resolver(
    catalogoApi.aceptarPostulacion,
    '¿Aceptar esta postulación? La oferta pasará a en progreso y las demás postulaciones pendientes se rechazarán.',
  );
  const rechazar = () => resolver(catalogoApi.rechazarPostulacion, '¿Rechazar esta postulación?');

  return (
    <>
      {mensaje && <div className="alert alert-success">{mensaje}</div>}
      <AlertaError>{errorAccion}</AlertaError>
      <article className="card">
        <h2>Postulación a: <Link to={`/catalogo/oferta/${postulacion.oferta.id}`}>{postulacion.oferta.titulo}</Link></h2>
        <p><strong>Desarrollador:</strong> {postulacion.desarrollador.nombres} {postulacion.desarrollador.apellido_paterno}</p>
        <p>
          <strong>Estado:</strong> <BadgeEstado estado={postulacion.estado} />{' '}
          {postulacion.oferta.estado === 'cerrado' && <BadgeEstado estado="cerrado" />}
          {postulacion.oferta.estado === 'en_progreso' && <BadgeEstado estado="en_progreso" />}
        </p>
        <p><strong>Costo propuesto:</strong> {formatDinero(postulacion.costo_propuesto)}</p>
        <p><strong>Enviada:</strong> {formatFechaHora(postulacion.fecha_hora)}</p>

        <h3 className="catalogo-section-title">Detalles de la propuesta</h3>
        <p>{postulacion.detalles}</p>

        <div className="catalogo-actions">
          {esCliente && postulacion.estado === 'pendiente' && (
            <>
              <button type="button" className="btn btn-success" onClick={aceptar} disabled={procesando}>Aceptar</button>
              <button type="button" className="btn btn-danger" onClick={rechazar} disabled={procesando}>Rechazar</button>
            </>
          )}
          {esCliente && postulacion.estado === 'aceptada' && (
            <a href={urlContratarPostulacion(postulacion)} className="btn btn-primary">Contratar a este desarrollador</a>
          )}
          {esCliente ? (
            <>
              <Link to={`/catalogo/oferta/${postulacion.oferta.id}`} className="btn btn-secondary btn-sm">Volver a la oferta</Link>
              <Link to="/catalogo/mis-ofertas" className="btn btn-secondary btn-sm">Mis ofertas</Link>
            </>
          ) : (
            <Link to="/catalogo/mis-postulaciones" className="btn btn-secondary btn-sm">Mis postulaciones</Link>
          )}
        </div>
      </article>
    </>
  );
}
