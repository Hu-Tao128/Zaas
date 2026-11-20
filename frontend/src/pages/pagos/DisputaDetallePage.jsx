import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { pagosApi } from '../../services/pagosApi';
import { formatFechaHora } from '../catalogo/catalogoUtils';
import { Cargando } from '../../components/catalogo/CatalogoUI';
import ModalPagos from './ModalPagos';
import {
  DECISIONES_LABEL,
  ESTADOS_DISPUTA_LABEL,
  RESOLUCION_LABEL,
  TIPOS_DISPUTA_LABEL,
  formatMonto,
  mensajeError,
} from './pagosUtils';

const DECISIONES = [
  { value: 'liberar', label: DECISIONES_LABEL.liberar },
  { value: 'reembolsar', label: DECISIONES_LABEL.reembolsar },
  { value: 'dividir', label: DECISIONES_LABEL.dividir },
];

function textoOrigen(disputa) {
  const origen = disputa.origen || {};
  if (origen.tipo === 'pago' && origen.pago) {
    return `Sobre un depósito de ${formatMonto(origen.pago.monto, origen.pago.moneda)} del ${formatFechaHora(origen.pago.fecha)}`;
  }
  if (origen.tipo === 'entregable' && origen.entregable) {
    return `Sobre el entregable ${origen.entregable.titulo || 'sin título'}`;
  }
  if (origen.tipo === 'incidencia' && origen.incidencia) {
    return `Sobre una incidencia: ${origen.incidencia.etiqueta || 'Incidencia'}`;
  }
  return 'Sobre el contrato en general';
}

function textoResolucion(arbitraje) {
  if (!arbitraje) return '';
  const base = RESOLUCION_LABEL[arbitraje.decision] || arbitraje.decision;
  if (arbitraje.decision === 'dividir') {
    const porcentaje = Number(arbitraje.porcentaje_desarrollador || 0);
    return `${base}: ${porcentaje}% al desarrollador y ${100 - porcentaje}% al cliente`;
  }
  return base;
}

function resumenDecision(form) {
  const etiqueta = DECISIONES.find((d) => d.value === form.decision)?.label || '';
  if (form.decision === 'dividir') {
    const porcentaje = Number(form.porcentaje || 0);
    return `Decisión: ${etiqueta}. Se repartirá ${porcentaje}% al desarrollador y ${100 - porcentaje}% al cliente.`;
  }
  return `Decisión: ${etiqueta}.`;
}

