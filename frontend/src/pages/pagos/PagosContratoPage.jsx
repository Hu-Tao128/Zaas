import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { pagosApi, PagoApiError } from '../../services/pagosApi';
import { formatDinero, formatFechaHora } from '../catalogo/catalogoUtils';
import { CargandoContratos, ErrorContratos } from '../contratos/ContratoUI';

const ESTADOS_PAGO = {
  retenido: 'Retenido',
  liberado: 'Liberado',
  reembolsado: 'Reembolsado',
  dividido: 'Dividido',
};

export default function PagosContratoPage() {
  const { id } = useParams();
  const { usuario } = useCatalogo();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({ monto: '', metodo_pago: 'simulado' });
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState('');

  async function cargar() {
    setLoading(true);
    setError(null);
    try {
      const datos = await pagosApi.listarPorContrato(id);
      setItems(datos.items || []);
    } catch (err) {
      setError(err instanceof PagoApiError ? err : new PagoApiError('Error al cargar pagos.', 0));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    cargar();
  }, [id]);

  async function registrarPago(e) {
    e.preventDefault();
    setEnviando(true);
    setMensaje('');
    try {
      await pagosApi.crear({
        id_contrato: Number(id),
        monto: form.monto ? Number(form.monto) : undefined,
        metodo_pago: form.metodo_pago,
      });
      setMensaje('Pago registrado. Los fondos quedan retenidos en escrow.');
      setForm({ monto: '', metodo_pago: 'simulado' });
      await cargar();
    } catch (err) {
      setMensaje(err instanceof PagoApiError ? err.message : 'No se pudo registrar el pago.');
    } finally {
      setEnviando(false);
    }
  }

  if (loading) return <CargandoContratos mensaje="Cargando pagos..." />;
  if (error) return <ErrorContratos error={error} onReintentar={cargar} />;

  return (
    <div className="card">
      <h2 className="contrato-section-title">Pagos del contrato #{id}</h2>
      {mensaje && <div className="alert alert-info">{mensaje}</div>}

      {usuario?.tipo_usuario === 'cliente' && (
        <form onSubmit={registrarPago} className="contrato-form" style={{ marginBottom: '1rem' }}>
          <label>
            Monto
            <input
              type="number"
              min="0.01"
              step="0.01"
              value={form.monto}
              onChange={(e) => setForm({ ...form, monto: e.target.value })}
              placeholder="Costo acordado"
            />
          </label>
          <label>
            Método
            <input
              type="text"
              value={form.metodo_pago}
              onChange={(e) => setForm({ ...form, metodo_pago: e.target.value })}
            />
          </label>
          <button type="submit" className="btn btn-primary btn-sm" disabled={enviando}>
            {enviando ? 'Registrando...' : 'Registrar pago'}
          </button>
        </form>
      )}

      {items.length === 0 ? (
        <p className="catalogo-muted">No hay pagos registrados.</p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Monto</th>
              <th>Estado</th>
              <th>Fecha</th>
              <th>Método</th>
              <th>Recibo</th>
            </tr>
          </thead>
          <tbody>
            {items.map((pago) => (
              <tr key={pago.id}>
                <td>{pago.id}</td>
                <td>{formatDinero(pago.monto)}</td>
                <td>{ESTADOS_PAGO[pago.estado_escrow] || pago.estado_escrow}</td>
                <td>{formatFechaHora(pago.fecha_pago)}</td>
                <td>{pago.metodo_pago || '-'}</td>
                <td>
                  {pago.recibo ? (
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={async () => {
                        try {
                          const datos = await pagosApi.recibo(pago.id);
                          alert(datos.recibo?.contenido_html || `Folio ${datos.recibo?.folio}`);
                        } catch (err) {
                          alert(err.message);
                        }
                      }}
                    >
                      Ver recibo
                    </button>
                  ) : (
                    '-'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
