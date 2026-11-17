import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { pagosApi } from '../../services/pagosApi';
import { contratosApi } from '../../services/contratosApi';
import { formatFechaHora } from '../catalogo/catalogoUtils';
import { Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { ESTADOS_PAGO_LABEL, formatMonto, mensajeError, parseMonto } from './pagosUtils';

function Modal({ titulo, abierto, onCerrar, children, ancho = 560 }) {
  if (!abierto) return null;
  return (
    <div role="dialog" aria-modal="true" aria-label={titulo} style={{ position: 'fixed', inset: 0, zIndex: 1000 }}>
      <button type="button" aria-label="Cerrar" onClick={onCerrar} style={{ position: 'absolute', inset: 0, background: 'rgba(15,23,42,.45)', border: 0 }} />
      <div className="card" style={{ position: 'relative', maxWidth: ancho, margin: '6vh auto', padding: '1rem 1.25rem', maxHeight: '88vh', overflow: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', marginBottom: '.75rem' }}>
          <h2 className="contrato-form-title" style={{ margin: 0 }}>{titulo}</h2>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onCerrar}>Cerrar</button>
        </div>
        {children}
      </div>
    </div>
  );
}

function CampoMonto({ id, label, value, onChange, placeholder = '0.00' }) {
  return (
    <div className="form-group">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        inputMode="decimal"
        placeholder={placeholder}
        value={value}
        onChange={(e) => {
          const v = e.target.value;
          if (/^\d*\.?\d{0,2}$/.test(v)) onChange(v);
        }}
      />
    </div>
  );
}

export default function PagosContratoPage() {
  const { id } = useParams();
  const { usuario } = useCatalogo();
  const [items, setItems] = useState([]);
  const [resumen, setResumen] = useState(null);
  const [contrato, setContrato] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [mensaje, setMensaje] = useState('');
  const [errorAccion, setErrorAccion] = useState('');
  const [enviando, setEnviando] = useState(false);

  const [modalDeposito, setModalDeposito] = useState(false);
  const [formDeposito, setFormDeposito] = useState({ monto: '', numero: '', vencimiento: '', cvc: '' });
  const [pagoActual, setPagoActual] = useState(null);
  const [codigo, setCodigo] = useState('');

  const [modalLiberar, setModalLiberar] = useState(null); // pago
  const [formLiberar, setFormLiberar] = useState({ monto: '', id_entregable: '', motivo: '' });

  const [modalRecibo, setModalRecibo] = useState(null); // {pago, recibo}

  const esCliente = usuario?.tipo_usuario === 'cliente';
  const esDev = usuario?.tipo_usuario === 'desarrollador';
  const esAdmin = usuario?.tipo_usuario === 'admin';

  async function cargar(silencioso = false) {
    if (!silencioso) setLoading(true);
    setError(null);
    try {
      const [pagosRes, resumenRes, contratoRes] = await Promise.all([
        pagosApi.listarPorContrato(id),
        pagosApi.resumenContrato(id),
        contratosApi.detalle(id),
      ]);
      setItems(pagosRes.items || []);
      setResumen(resumenRes.resumen || null);
      setContrato(contratoRes.contrato || null);
      return { pagos: pagosRes.items || [] };
    } catch (err) {
      setError(err);
      return null;
    } finally {
      if (!silencioso) setLoading(false);
    }
  }

  useEffect(() => { cargar(); }, [id]);

  const entregablesAprobados = useMemo(
    () => (contrato?.entregables || []).filter((e) => e.estado === 'aprobado'),
    [contrato],
  );

  const puedeDepositar = useMemo(() => {
    if (!esCliente || !contrato || !resumen) return false;
    if (!['aceptado', 'en_progreso', 'entregado'].includes(contrato.estado)) return false;
    return parseMonto(resumen.por_depositar) > 0;
  }, [esCliente, contrato, resumen]);

  function validarMonto(valor, etiqueta = 'El monto') {
    if (!valor || !String(valor).trim()) return `${etiqueta} es obligatorio.`;
    if (!/^\d+(\.\d{1,2})?$/.test(String(valor).trim())) return `${etiqueta} debe ser un número válido (hasta 2 decimales).`;
    if (Number(valor) <= 0) return `${etiqueta} debe ser mayor a 0.`;
    return null;
  }

  function validarDeposito() {
    const errMonto = validarMonto(formDeposito.monto, 'El monto a depositar');
    if (errMonto) return errMonto;
    if (resumen && Number(formDeposito.monto) > parseMonto(resumen.por_depositar) + 0.0001) {
      return 'El monto supera el importe pendiente por depositar.';
    }
    const numero = formDeposito.numero.replace(/\s/g, '');
    if (!/^\d{13,19}$/.test(numero)) return 'El número de tarjeta no es válido.';
    if (!/^\d{2}\/\d{2}$/.test(formDeposito.vencimiento)) return 'El vencimiento debe tener formato MM/AA.';
    if (!/^\d{3,4}$/.test(formDeposito.cvc)) return 'El código de seguridad no es válido.';
    return null;
  }

  async function registrarDeposito(e) {
    e.preventDefault();
    const err = validarDeposito();
    if (err) { setErrorAccion(err); return; }
    setEnviando(true);
    setMensaje('');
    setErrorAccion('');
    const idempotencyKey = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    try {
      const datos = await pagosApi.crear({
        id_contrato: Number(id),
        monto: Number(formDeposito.monto),
        tarjeta: {
          numero: formDeposito.numero.replace(/\s/g, ''),
          vencimiento: formDeposito.vencimiento,
          cvc: formDeposito.cvc,
        },
      }, idempotencyKey);
      setMensaje('Solicitud de depósito enviada. Esperando confirmación del procesamiento.');
      setPagoActual(datos.pago);
      setFormDeposito({ monto: '', numero: '', vencimiento: '', cvc: '' });
      setModalDeposito(false);
      await cargar(true);
      let intentos = 0;
      const intervalo = setInterval(async () => {
        intentos += 1;
        try {
          const actualizado = await pagosApi.obtener(datos.pago.id);
          setPagoActual(actualizado.pago);
          if (actualizado.pago.estado_escrow !== 'pendiente' || intentos >= 15) {
            clearInterval(intervalo);
            await cargar(true);
          }
        } catch {
          clearInterval(intervalo);
        }
      }, 2000);
    } catch (err2) {
      setErrorAccion(mensajeError(err2));
    } finally {
      setEnviando(false);
    }
  }

  async function verificar() {
    if (!pagoActual) return;
    setEnviando(true);
    setErrorAccion('');
    try {
      const datos = await pagosApi.verificar(pagoActual.id, codigo);
      setPagoActual(datos.pago);
      setMensaje('Pago verificado correctamente.');
      setCodigo('');
      await cargar(true);
    } catch (err) {
      setErrorAccion(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  function abrirModalLiberar(pago) {
    setErrorAccion('');
    setFormLiberar({ monto: pago.disponible || '', id_entregable: '', motivo: '' });
    setModalLiberar(pago);
  }

  async function confirmarLiberacion(e) {
    e.preventDefault();
    if (!modalLiberar) return;
    const errMonto = validarMonto(formLiberar.monto, 'El monto a liberar');
    if (errMonto) { setErrorAccion(errMonto); return; }
    if (Number(formLiberar.monto) > parseMonto(modalLiberar.disponible) + 0.0001) {
      setErrorAccion('El monto a liberar supera el saldo disponible de este depósito.');
      return;
    }
    setEnviando(true);
    setErrorAccion('');
    try {
      await pagosApi.crearLiberacion({
        id_pago: modalLiberar.id,
        monto_liberado: Number(formLiberar.monto),
        id_entregable: formLiberar.id_entregable ? Number(formLiberar.id_entregable) : undefined,
        motivo: formLiberar.motivo || undefined,
      });
      setMensaje('Liberación registrada correctamente.');
      setModalLiberar(null);
      setFormLiberar({ monto: '', id_entregable: '', motivo: '' });
      await cargar(true);
    } catch (err) {
      setErrorAccion(mensajeError(err));
    } finally {
      setEnviando(false);
    }
  }

  function nombreProyecto() {
    return contrato?.proyecto?.nombre || contrato?.proyecto?.titulo || contrato?.objeto || 'Proyecto del contrato';
  }

  if (loading) return <Cargando />;
  if (error) return <ErrorCard error={{ message: mensajeError(error) }} volverA="/contratos" volverTexto="Volver a contratos" />;

  const moneda = resumen?.moneda || 'MXN';
  const estadoContrato = contrato?.estado;

  return (
    <div className="contratos-page">
      <nav aria-label="Migas de pan" className="proyecto-breadcrumbs">
        <Link to="/contratos">Contratos</Link>
        <span aria-hidden="true">/</span>
        <Link to={`/contratos/${id}`}>Contrato</Link>
        <span aria-hidden="true">/</span>
        <span className="current" aria-current="page">Pagos y garantía</span>
      </nav>

      <header className="contratos-header">
        <div>
          <h1 className="catalogo-page-title">Pagos y garantía</h1>
          <p className="catalogo-page-subtitle">
            {nombreProyecto()} · {contrato?.cliente?.nombre_completo} y {contrato?.desarrollador?.nombre_completo}
          </p>
        </div>
      </header>

      {mensaje && <div className="alert alert-success" role="status">{mensaje}</div>}
      {errorAccion && <div className="alert alert-danger" role="alert">{errorAccion}</div>}

      <div className="alert alert-warning" role="status">
        <strong>Modo demostración:</strong> no se realizan cargos reales.
        <details style={{ marginTop: '0.5rem' }}>
          <summary>Tarjetas de prueba admitidas</summary>
          <ul style={{ margin: '0.5rem 0 0 1.25rem' }}>
            <li><code>4242 4242 4242 4242</code> — Aprobada (simulación de depósito en garantía).</li>
            <li><code>4000 0000 0000 0002</code> — Rechazada (simulación de pago no completado).</li>
            <li><code>4000 0000 0000 3220</code> — Requiere verificación (código de prueba: <code>123456</code>).</li>
          </ul>
        </details>
      </div>

      {resumen && (
        <section className="card contrato-section" aria-label="Resumen de fondos">
          <h2 className="contrato-section-title">Resumen de fondos</h2>
          <div className="contrato-escrow-breakdown" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))' }}>
            <div><span>Costo acordado</span><strong>{formatMonto(resumen.costo_acordado, moneda)}</strong></div>
            <div><span>Depositado</span><strong>{formatMonto(resumen.depositado, moneda)}</strong></div>
            <div><span>En custodia</span><strong>{formatMonto(resumen.en_custodia, moneda)}</strong></div>
            <div><span>Liberado</span><strong>{formatMonto(resumen.liberado, moneda)}</strong></div>
            <div><span>Por depositar</span><strong>{formatMonto(resumen.por_depositar, moneda)}</strong></div>
          </div>
          {esCliente && (
            <div style={{ marginTop: '1rem', display: 'flex', gap: '.75rem', flexWrap: 'wrap', alignItems: 'center' }}>
              {puedeDepositar ? (
                <button type="button" className="btn btn-primary" onClick={() => { setErrorAccion(''); setModalDeposito(true); }}>
                  Depositar fondos
                </button>
              ) : estadoContrato === 'pendiente' ? (
                <p className="contrato-accion-nota" style={{ margin: 0 }}>Falta la firma del desarrollador para poder depositar.</p>
              ) : parseMonto(resumen.por_depositar) <= 0 ? (
                <p className="contrato-accion-nota" style={{ margin: 0 }}>No hay monto pendiente por depositar.</p>
              ) : !['aceptado', 'en_progreso', 'entregado'].includes(estadoContrato || '') ? (
                <p className="contrato-accion-nota" style={{ margin: 0 }}>Los depósitos no están disponibles en el estado actual del contrato.</p>
              ) : null}
            </div>
          )}
          {esDev && (
            <p className="contrato-accion-nota" style={{ marginTop: '.75rem' }}>
              Solo el cliente puede depositar o liberar fondos. Aquí puedes consultar el estado de la garantía y las liberaciones.
            </p>
          )}
          {esAdmin && (
            <p className="contrato-accion-nota" style={{ marginTop: '.75rem' }}>
              Vista administrativa de solo lectura. La liberación de fondos corresponde al cliente; el administrador interviene únicamente mediante arbitraje en disputas.
            </p>
          )}
        </section>
      )}

      {pagoActual && pagoActual.estado_escrow === 'pendiente' && (
        <section className="card contrato-section" aria-label="Verificación de pago">
          <h2 className="contrato-section-title">Verificación requerida</h2>
          <p className="catalogo-muted">Ingresa el código de verificación para confirmar el depósito en garantía.</p>
          <div className="form-group" style={{ maxWidth: 320 }}>
            <label htmlFor="codigo-verificacion">Código de verificación</label>
            <input id="codigo-verificacion" type="text" value={codigo} onChange={(e) => setCodigo(e.target.value)} placeholder="Código" autoComplete="one-time-code" />
          </div>
          <button type="button" className="btn btn-primary btn-sm" disabled={enviando || !codigo.trim()} onClick={verificar}>
            {enviando ? 'Verificando...' : 'Verificar depósito'}
          </button>
        </section>
      )}

      <section aria-label="Depósitos y liberaciones" style={{ marginTop: '1rem' }}>
        <h2 className="contrato-section-title">Depósitos</h2>
        {items.length === 0 ? (
          <div className="card contrato-empty">
            <h3 className="contrato-empty-title">Sin depósitos registrados</h3>
            <p className="contrato-empty-text">
              {esCliente ? 'Aún no se han depositado fondos en garantía para este contrato.' : 'No hay depósitos registrados para este contrato.'}
            </p>
          </div>
        ) : (
          <div className="contratos-grid">
            {items.map((pago, idx) => {
              const disponible = parseMonto(pago.disponible);
              const liberadoPago = parseMonto(pago.liberado);
              const puedeLiberarPago = esCliente && pago.estado_escrow === 'retenido' && disponible > 0;
              return (
                <article key={pago.id} className="card contrato-card">
                  <div className="contrato-card-top">
                    <span className="contrato-id">Depósito {idx + 1}</span>
                    <span className="contrato-badge contrato-badge--neutral">
                      {ESTADOS_PAGO_LABEL[pago.estado_escrow] || pago.estado_escrow}
                    </span>
                  </div>
                  <h3 className="contrato-card-title">{formatMonto(pago.monto, pago.moneda || moneda)}</h3>
                  <div className="contrato-card-meta" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '.25rem' }}>
                    <span>Disponible: <strong>{formatMonto(pago.disponible, pago.moneda || moneda)}</strong></span>
                    <span>Liberado: {formatMonto(pago.liberado, pago.moneda || moneda)}</span>
                    <span>Fecha: {formatFechaHora(pago.fecha_pago)}</span>
                  </div>
                  {pago.estado_escrow === 'fallido' && pago.mensaje_fallo && (
                    <p className="contrato-card-party"><strong>Motivo:</strong> {pago.mensaje_fallo}</p>
                  )}
                  {pago.estado_escrow === 'fallido' && !pago.mensaje_fallo && pago.codigo_fallo && (
                    <p className="contrato-card-party"><strong>Motivo:</strong> No se pudo completar el depósito.</p>
                  )}

                  {(pago.liberaciones || []).length > 0 && (
                    <div style={{ marginTop: '.5rem' }}>
                      <strong style={{ fontSize: '.9rem' }}>Liberaciones</strong>
                      <ul style={{ margin: '.25rem 0 0 1rem', padding: 0 }}>
                        {pago.liberaciones.map((l, i) => (
                          <li key={l.id || i} style={{ fontSize: '.9rem' }}>
                            {formatMonto(l.monto_liberado, pago.moneda || moneda)}{l.motivo ? ` — ${l.motivo}` : ''} · {formatFechaHora(l.fecha_hora)}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="catalogo-actions-group" style={{ marginTop: '.75rem', flexWrap: 'wrap' }}>
                    {pago.recibo && (
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setModalRecibo({ pago, recibo: pago.recibo })}>
                        Ver recibo
                      </button>
                    )}
                    {puedeLiberarPago && (
                      <button type="button" className="btn btn-primary btn-sm" onClick={() => abrirModalLiberar(pago)}>
                        Liberar fondos
                      </button>
                    )}
                    {esCliente && pago.estado_escrow === 'retenido' && disponible <= 0 && (
                      <span className="catalogo-muted" style={{ fontSize: '.85rem' }}>Sin saldo disponible para liberar.</span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <Modal titulo="Depositar fondos en garantía" abierto={modalDeposito} onCerrar={() => !enviando && setModalDeposito(false)}>
        <p className="catalogo-muted" style={{ marginTop: 0 }}>
          Ingresa el monto y los datos de la tarjeta de prueba. No se realiza ningún cargo real y no se almacenan datos sensibles del medio de pago.
        </p>
        <form onSubmit={registrarDeposito}>
          <CampoMonto id="dep-monto" label="Monto a depositar" value={formDeposito.monto} onChange={(v) => setFormDeposito({ ...formDeposito, monto: v })} />
          {resumen && <p className="form-hint">Monto pendiente por depositar: {formatMonto(resumen.por_depositar, moneda)}</p>}
          <div className="form-group">
            <label htmlFor="dep-numero">Número de tarjeta</label>
            <input id="dep-numero" type="text" inputMode="numeric" autoComplete="off" value={formDeposito.numero} onChange={(e) => setFormDeposito({ ...formDeposito, numero: e.target.value })} placeholder="Número de tarjeta" />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '.75rem' }}>
            <div className="form-group">
              <label htmlFor="dep-venc">Vencimiento (MM/AA)</label>
              <input id="dep-venc" type="text" autoComplete="off" value={formDeposito.vencimiento} onChange={(e) => setFormDeposito({ ...formDeposito, vencimiento: e.target.value })} placeholder="MM/AA" />
            </div>
            <div className="form-group">
              <label htmlFor="dep-cvc">Código de seguridad</label>
              <input id="dep-cvc" type="text" inputMode="numeric" autoComplete="off" value={formDeposito.cvc} onChange={(e) => setFormDeposito({ ...formDeposito, cvc: e.target.value })} placeholder="CVC" />
            </div>
          </div>
          <div className="catalogo-actions-group" style={{ marginTop: '.5rem' }}>
            <button type="submit" className="btn btn-primary" disabled={enviando}>{enviando ? 'Procesando...' : 'Depositar en garantía'}</button>
            <button type="button" className="btn btn-secondary" disabled={enviando} onClick={() => setModalDeposito(false)}>Cancelar</button>
          </div>
        </form>
      </Modal>

      <Modal titulo="Liberar fondos" abierto={Boolean(modalLiberar)} onCerrar={() => !enviando && setModalLiberar(null)}>
        {modalLiberar && (
          <form onSubmit={confirmarLiberacion}>
            <p className="catalogo-muted" style={{ marginTop: 0 }}>
              Saldo disponible de este depósito: <strong>{formatMonto(modalLiberar.disponible, modalLiberar.moneda || moneda)}</strong>
            </p>
            <CampoMonto id="lib-monto" label="Monto a liberar" value={formLiberar.monto} onChange={(v) => setFormLiberar({ ...formLiberar, monto: v })} />
            <div className="form-group">
              <label htmlFor="lib-entregable">Entregable asociado (opcional)</label>
              <select id="lib-entregable" value={formLiberar.id_entregable} onChange={(e) => setFormLiberar({ ...formLiberar, id_entregable: e.target.value })}>
                <option value="">Sin entregable específico</option>
                {entregablesAprobados.map((e) => (
                  <option key={e.id} value={e.id}>{e.titulo || 'Entregable aprobado'}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="lib-motivo">Motivo (opcional)</label>
              <input id="lib-motivo" type="text" value={formLiberar.motivo} onChange={(e) => setFormLiberar({ ...formLiberar, motivo: e.target.value })} placeholder="Ej. Entregable aprobado" />
            </div>
            <div className="catalogo-actions-group" style={{ marginTop: '.5rem' }}>
              <button type="submit" className="btn btn-primary" disabled={enviando}>{enviando ? 'Liberando...' : 'Confirmar liberación'}</button>
              <button type="button" className="btn btn-secondary" disabled={enviando} onClick={() => setModalLiberar(null)}>Cancelar</button>
            </div>
          </form>
        )}
      </Modal>

      <Modal titulo="Recibo de depósito" abierto={Boolean(modalRecibo)} onCerrar={() => setModalRecibo(null)} ancho={640}>
        {modalRecibo && (
          <div>
            <dl style={{ display: 'grid', gridTemplateColumns: '160px 1fr', gap: '.4rem .75rem', margin: 0 }}>
              <dt><strong>Folio</strong></dt><dd>{modalRecibo.recibo?.folio || '—'}</dd>
              <dt><strong>Fecha</strong></dt><dd>{formatFechaHora(modalRecibo.recibo?.fecha_emision || modalRecibo.pago?.fecha_pago)}</dd>
              <dt><strong>Monto</strong></dt><dd>{formatMonto(modalRecibo.recibo?.total ?? modalRecibo.pago?.monto, modalRecibo.recibo?.moneda || modalRecibo.pago?.moneda || moneda)}</dd>
              <dt><strong>Proyecto</strong></dt><dd>{nombreProyecto()}</dd>
              <dt><strong>Cliente</strong></dt><dd>{contrato?.cliente?.nombre_completo || '—'}</dd>
              <dt><strong>Desarrollador</strong></dt><dd>{contrato?.desarrollador?.nombre_completo || '—'}</dd>
              <dt><strong>Concepto</strong></dt><dd>{modalRecibo.recibo?.concepto || 'Depósito en garantía'}</dd>
            </dl>
            {modalRecibo.recibo?.contenido_html && (
              <details style={{ marginTop: '1rem' }}>
                <summary>Ver comprobante detallado</summary>
                <iframe
                  title="Comprobante"
                  sandbox=""
                  style={{ width: '100%', height: 260, border: '1px solid #e2e8f0', marginTop: '.5rem', borderRadius: 8 }}
                  srcDoc={String(modalRecibo.recibo.contenido_html)}
                />
              </details>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