export default function DisputaDetallePage() {
  const { id } = useParams();
  const { usuario } = useCatalogo();
  const esAdmin = usuario?.tipo_usuario === 'admin';

  const [disputa, setDisputa] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const [errorAccion, setErrorAccion] = useState('');
  const [mensaje, setMensaje] = useState('');
  const [form, setForm] = useState({ decision: '', porcentaje: '', notas: '' });
  const [modalConfirmar, setModalConfirmar] = useState(false);

  async function cargar() {
    setLoading(true);
    setError(null);
    try {
      const respuesta = await pagosApi.obtenerDisputa(id);
      setDisputa(respuesta.disputa || null);
    } catch (err) {
      setError(err);
      setDisputa(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { cargar(); }, [id]);

  async function atender() {
    if (enviando) return;
    setEnviando(true);
    setErrorAccion('');
    setMensaje('');
    try {
      await pagosApi.atenderDisputa(disputa.id);
      setMensaje('Disputa tomada. Ahora está en revisión.');
      await cargar();
    } catch (err) {
      setErrorAccion(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  async function confirmarResolucion() {
    if (enviando) return;
    setEnviando(true);
    setErrorAccion('');
    setMensaje('');
    try {
      await pagosApi.crearArbitraje(disputa.id, {
        decision: form.decision,
        porcentaje_desarrollador: form.decision === 'dividir' ? Number(form.porcentaje || 0) : undefined,
        notas: (form.notas || '').trim() || undefined,
      });
      setModalConfirmar(false);
      setForm({ decision: '', porcentaje: '', notas: '' });
      setMensaje('Disputa resuelta correctamente.');
      await cargar();
    } catch (err) {
      setErrorAccion(mensajeError(err));
      setModalConfirmar(false);
    } finally {
      setEnviando(false);
    }
  }

  if (loading) return <Cargando />;

  if (error || !disputa) {
    const noEncontrada = error && (error.codigo === 'disputa_no_encontrada' || error.status === 404);
    return (
      <div className="contratos-page">
        <div className="card contrato-empty" role="alert">
          <h2 className="contrato-empty-title">
            {noEncontrada ? 'No encontramos esta disputa o no tienes acceso.' : 'No se pudo cargar la disputa.'}
          </h2>
          <p className="contrato-empty-text">
            {noEncontrada
              ? 'Es posible que la disputa no exista, que pertenezca a otro contrato o que tu sesión haya expirado.'
              : mensajeError(error)}
          </p>
          <Link to="/disputas" className="btn btn-secondary">Volver a disputas</Link>
        </div>
      </div>
    );
  }

  const estado = disputa.estado;
  const enCurso = ['abierta', 'en_revision'].includes(estado);
  const mostrarArbitraje = esAdmin && !['resuelta', 'cerrada'].includes(estado);
  const contrato = disputa.contrato || {};
  const origen = disputa.origen || {};
  const arbitraje = disputa.arbitraje;

  return (
    <div className="contratos-page">
      <nav aria-label="Migas de pan" className="proyecto-breadcrumbs">
        <Link to="/disputas">Disputas</Link>
        <span aria-hidden="true">/</span>
        <span className="current" aria-current="page">Detalle de la disputa</span>
      </nav>

      <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
        <Link to="/disputas" className="btn btn-secondary">← Volver a disputas</Link>
      </div>

      <header className="card contrato-section">
        <div className="contrato-card-top">
          <span className="contrato-id">{TIPOS_DISPUTA_LABEL[disputa.tipo] || 'Disputa'}</span>
          <span className="contrato-badge contrato-badge--neutral">{ESTADOS_DISPUTA_LABEL[estado] || estado}</span>
        </div>
        <h1 className="catalogo-page-title" style={{ marginTop: '.5rem' }}>Detalle de la disputa</h1>
        <p className="catalogo-muted">Abierta el {formatFechaHora(disputa.fecha_hora_publicacion)}</p>
      </header>

      {mensaje && <div className="alert alert-success" role="status">{mensaje}</div>}
      {errorAccion && <div className="alert alert-danger" role="alert">{errorAccion}</div>}

      {enCurso && (
        <div className="alert alert-warning" role="alert">
          Mientras esta disputa esté en curso no se pueden liberar fondos de este contrato.
        </div>
      )}

      <section className="card contrato-section" aria-label="Contrato relacionado">
        <h2 className="contrato-section-title">Contrato</h2>
        <p className="contrato-card-title">{contrato.titulo || 'Contrato'}</p>
        <p className="contrato-card-party"><strong>Cliente:</strong> {contrato.cliente?.nombre_completo || '—'}</p>
        <p className="contrato-card-party"><strong>Desarrollador:</strong> {contrato.desarrollador?.nombre_completo || '—'}</p>
        <Link to={`/contratos/${disputa.id_contrato}`} className="btn btn-secondary btn-sm">Ver contrato</Link>
      </section>

      <section className="card contrato-section" aria-label="Origen del conflicto">
        <h2 className="contrato-section-title">Origen del conflicto</h2>
        <p className="contrato-card-party">{textoOrigen(disputa)}</p>
        {origen.tipo === 'incidencia' && origen.incidencia && (
          <div style={{ marginTop: '.5rem' }}>
            <p className="contrato-card-party"><strong>Incidencia:</strong> {origen.incidencia.etiqueta}</p>
            {origen.incidencia.resumen && <p className="contrato-card-party">{origen.incidencia.resumen}</p>}
          </div>
        )}
      </section>

      <section className="card contrato-section" aria-label="Descripción de la disputa">
        <h2 className="contrato-section-title">Quién la abrió</h2>
        <p className="contrato-card-party">
          {disputa.reportante?.nombre_completo || 'Usuario'}{disputa.es_mia ? ' (Tú)' : ''}
        </p>
        <p className="contrato-card-party">{disputa.descripcion}</p>
      </section>

      {arbitraje && (
        <section className="card contrato-section" aria-label="Resolución">
          <h2 className="contrato-section-title">Resolución</h2>
          <p className="contrato-card-party"><strong>Decisión:</strong> {textoResolucion(arbitraje)}</p>
          {arbitraje.notas && <p className="contrato-card-party"><strong>Notas:</strong> {arbitraje.notas}</p>}
          <p style={{ fontSize: '.85rem', color: '#6b7280', margin: '.5rem 0 0' }}>
            {formatFechaHora(arbitraje.fecha_hora)}
          </p>
        </section>
      )}

      {mostrarArbitraje && (
        <section className="card contrato-section" aria-label="Arbitraje">
          <h2 className="contrato-section-title">Arbitraje</h2>
          {disputa.sin_atender && (
            <div style={{ marginBottom: '1rem' }}>
              <p className="contrato-card-party">Esta disputa aún no ha sido tomada por un administrador.</p>
              <button type="button" className="btn btn-secondary" disabled={enviando} onClick={atender}>
                {enviando ? 'Tomando...' : 'Tomar disputa'}
              </button>
            </div>
          )}
          <form onSubmit={(e) => { e.preventDefault(); setErrorAccion(''); setModalConfirmar(true); }}>
            <div className="form-group">
              <label htmlFor="arbitraje-decision">Decisión</label>
              <select
                id="arbitraje-decision"
                value={form.decision}
                onChange={(e) => setForm({ ...form, decision: e.target.value })}
                required
              >
                <option value="">Selecciona una decisión...</option>
                {DECISIONES.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
              </select>
            </div>
            {form.decision === 'dividir' && (
              <div className="form-group">
                <label htmlFor="arbitraje-porcentaje">Porcentaje para el desarrollador (0-100)</label>
                <input
                  id="arbitraje-porcentaje"
                  type="text"
                  inputMode="numeric"
                  value={form.porcentaje}
                  onChange={(e) => {
                    const v = e.target.value;
                    if (/^\d{0,3}$/.test(v)) {
                      setForm({ ...form, porcentaje: v === '' ? '' : String(Math.min(100, Math.max(0, Number(v)))) });
                    }
                  }}
                  placeholder="0-100"
                />
              </div>
            )}
            <div className="form-group">
              <label htmlFor="arbitraje-notas">Notas</label>
              <textarea
                id="arbitraje-notas"
                rows="2"
                value={form.notas}
                onChange={(e) => setForm({ ...form, notas: e.target.value })}
              />
            </div>
            <button type="submit" className="btn btn-primary" disabled={enviando || !form.decision}>
              {enviando ? 'Resolviendo...' : 'Resolver disputa'}
            </button>
          </form>
        </section>
      )}

      <ModalPagos
        abierto={modalConfirmar}
        titulo="Confirmar resolución"
        onCerrar={() => !enviando && setModalConfirmar(false)}
        procesando={enviando}
        cerrarEnFondo={false}
        mostrarCancelar
        pie={(
          <button type="button" className="btn btn-primary" disabled={enviando} onClick={confirmarResolucion}>
            Confirmar
          </button>
        )}
      >
        <p className="contrato-card-party">{resumenDecision(form)}</p>
        {form.notas && <p className="contrato-card-party"><strong>Notas:</strong> {form.notas}</p>}
        <p className="catalogo-muted">
          Al confirmar se aplicará la decisión y se registrará la resolución de la disputa.
        </p>
      </ModalPagos>
    </div>
  );
}
