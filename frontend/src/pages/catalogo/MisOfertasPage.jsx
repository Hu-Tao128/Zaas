import { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, BadgeEstado, Cargando, EmptyCard, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { formatDinero, formatFecha, recortar } from './catalogoUtils';

export default function MisOfertasPage() {
  const location = useLocation();
  const { data, loading, error, recargar } = useApi(() => catalogoApi.misOfertas(), []);
  const [mensaje, setMensaje] = useState(location.state?.mensaje);
  const [errorAccion, setErrorAccion] = useState('');

  async function handleCerrar(oferta) {
    const confirmacion = oferta.estado === 'en_progreso'
      ? '¿Cerrar esta oferta en progreso? Solo es posible si no tiene un contrato activo.'
      : '¿Cerrar esta oferta? Dejará de aparecer en el listado público y no recibirá más postulaciones.';
    if (!window.confirm(confirmacion)) return;
    setErrorAccion('');
    try {
      const respuesta = await catalogoApi.cerrarOferta(oferta.id);
      setMensaje(respuesta.mensaje);
      recargar();
    } catch (err) {
      setMensaje('');
      setErrorAccion(err.message);
    }
  }

  if (loading && !data) return <Cargando />;
  if (error) return <ErrorCard error={error} />;
  const misOfertas = data.items;

  return (
    <>
      <h1>Mis ofertas</h1>
      {mensaje && <div className="alert alert-success">{mensaje}</div>}
      <AlertaError>{errorAccion}</AlertaError>
      <div className="catalogo-actions">
        <Link to="/catalogo/oferta/nueva" className="btn btn-primary">+ Nueva Oferta</Link>
        <Link to="/catalogo/ofertas" className="btn btn-secondary">Ver ofertas públicas</Link>
      </div>

      {misOfertas.length > 0 ? misOfertas.map((oferta) => (
        <article key={oferta.id} className="card">
          <div className="catalogo-title-row">
            <h3><Link to={`/catalogo/oferta/${oferta.id}`}>{oferta.titulo}</Link></h3>
            <BadgeEstado estado={oferta.estado} />
          </div>
          <p>{recortar(oferta.descripcion_requerimientos || 'Sin descripción', 200)}</p>
          <p>
            <strong>Presupuesto:</strong> {oferta.presupuesto ? formatDinero(oferta.presupuesto) : 'No especificado'}
            {' | '}
            <strong>Entrega:</strong> {oferta.fecha_entrega ? formatFecha(oferta.fecha_entrega) : 'Sin fecha'}
            {' | '}
            <strong>Publicada:</strong> {formatFecha(oferta.fecha_publicacion)}
          </p>
          <p><strong>Postulaciones:</strong> {oferta.num_postulaciones}</p>
          <div className="catalogo-actions">
            <Link to={`/catalogo/oferta/${oferta.id}`} className="btn btn-secondary btn-sm">Ver detalle y postulaciones</Link>
            {['abierto', 'en_progreso'].includes(oferta.estado) && (
              <button type="button" className="btn btn-danger btn-sm" onClick={() => handleCerrar(oferta)}>Cerrar</button>
            )}
          </div>
        </article>
      )) : <EmptyCard>Aún no has publicado ofertas.</EmptyCard>}
    </>
  );
}
