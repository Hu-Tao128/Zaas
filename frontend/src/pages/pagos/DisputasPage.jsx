import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { pagosApi } from '../../services/pagosApi';
import { contratosApi } from '../../services/contratosApi';
import { formatFechaHora } from '../catalogo/catalogoUtils';
import { Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { DECISIONES_LABEL, ESTADOS_DISPUTA_LABEL, TIPOS_DISPUTA_LABEL, formatMonto, mensajeError, parseMonto } from './pagosUtils';

const TIPOS = [
  { value: 'pago', label: TIPOS_DISPUTA_LABEL.pago },
  { value: 'entregable', label: TIPOS_DISPUTA_LABEL.entregable },
  { value: 'incumplimiento', label: TIPOS_DISPUTA_LABEL.incumplimiento },
  { value: 'otro', label: TIPOS_DISPUTA_LABEL.otro },
];

function labelContrato(c) {
  const titulo = c.proyecto?.nombre || c.proyecto?.titulo || c.objeto || 'Contrato';
  const contraparte = c.contraparte?.nombre_completo || c.cliente?.nombre_completo || c.desarrollador?.nombre_completo || '';
  return contraparte ? `${titulo} — ${contraparte}` : titulo;
}

function labelPago(p, idx) {
  const estado = p.estado_escrow ? (p.estado_escrow === 'retenido' ? 'en garantía' : p.estado_escrow === 'liberado' ? 'liberado' : p.estado_escrow === 'reembolsado' ? 'reembolsado' : p.estado_escrow === 'dividido' ? 'dividido' : p.estado_escrow) : '';
  return `Depósito ${idx + 1} · ${formatMonto(p.monto, p.moneda || 'MXN')}${estado ? ` (${estado})` : ''}`;
}

export default function DisputasPage() {
  const [items, setItems] = useState([]);
  const [contratos, setContratos] = useState([]);
  const [contratoDetalle, setContratoDetalle] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [mensaje, setMensaje] = useState('');
  const [errorAccion, setErrorAccion] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [cargandoDetalle, setCargandoDetalle] = useState(false);

  const [form, setForm] = useState({ id_contrato: '', tipo: 'pago', descripcion: '', origen: '' });

  async function cargar() {
    setLoading(true);
    setError(null);
    try {
      const [disputas, contratosDatos] = await Promise.all([
        pagosApi.disputas(),
        contratosApi.listar(),
      ]);
      setItems(disputas.items || []);
      setContratos(contratosDatos.items || contratosDatos || []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { cargar(); }, []);

  useEffect(() => {
    if (!form.id_contrato) { setContratoDetalle(null); return; }
    let vigente = true;
    setCargandoDetalle(true);
    contratosApi.detalle(form.id_contrato)
      .then((res) => { if (vigente) setContratoDetalle(res.contrato || null); })
      .catch(() => { if (vigente) setContratoDetalle(null); })
      .finally(() => { if (vigente) setCargandoDetalle(false); });
    return () => { vigente = false; };
  }, [form.id_contrato]);

  const pagosContrato = useMemo(() => contratoDetalle?.pagos || [], [contratoDetalle]);
  const entregablesContrato = useMemo(() => contratoDetalle?.entregables || [], [contratoDetalle]);

  function origenesDisponibles() {
    if (!contratoDetalle) return [];
    if (form.tipo === 'pago') {
      return pagosContrato.map((p, idx) => ({ value: `pago:${p.id}`, label: labelPago(p, idx) }));
    }
    if (form.tipo === 'entregable') {
      return entregablesContrato.map((e, idx) => ({ value: `entregable:${e.id}`, label: e.titulo ? `Entregable: ${e.titulo}` : `Entregable ${idx + 1}` }));
    }
    return [];
  }

  function validarDisputa() {
    if (!form.id_contrato) return 'Selecciona el contrato relacionado.';
    if (!form.descripcion.trim()) return 'Describe el motivo de la disputa.';
    if (form.tipo === 'pago' && pagosContrato.length > 0 && !form.origen) return 'Selecciona el depósito relacionado con la disputa.';
    if (form.tipo === 'entregable' && entregablesContrato.length > 0 && !form.origen) return 'Selecciona el entregable relacionado con la disputa.';
    return null;
  }

  async function abrirDisputa(e) {
    e.preventDefault();
    if (enviando) return;
    const err = validarDisputa();
    if (err) { setErrorAccion(err); return; }
    setEnviando(true);
    setMensaje('');
    setErrorAccion('');
    const payload = {
      id_contrato: Number(form.id_contrato),
      tipo: form.tipo === 'contrato' ? 'otro' : form.tipo, // compatibilidad si backend espera tipos conocidos
      descripcion: form.descripcion.trim(),
    };
    // origen único
    if (form.origen && form.tipo === 'pago') payload.id_pago = Number(form.origen.split(':')[1]);
    if (form.origen && form.tipo === 'entregable') payload.id_entregable = Number(form.origen.split(':')[1]);
    try {
      await pagosApi.crearDisputa(payload);
      setMensaje('Disputa registrada correctamente.');
      setForm({ id_contrato: '', tipo: 'pago', descripcion: '', origen: '' });
      setContratoDetalle(null);
      await cargar();
    } catch (err2) {
      setErrorAccion(mensajeError(err2));
    } finally {
      setEnviando(false);
    }
  }

  const contratosPorId = useMemo(() => {
    const m = new Map();
    contratos.forEach((c) => m.set(c.id, c));
    return m;
  }, [contratos]);

  if (loading) return <Cargando />;
  if (error) return <ErrorCard error={{ message: mensajeError(error) }} volverA="/" volverTexto="Volver al inicio" />;

  const origenes = origenesDisponibles();

  return (
    <div className="contratos-page">
      <header className="contratos-header">
        <div>
          <h1 className="catalogo-page-title">Disputas</h1>
          <p className="catalogo-page-subtitle">Registra y da seguimiento a disputas relacionadas con tus contratos.</p>
        </div>
      </header>

      {mensaje && <div className="alert alert-success" role="status">{mensaje}</div>}
      {errorAccion && <div className="alert alert-danger" role="alert">{errorAccion}</div>}

      <form className="card contrato-form-card" onSubmit={abrirDisputa}>
        <h2 className="contrato-form-title">Nueva disputa</h2>
        <div className="form-group">
          <label htmlFor="disputa-contrato">Contrato relacionado *</label>
          <select id="disputa-contrato" value={form.id_contrato} onChange={(e) => setForm({ ...form, id_contrato: e.target.value, origen: '' })} required>
            <option value="">Selecciona un contrato...</option>
            {contratos.map((c) => (
              <option key={c.id} value={c.id}>{labelContrato(c)}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label htmlFor="disputa-tipo">Tipo de disputa</label>
          <select id="disputa-tipo" value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value, origen: '' })}>
            {TIPOS.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>
        </div>

        {form.id_contrato && (form.tipo === 'pago' || form.tipo === 'entregable') && (
          <div className="form-group">
            <label htmlFor="disputa-origen">
              {form.tipo === 'pago' ? 'Depósito relacionado' : 'Entregable relacionado'}
              {(form.tipo === 'pago' ? pagosContrato.length > 0 : entregablesContrato.length > 0) ? ' *' : ' (opcional)'}
            </label>
            {cargandoDetalle ? (
              <p className="catalogo-muted">Cargando información del contrato...</p>
            ) : origenes.length === 0 ? (
              <p className="catalogo-muted">
                {form.tipo === 'pago' ? 'No hay depósitos registrados en este contrato.' : 'No hay entregables registrados en este contrato.'}
              </p>
            ) : (
              <select id="disputa-origen" value={form.origen} onChange={(e) => setForm({ ...form, origen: e.target.value })}>
                <option value="">Selecciona una opción...</option>
                {origenes.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            )}
            <p className="form-hint">Se asocia un único origen a la disputa.</p>
          </div>
        )}

        <div className="form-group">
          <label htmlFor="disputa-descripcion">Descripción *</label>
          <textarea id="disputa-descripcion" rows="4" value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} placeholder="Describe claramente el motivo de la disputa" required />
        </div>
        <button type="submit" className="btn btn-primary" disabled={enviando}>{enviando ? 'Enviando...' : 'Registrar disputa'}</button>
      </form>

      {items.length === 0 ? (
        <div className="card contrato-empty">
          <h2 className="contrato-empty-title">Sin disputas</h2>
          <p className="contrato-empty-text">No hay disputas registradas.</p>
        </div>
      ) : (
        <div className="contratos-grid">
          {items.map((d) => {
            const c = contratosPorId.get(d.id_contrato);
            return (
              <article key={d.id} className="card contrato-card">
                <div className="contrato-card-top">
                  <span className="contrato-id">{TIPOS_DISPUTA_LABEL[d.tipo] || 'Disputa'}</span>
                  <span className="contrato-badge contrato-badge--neutral">{ESTADOS_DISPUTA_LABEL[d.estado] || d.estado}</span>
                </div>
                <h2 className="contrato-card-title">{d.contrato?.titulo || (c ? labelContrato(c) : 'Contrato asociado')}</h2>
                <p className="contrato-card-party">{d.descripcion}</p>
                <div className="contrato-card-meta">
                  <span>{formatFechaHora(d.fecha_hora_publicacion)}</span>
                </div>
                {d.arbitraje && (
                  <p className="contrato-card-party" style={{ marginTop: '.5rem' }}>
                    <strong>Resolución:</strong> {DECISIONES_LABEL[d.arbitraje.decision] || d.arbitraje.decision}
                    {d.arbitraje.notas ? ` — ${d.arbitraje.notas}` : ''}
                  </p>
                )}
                <div style={{ marginTop: '.75rem', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                  <Link to={`/disputas/${d.id}`} className="btn btn-secondary btn-sm">Ver detalle</Link>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
