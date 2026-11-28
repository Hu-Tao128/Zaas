import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, Cargando, ErrorCard, FormField, ChipSelector } from '../../components/catalogo/CatalogoUI';

export default function ProyectoFormPage() {
  const { id } = useParams();
  const editar = Boolean(id);
  const { data, loading, error } = useApi(editar ? () => catalogoApi.proyecto(id) : null, [id]);

  if (editar && loading) return <Cargando />;
  if (editar && error) return <ErrorCard error={error} volverA="/mis-productos" volverTexto="Volver a mis productos" />;
  if (editar && !data.es_dueno) {
    return <ErrorCard error={new Error('No tienes permiso para editar este proyecto.')} volverA={`/proyecto/${id}`} volverTexto="Volver al proyecto" />;
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
    precio_negociable: Boolean(proyecto?.precio_negociable),
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

  function alternarSeleccion(campo, id) {
    setDatos((actuales) => {
      const seleccionados = actuales[campo];
      return {
        ...actuales,
        [campo]: seleccionados.includes(id)
          ? seleccionados.filter((item) => item !== id)
          : [...seleccionados, id],
      };
    });
  }

  function validar() {
    const nuevosErrores = {};
    if (datos.titulo.trim().length < 3) nuevosErrores.titulo = 'El título debe tener al menos 3 caracteres.';
    if (datos.titulo.trim().length > 200) nuevosErrores.titulo = 'El título no puede superar 200 caracteres.';
    if (datos.descripcion.trim().length < 10) nuevosErrores.descripcion = 'La descripción debe tener al menos 10 caracteres.';
    if (!datos.precio || !String(datos.precio).trim()) {
      nuevosErrores.precio = 'El precio es obligatorio.';
    } else if (!/^\d+(\.\d{1,2})?$/.test(String(datos.precio).trim())) {
      nuevosErrores.precio = 'El precio debe ser un número válido (hasta 2 decimales).';
    } else if (Number(datos.precio) <= 0) {
      nuevosErrores.precio = 'El precio debe ser mayor que 0.';
    }
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
      navigate(`/proyecto/${respuesta.proyecto.id}`, { state: { mensaje: respuesta.mensaje } });
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
          <input
            id="precio"
            name="precio"
            type="text"
            inputMode="decimal"
            placeholder="0.00"
            value={datos.precio}
            onChange={(e) => {
              const v = e.target.value;
              if (/^\d*\.?\d{0,2}$/.test(v)) actualizarCampo({ target: { name: 'precio', value: v } });
            }}
            required
          />
        </FormField>
        <div className="form-group catalogo-checkbox">
          <input
            id="precio_negociable"
            name="precio_negociable"
            type="checkbox"
            checked={datos.precio_negociable}
            onChange={actualizarCampo}
          />
          <label htmlFor="precio_negociable">Precio negociable</label>
          <small className="form-hint" style={{ display: 'block', marginLeft: '1.75rem' }}>
            Si lo desactivas, el cliente no podrá cambiar el precio al crear el contrato.
          </small>
        </div>

        <FormField
          label="Categorías"
          name="categorias_ids"
          error={errores.categorias_ids}
          hint={categorias.length ? 'Toca para seleccionar una o varias.' : 'No hay categorías registradas.'}
        >
          <ChipSelector
            opciones={categorias}
            seleccionados={datos.categorias_ids}
            onToggle={(id) => alternarSeleccion('categorias_ids', id)}
          />
        </FormField>

        <FormField
          label="Tecnologías"
          name="tecnologias_ids"
          error={errores.tecnologias_ids}
          hint={tecnologias.length ? 'Toca para seleccionar una o varias.' : 'No hay tecnologías registradas.'}
        >
          <ChipSelector
            opciones={tecnologias}
            seleccionados={datos.tecnologias_ids}
            onToggle={(id) => alternarSeleccion('tecnologias_ids', id)}
          />
        </FormField>
        <div className="form-group catalogo-checkbox">
          <input id="demo_habilitada" name="demo_habilitada" type="checkbox" checked={datos.demo_habilitada} onChange={actualizarCampo} />
          <label htmlFor="demo_habilitada">Habilitar demo</label>
        </div>
        <div className="catalogo-actions">
          <button type="submit" className="btn btn-primary" disabled={enviando}>{enviando ? 'Guardando...' : 'Guardar'}</button>
          <Link to="/mis-productos" className="btn btn-secondary">Cancelar</Link>
        </div>
      </form>
    </div>
  );
}
