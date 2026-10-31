import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, Cargando, ErrorCard, FormField } from '../../components/catalogo/CatalogoUI';

export default function DemoFormPage() {
  const { id } = useParams();
  const { usuario } = useCatalogo();
  const navigate = useNavigate();
  const { data, loading, error } = useApi(() => catalogoApi.proyecto(id), [id]);
  const [datos, setDatos] = useState({
    nombre_contacto: `${usuario.nombres} ${usuario.apellido_paterno}`.trim(),
    correo_contacto: usuario.email || '',
  });
  const [errores, setErrores] = useState({});
  const [errorGeneral, setErrorGeneral] = useState('');
  const [enviando, setEnviando] = useState(false);

  if (loading) return <Cargando />;
  if (error) return <ErrorCard error={error} />;
  const { proyecto } = data;

  function actualizarCampo(event) {
    setDatos((actuales) => ({ ...actuales, [event.target.name]: event.target.value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setErrorGeneral('');
    const nuevosErrores = {};
    if (!datos.nombre_contacto.trim()) nuevosErrores.nombre_contacto = 'El nombre de contacto es obligatorio.';
    if (!datos.correo_contacto.trim()) {
      nuevosErrores.correo_contacto = 'El correo de contacto es obligatorio.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(datos.correo_contacto)) {
      nuevosErrores.correo_contacto = 'Ingresa un correo válido.';
    }
    setErrores(nuevosErrores);
    if (Object.keys(nuevosErrores).length > 0) return;

    setEnviando(true);
    try {
      const respuesta = await catalogoApi.solicitarDemo(proyecto.id, {
        nombre_contacto: datos.nombre_contacto.trim(),
        correo_contacto: datos.correo_contacto.trim(),
      });
      navigate(`/catalogo/proyecto/${proyecto.id}`, { state: { mensaje: respuesta.mensaje } });
    } catch (err) {
      setErrores(err.errores || {});
      setErrorGeneral(err.message);
      setEnviando(false);
    }
  }

  return (
    <div className="card catalogo-form-card catalogo-demo-card">
      <h2>Solicitar Demo de: {proyecto.titulo}</h2>
      <AlertaError>{errorGeneral}</AlertaError>
      <form onSubmit={handleSubmit} noValidate>
        <FormField label="Nombre de Contacto" name="nombre_contacto" error={errores.nombre_contacto}>
          <input id="nombre_contacto" name="nombre_contacto" value={datos.nombre_contacto} onChange={actualizarCampo} maxLength={150} required />
        </FormField>
        <FormField label="Correo de Contacto" name="correo_contacto" error={errores.correo_contacto}>
          <input id="correo_contacto" name="correo_contacto" type="email" value={datos.correo_contacto} onChange={actualizarCampo} maxLength={150} required />
        </FormField>
        <div className="catalogo-actions">
          <button type="submit" className="btn btn-primary" disabled={enviando}>{enviando ? 'Enviando...' : 'Enviar Solicitud'}</button>
          <Link to={`/catalogo/proyecto/${proyecto.id}`} className="btn btn-secondary">Cancelar</Link>
        </div>
      </form>
    </div>
  );
}
