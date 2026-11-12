import { useEffect, useState } from 'react';
import { useCatalogo } from '../../context/CatalogoContext';
import { pagosApi, PagoApiError } from '../../services/pagosApi';
import { formatFechaHora } from '../catalogo/catalogoUtils';
import { CargandoContratos, ErrorContratos } from '../contratos/ContratoUI';

export default function DisputasPage() {
  const { usuario } = useCatalogo();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ id_contrato: '', tipo: 'pago', descripcion: '', id_pago: '', id_entregable: '', id_incidencia: '' });
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState('');

  async function cargar() {
    setLoading(true);
    setError(null);
    try {
      const datos = await pagosApi.disputas();
      setItems(datos.items || []);
    } catch (err) {
      setError(err instanceof PagoApiError ? err : new PagoApiError('Error al cargar disputas.', 0));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
  }, []);

  async function abrirDisputa(e) {
    e.preventDefault();
    setEnviando(true);
    setMensaje('');
    try {
      await pagosApi.crearDisputa({
        id_contrato: Number(form.id_contrato),
        tipo: form.tipo,
        descripcion: form.descripcion,
        id_pago: form.id_pago ? Number(form.id_pago) : undefined,
        id_entregable: form.id_entregable ? Number(form.id_entregable) : undefined,
        id_incidencia: form.id_incidencia ? Number(form.id_incidencia) : undefined,
      });
      setMensaje('Disputa abierta.');
      setForm({ id_contrato: '', tipo: 'pago', descripcion: '', id_pago: '', id_entregable: '', id_incidencia: '' });
      await cargar();
    } catch (err) {
      setMensaje(err instanceof PagoApiError ? err.message : 'No se pudo abrir la disputa.');
    } finally {
      setEnviando(false);
    }
  }

  if (loading) return <CargandoContratos mensaje="Cargando disputas..." />;
  if (error) return <ErrorContratos error={error} onReintentar={cargar} />;

  return (
    <div className="card">
      <h2 className="contrato-section-title">Disputas</h2>
      {mensaje && <div className="alert alert-info">{mensaje}</div>}

      <form onSubmit={abrirDisputa} className="contrato-form" style={{ marginBottom: '1rem' }}>
        <label>
          Contrato
          <input type="number" value={form.id_contrato} onChange={(e) => setForm({ ...form, id_contrato: e.target.value })} required />
        </label>
        <label>
          Tipo
          <input type="text" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })} />
        </label>
        <label>
          Descripción
          <textarea value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} required />
        </label>
        <label>
          ID pago (opcional)
          <input type="number" value={form.id_pago} onChange={(e) => setForm({ ...form, id_pago: e.target.value })} />
        </label>
        <label>
          ID entregable (opcional)
          <input type="number" value={form.id_entregable} onChange={(e) => setForm({ ...form, id_entregable: e.target.value })} />
        </label>
        <label>
          ID incidencia (opcional)
          <input type="number" value={form.id_incidencia} onChange={(e) => setForm({ ...form, id_incidencia: e.target.value })} />
        </label>
        <button type="submit" className="btn btn-primary btn-sm" disabled={enviando}>
          {enviando ? 'Enviando...' : 'Abrir disputa'}
        </button>
      </form>

      {items.length === 0 ? (
        <p className="catalogo-muted">No hay disputas registradas.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Contrato</th>
              <th>Tipo</th>
              <th>Estado</th>
              <th>Fecha</th>
            </tr>
          </thead>
          <tbody>
            {items.map((d) => (
              <tr key={d.id}>
                <td>{d.id}</td>
                <td>{d.id_contrato}</td>
                <td>{d.tipo}</td>
                <td>{d.estado}</td>
                <td>{formatFechaHora(d.fecha_hora_publicacion)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {usuario?.tipo_usuario === 'admin' && (
        <p className="catalogo-muted">Para arbitrar, usa el endpoint de arbitraje con la disputa seleccionada.</p>
      )}
    </div>
  );
}
