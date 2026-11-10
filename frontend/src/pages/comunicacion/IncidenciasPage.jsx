import { useState } from 'react';
import { useApi } from '../../hooks/useApi';
import { useCatalogo } from '../../context/CatalogoContext';
import { comunicacionApi } from '../../services/comunicacionApi';
import { Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { formatFechaHora } from '../catalogo/catalogoUtils';

const TIPOS = [
  { value: 'acoso', label: 'Acoso' },
  { value: 'fraude', label: 'Fraude' },
  { value: 'incumplimiento', label: 'Incumplimiento' },
  { value: 'bug', label: 'Bug del sistema' },
  { value: 'otro', label: 'Otro' },
];

export default function IncidenciasPage() {
  const { usuario } = useCatalogo();
  const esAdmin = usuario.tipo_usuario === 'admin';
  const { data, loading, error, recargar } = useApi(
    () => comunicacionApi.incidencias(),
    [],
  );

  const [form, setForm] = useState({ tipo: 'otro', descripcion: '', id_contrato: '' });
  const [resoluciones, setResoluciones] = useState({});
  const [enviando, setEnviando] = useState(false);
  const [mensaje, setMensaje] = useState('');
  const [errorAccion, setErrorAccion] = useState('');

  async function crearIncidencia(event) {
    event.preventDefault();
    if (enviando) return;
    setEnviando(true);
    setMensaje('');
    setErrorAccion('');
    try {
      const payload = {
        tipo: form.tipo,
        descripcion: form.descripcion.trim(),
      };
      if (form.id_contrato) payload.id_contrato = Number(form.id_contrato);
      await comunicacionApi.crearIncidencia(payload);
      setMensaje('Incidencia reportada.');
      setForm({ tipo: 'otro', descripcion: '', id_contrato: '' });
      recargar();
    } catch (err) {
      setErrorAccion(err.message || 'No se pudo reportar la incidencia.');
    } finally {
      setEnviando(false);
    }
  }

  async function resolverIncidencia(id) {
    if (enviando) return;
    setEnviando(true);
    setMensaje('');
    setErrorAccion('');
    try {
      await comunicacionApi.resolverIncidencia(id, resoluciones[id] || '');
      setMensaje('Incidencia resuelta.');
      setResoluciones((actual) => ({ ...actual, [id]: '' }));
      recargar();
    } catch (err) {
      setErrorAccion(err.message || 'No se pudo resolver la incidencia.');
    } finally {
      setEnviando(false);
    }
  }

  if (loading) return <Cargando />;
  if (error) {
    return <ErrorCard error={error} volverA="/" volverTexto="Volver al catálogo" />;
  }

  const items = data?.items || [];

  return (
    <div className="contratos-page">
      <header className="contratos-header">
        <div>
          <h1 className="catalogo-page-title">Incidencias</h1>
          <p className="catalogo-page-subtitle">
            Reporta problemas de conducta, fraude, incumplimiento o bugs del sistema.
          </p>
        </div>
      </header>

      {mensaje && <div className="alert alert-success" role="status">{mensaje}</div>}
      {errorAccion && <div className="alert alert-danger" role="alert">{errorAccion}</div>}

      {!esAdmin && (
        <form className="card contrato-form-card" onSubmit={crearIncidencia}>
          <h2 className="contrato-form-title">Nueva incidencia</h2>
          <div className="form-group">
            <label htmlFor="incidencia-tipo">Tipo</label>
            <select
              id="incidencia-tipo"
              value={form.tipo}
              onChange={(e) => setForm({ ...form, tipo: e.target.value })}
            >
              {TIPOS.map((tipo) => (
                <option key={tipo.value} value={tipo.value}>{tipo.label}</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label htmlFor="incidencia-contrato">ID de contrato relacionado (opcional)</label>
            <input
              id="incidencia-contrato"
              type="number"
              min="1"
              value={form.id_contrato}
              onChange={(e) => setForm({ ...form, id_contrato: e.target.value })}
              placeholder="Ej. 12"
            />
          </div>
          <div className="form-group">
            <label htmlFor="incidencia-descripcion">Descripción *</label>
            <textarea
              id="incidencia-descripcion"
              rows="3"
              value={form.descripcion}
              onChange={(e) => setForm({ ...form, descripcion: e.target.value })}
              required
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={enviando}>
            {enviando ? 'Enviando...' : 'Reportar incidencia'}
          </button>
        </form>
      )}

      {items.length === 0 ? (
        <div className="card contrato-empty">
          <h2 className="contrato-empty-title">Sin incidencias</h2>
          <p className="contrato-empty-text">No hay incidencias registradas.</p>
        </div>
      ) : (
        <div className="contratos-grid">
          {items.map((incidencia) => (
            <article key={incidencia.id} className="card contrato-card">
              <div className="contrato-card-top">
                <span className="contrato-id">Incidencia #{incidencia.id}</span>
                <span className="contrato-badge contrato-badge--neutral">{incidencia.estado}</span>
              </div>
              <h2 className="contrato-card-title">{incidencia.tipo}</h2>
              <p className="contrato-card-party">{incidencia.descripcion}</p>
              {incidencia.contrato_objeto && (
                <p className="contrato-card-party">
                  Contrato: <strong>{incidencia.contrato_objeto}</strong>
                </p>
              )}
              <div className="contrato-card-meta">
                <span>{formatFechaHora(incidencia.fecha_hora)}</span>
              </div>
              {incidencia.resolucion && (
                <p className="contrato-card-party">
                  <strong>Resolución:</strong> {incidencia.resolucion}
                </p>
              )}
              {esAdmin && ['abierta', 'en_proceso'].includes(incidencia.estado) && (
                <div className="form-group">
                  <textarea
                    rows="2"
                    placeholder="Resolución"
                    value={resoluciones[incidencia.id] || ''}
                    onChange={(e) => setResoluciones((actual) => ({
                      ...actual,
                      [incidencia.id]: e.target.value,
                    }))}
                  />
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    disabled={enviando || !(resoluciones[incidencia.id] || '').trim()}
                    onClick={() => resolverIncidencia(incidencia.id)}
                  >
                    Resolver
                  </button>
                </div>
              )}
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
