import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, Cargando, EmptyCard, ErrorCard, FormField } from '../../components/catalogo/CatalogoUI';

export default function PostularPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data, loading, error } = useApi(() => catalogoApi.oferta(id), [id]);
  const [datos, setDatos] = useState({ detalles: '', costo_propuesto: '' });
  const [errores, setErrores] = useState({});
  const [errorGeneral, setErrorGeneral] = useState('');
  const [enviando, setEnviando] = useState(false);

  if (loading) return <Cargando />;
  if (error) return <ErrorCard error={error} volverA="/catalogo/ofertas" volverTexto="Volver a las ofertas" />;

  const { oferta, mi_postulacion: existente } = data;

  if (existente) {
    return (
      <EmptyCard>
        Ya te postulaste a esta oferta. <Link to={`/catalogo/postulacion/${existente.id}`}>Ver mi postulación</Link>.
      </EmptyCard>
    );
  }

  if (oferta.estado !== 'abierto') {
    return (
      <div className="card">
        <div className="alert alert-warning">Esta oferta ya no acepta postulaciones.</div>
        <Link to={`/catalogo/oferta/${oferta.id}`} className="btn btn-secondary">Volver a la oferta</Link>
      </div>
    );
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorGeneral('');
    const nuevosErrores = {};
    if (datos.detalles.trim().length < 10) nuevosErrores.detalles = 'Los detalles deben tener al menos 10 caracteres.';
    if (!datos.costo_propuesto || Number(datos.costo_propuesto) <= 0) {
      nuevosErrores.costo_propuesto = 'El costo debe ser mayor que 0.';
    }
    setErrores(nuevosErrores);
    if (Object.keys(nuevosErrores).length > 0) return;

    setEnviando(true);
    try {
      const respuesta = await catalogoApi.postular(oferta.id, datos);
      navigate('/catalogo/mis-postulaciones', { state: { mensaje: respuesta.mensaje } });
    } catch (err) {
      setErrores(err.status === 422 ? err.errores : {});
      setErrorGeneral(err.message);
      setEnviando(false);
    }
  }

  return (
    <div className="card catalogo-form-card">
      <h2>Postularse a: {oferta.titulo}</h2>
      <AlertaError>{errorGeneral}</AlertaError>
      <form onSubmit={handleSubmit} noValidate>
        <FormField label="Detalles de la Postulación" name="detalles" error={errores.detalles}>
          <textarea
            id="detalles"
            name="detalles"
            value={datos.detalles}
            onChange={(event) => setDatos((actuales) => ({ ...actuales, detalles: event.target.value }))}
            required
          />
        </FormField>
        <FormField label="Costo Propuesto" name="costo_propuesto" error={errores.costo_propuesto}>
          <input
            id="costo_propuesto"
            name="costo_propuesto"
            type="number"
            min="0.01"
            step="0.01"
            value={datos.costo_propuesto}
            onChange={(event) => setDatos((actuales) => ({ ...actuales, costo_propuesto: event.target.value }))}
            required
          />
        </FormField>
        <div className="catalogo-actions">
          <button type="submit" className="btn btn-primary" disabled={enviando}>{enviando ? 'Enviando...' : 'Enviar Postulación'}</button>
          <Link to={`/catalogo/oferta/${oferta.id}`} className="btn btn-secondary">Cancelar</Link>
        </div>
      </form>
    </div>
  );
}
