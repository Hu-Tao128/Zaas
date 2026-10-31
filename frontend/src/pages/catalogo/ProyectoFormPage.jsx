import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, Cargando, ErrorCard, FormField } from '../../components/catalogo/CatalogoUI';

export default function ProyectoFormPage() {
  const { id } = useParams();
  const editar = Boolean(id);
  const { data, loading, error } = useApi(editar ? () => catalogoApi.proyecto(id) : null, [id]);

  if (editar && loading) return <Cargando />;
  if (editar && error) return <ErrorCard error={error} volverA="/catalogo/mis-productos" volverTexto="Volver a mis productos" />;
  if (editar && !data.es_dueno) {
    return <ErrorCard error={new Error('No tienes permiso para editar este proyecto.')} volverA={`/catalogo/proyecto/${id}`} volverTexto="Volver al proyecto" />;
  }
  return <ProyectoForm proyecto={data?.proyecto || null} />;
}

function ProyectoForm({ proyecto }) {
  const editar = Boolean(proyecto);
  const { categorias, tecnologias } = useCatalogo();
  const navigate = useNavigate();
  const [datos, setDatos] = useState(() => ({
    titulo: proyecto?.titulo || '',
    descripcion: proyecto?.descripcion || '',
    precio: proyecto?.precio?.toString() || '',
    categorias_ids: proyecto?.categorias.map((item) => item.id) || [],
    tecnologias_ids: proyecto?.tecnologias.map((item) => item.id) || [],
    demo_habilitada: proyecto?.demo_habilitada || false,
  }));
  const [errores, setErrores] = useState({});
  const [errorGeneral, setErrorGeneral] = useState('');
  const [enviando, setEnviando] = useState(false);

  function actualizarCampo(event) {
    const { name, value, type, checked } = event.target;
    setDatos((actuales) => ({ ...actuales, [name]: type === 'checkbox' ? checked : value }));
  }

  function actualizarSeleccion(event) {
    const valores = Array.from(event.target.selectedOptions, (option) => Number(option.value));
    setDatos((actuales) => ({ ...actuales, [event.target.name]: valores }));
  }

  function validar() {
    const nuevosErrores = {};
    if (datos.titulo.trim().length < 3) nuevosErrores.titulo = 'El título debe tener al menos 3 caracteres.';
    if (datos.titulo.trim().length > 200) nuevosErrores.titulo = 'El título no puede superar 200 caracteres.';
    if (datos.descripcion.trim().length < 10) nuevosErrores.descripcion = 'La descripción debe tener al menos 10 caracteres.';
    if (!datos.precio || Number(datos.precio) <= 0) nuevosErrores.precio = 'El precio debe ser mayor que 0.';
    setErrores(nuevosErrores);
    return Object.keys(nuevosErrores).length === 0;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorGeneral('');
    if (!validar()) return;
    setEnviando(true);
    try {
      const respuesta = editar
        ? await catalogoApi.editarProyecto(proyecto.id, datos)
        : await catalogoApi.crearProyecto(datos);
      navigate(`/catalogo/proyecto/${respuesta.proyecto.id}`, { state: { mensaje: respuesta.mensaje } });
    } catch (err) {
      setErrores(err.errores || {});
      setErrorGeneral(err.message);
      setEnviando(false);
    }
  }

  return (
    <div className="card catalogo-form-card">
      <h2>{editar ? 'Editar Proyecto' : 'Nuevo Proyecto'}</h2>
      <AlertaError>{errorGeneral}</AlertaError>
      <form onSubmit={handleSubmit} noValidate>
        <FormField label="Título" name="titulo" error={errores.titulo}>
          <input id="titulo" name="titulo" value={datos.titulo} onChange={actualizarCampo} maxLength={200} required />
        </FormField>
        <FormField label="Descripción" name="descripcion" error={errores.descripcion}>
          <textarea id="descripcion" name="descripcion" value={datos.descripcion} onChange={actualizarCampo} required />
        </FormField>
        <FormField label="Precio" name="precio" error={errores.precio}>
          <input id="precio" name="precio" type="number" min="0.01" step="0.01" value={datos.precio} onChange={actualizarCampo} required />
        </FormField>
        <FormField
          label="Categorías"
          name="categorias_ids"
          error={errores.categorias_ids}
          hint={categorias.length ? 'Mantén Ctrl (o Cmd) para elegir varias.' : 'No hay categorías registradas.'}
        >
          <select id="categorias_ids" name="categorias_ids" multiple value={datos.categorias_ids} onChange={actualizarSeleccion}>
            {categorias.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
          </select>
        </FormField>
        <FormField
          label="Tecnologías"
          name="tecnologias_ids"
          error={errores.tecnologias_ids}
          hint={tecnologias.length ? 'Mantén Ctrl (o Cmd) para elegir varias.' : 'No hay tecnologías registradas.'}
        >
          <select id="tecnologias_ids" name="tecnologias_ids" multiple value={datos.tecnologias_ids} onChange={actualizarSeleccion}>
            {tecnologias.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
          </select>
        </FormField>
        <div className="form-group catalogo-checkbox">
          <input id="demo_habilitada" name="demo_habilitada" type="checkbox" checked={datos.demo_habilitada} onChange={actualizarCampo} />
          <label htmlFor="demo_habilitada">Habilitar demo</label>
        </div>
        <div className="catalogo-actions">
          <button type="submit" className="btn btn-primary" disabled={enviando}>{enviando ? 'Guardando...' : 'Guardar'}</button>
          <Link to="/catalogo/mis-productos" className="btn btn-secondary">Cancelar</Link>
        </div>
      </form>
    </div>
  );
}
