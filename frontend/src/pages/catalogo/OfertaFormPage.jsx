import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, FormField } from '../../components/catalogo/CatalogoUI';
import { fechaMinimaLocal } from './catalogoUtils';

export default function OfertaFormPage() {
  const navigate = useNavigate();
  const [datos, setDatos] = useState({
    titulo: '',
    descripcion: '',
    presupuesto: '',
    fecha_entrega: '',
  });
  const [errores, setErrores] = useState({});
  const [errorGeneral, setErrorGeneral] = useState('');
  const [enviando, setEnviando] = useState(false);

  function actualizarCampo(event) {
    setDatos((actuales) => ({ ...actuales, [event.target.name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorGeneral('');
    const nuevosErrores = {};
    if (datos.titulo.trim().length < 3) nuevosErrores.titulo = 'El título debe tener al menos 3 caracteres.';
    if (datos.titulo.trim().length > 200) nuevosErrores.titulo = 'El título no puede superar 200 caracteres.';
    if (datos.descripcion.trim().length < 10) nuevosErrores.descripcion = 'La descripción debe tener al menos 10 caracteres.';
    if (datos.presupuesto && Number(datos.presupuesto) <= 0) nuevosErrores.presupuesto = 'El presupuesto debe ser mayor que 0.';
    if (datos.fecha_entrega && new Date(datos.fecha_entrega) <= new Date()) {
      nuevosErrores.fecha_entrega = 'La fecha de entrega debe ser futura.';
    }
    setErrores(nuevosErrores);
    if (Object.keys(nuevosErrores).length > 0) return;

    setEnviando(true);
    try {
      const respuesta = await catalogoApi.crearOferta(datos);
      navigate(`/catalogo/oferta/${respuesta.oferta.id}`, { state: { mensaje: respuesta.mensaje } });
    } catch (err) {
      setErrores(err.errores || {});
      setErrorGeneral(err.message);
      setEnviando(false);
    }
  }

  return (
    <div className="card catalogo-form-card">
      <h2>Nueva Oferta de Trabajo</h2>
      <AlertaError>{errorGeneral}</AlertaError>
      <form onSubmit={handleSubmit} noValidate>
        <FormField label="Título" name="titulo" error={errores.titulo}>
          <input id="titulo" name="titulo" value={datos.titulo} onChange={actualizarCampo} maxLength={200} required />
        </FormField>
        <FormField label="Descripción de Requerimientos" name="descripcion" error={errores.descripcion}>
          <textarea id="descripcion" name="descripcion" value={datos.descripcion} onChange={actualizarCampo} required />
        </FormField>
        <FormField label="Presupuesto" name="presupuesto" error={errores.presupuesto}>
          <input id="presupuesto" name="presupuesto" type="number" min="0.01" step="0.01" value={datos.presupuesto} onChange={actualizarCampo} />
        </FormField>
        <FormField label="Fecha de Entrega" name="fecha_entrega" error={errores.fecha_entrega}>
          <input id="fecha_entrega" name="fecha_entrega" type="datetime-local" min={fechaMinimaLocal()} value={datos.fecha_entrega} onChange={actualizarCampo} />
        </FormField>
        <div className="catalogo-actions">
          <button type="submit" className="btn btn-primary" disabled={enviando}>{enviando ? 'Publicando...' : 'Publicar Oferta'}</button>
          <Link to="/catalogo/ofertas" className="btn btn-secondary">Cancelar</Link>
        </div>
      </form>
    </div>
  );
}
