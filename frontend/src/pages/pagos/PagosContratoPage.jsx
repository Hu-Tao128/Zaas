import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { pagosApi } from '../../services/pagosApi';
import { contratosApi } from '../../services/contratosApi';
import { formatFechaHora } from '../catalogo/catalogoUtils';
import { Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { ESTADOS_PAGO_LABEL, centavosAMonto, formatMonto, mensajeError, montoACentavos, parseMonto } from './pagosUtils';
import ModalPagos from './ModalPagos';
import './pagos.css';

const OPCION_SELECCIONA = '__selecciona__';

function motivoFallo(pago) {
  if (pago?.mensaje_fallo) return pago.mensaje_fallo;
  if (pago?.codigo_fallo === 'tarjeta_rechazada') return 'El medio de pago fue rechazado.';
  if (pago?.codigo_fallo === 'fondos_insuficientes') return 'El medio de pago no tiene fondos suficientes.';
  if (pago?.codigo_fallo === 'verificacion_expirada') return 'El tiempo límite para verificar el pago expiró.';
  if (pago?.codigo_fallo === 'intentos_agotados') return 'Se agotaron los intentos de verificación permitidos.';
  return 'No se pudo completar el depósito.';
}

function CampoMonto({ id, label, value, onChange, onBlur, error = '', ayuda = null }) {
  return (
    <div className="form-group">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="text"
        inputMode="decimal"
        autoComplete="off"
        value={value}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
        onChange={(e) => {
          const v = e.target.value;
          if (/^\d*\.?\d{0,2}$/.test(v)) onChange(v);
        }}
        onBlur={onBlur}
      />
      {ayuda}
      {error && <p id={`${id}-error`} className="pagos-error-campo" role="alert">{error}</p>}
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
  const [pasoDeposito, setPasoDeposito] = useState('formulario'); // 'formulario' | 'procesando' | 'verificacion' | 'resultado'
  const [formDeposito, setFormDeposito] = useState({ monto: '', numero: '', vencimiento: '', cvc: '' });
  const [errorCampoDeposito, setErrorCampoDeposito] = useState('');
  const [pagoActual, setPagoActual] = useState(null);
  const [codigo, setCodigo] = useState('');
  const [errorModal, setErrorModal] = useState('');
  const intervaloRef = useRef(null);

  const [modalLiberar, setModalLiberar] = useState(null); // pago
  const [pasoLiberar, setPasoLiberar] = useState('formulario'); // 'formulario' | 'revision'
  const [confirmadoTodo, setConfirmadoTodo] = useState(false);
  const [formLiberar, setFormLiberar] = useState({ monto: '', id_entregable: OPCION_SELECCIONA, motivo: '' });
  const [errorCampoLiberar, setErrorCampoLiberar] = useState('');
  const ejecutandoLiberacionRef = useRef(false);
  const botonVolverRef = useRef(null);

  const [modalRecibo, setModalRecibo] = useState(null); // {pago, recibo}

  useEffect(() => {
    return () => {
      if (intervaloRef.current) {
        clearInterval(intervaloRef.current);
        intervaloRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (pasoLiberar === 'revision' && botonVolverRef.current) {
      botonVolverRef.current.focus();
    }
  }, [pasoLiberar]);

  function abrirModalDeposito() {
    if (intervaloRef.current) {
      clearInterval(intervaloRef.current);
      intervaloRef.current = null;
    }
    setErrorAccion('');
    setErrorModal('');
    setErrorCampoDeposito('');
    setCodigo('');
    setPagoActual(null);
    setFormDeposito({ monto: '', numero: '', vencimiento: '', cvc: '' });
    setPasoDeposito('formulario');
    setModalDeposito(true);
  }

  function cerrarModalDeposito() {
    if (intervaloRef.current) {
      clearInterval(intervaloRef.current);
      intervaloRef.current = null;
    }
    setModalDeposito(false);
    setPasoDeposito('formulario');
    setErrorModal('');
    setErrorCampoDeposito('');
    setCodigo('');
    setFormDeposito({ monto: '', numero: '', vencimiento: '', cvc: '' });
  }

  function validarMontoDeposito(valor) {
    const v = String(valor || '').trim();
    if (!v) return 'El monto a depositar es obligatorio.';
    if (!/^\d+(\.\d{1,2})?$/.test(v)) return 'El monto debe ser un número válido (hasta 2 decimales).';
    const centavos = montoACentavos(v);
    if (centavos <= 0) return 'El monto debe ser mayor a 0.';
    const pendienteCentavos = montoACentavos(resumen?.por_depositar);
    if (pendienteCentavos > 0 && centavos > pendienteCentavos) {
      return `El monto supera lo que falta por depositar: ${formatMonto(resumen?.por_depositar, moneda)}.`;
    }
    return null;
  }

  function validarCampoDeposito(valor) {
    setErrorCampoDeposito(validarMontoDeposito(valor) || '');
  }

  function abrirModalLiberar(pago) {
    setErrorAccion('');
    setErrorModal('');
    setPasoLiberar('formulario');
    setConfirmadoTodo(false);
    setErrorCampoLiberar('');
    setFormLiberar({ monto: '', id_entregable: OPCION_SELECCIONA, motivo: '' });
    setModalLiberar(pago);
  }

  function cerrarModalLiberar() {
    if (enviando) return;
    setModalLiberar(null);
    setPasoLiberar('formulario');
    setConfirmadoTodo(false);
    setErrorCampoLiberar('');
    setFormLiberar({ monto: '', id_entregable: OPCION_SELECCIONA, motivo: '' });
  }

  function validarMontoLiberacion(valor, disponible) {
    const v = String(valor || '').trim();
    if (!v) return 'El monto a liberar es obligatorio.';
    if (!/^\d+(\.\d{1,2})?$/.test(v)) return 'El monto debe ser un número válido (hasta 2 decimales).';
    const centavos = montoACentavos(v);
    if (centavos <= 0) return 'El monto debe ser mayor a 0.';
    const dispCentavos = montoACentavos(disponible);
    if (centavos > dispCentavos) {
      return `El monto supera el disponible para liberar: ${formatMonto(disponible, modalLiberar?.moneda || moneda)}.`;
    }
    return null;
  }

  function validarCampoLiberar(valor) {
    setErrorCampoLiberar(validarMontoLiberacion(valor, modalLiberar?.disponible) || '');
  }

  function abrirModalVerificacion(pago) {
    if (intervaloRef.current) {
      clearInterval(intervaloRef.current);
      intervaloRef.current = null;
    }
    setErrorAccion('');
    setErrorModal('');
    setCodigo('');
    setPagoActual(pago);
    setPasoDeposito('verificacion');
    setModalDeposito(true);
  }

  const tituloModalDeposito = useMemo(() => {
    if (pasoDeposito === 'verificacion') return 'Verificación requerida';
    if (pasoDeposito === 'procesando') return 'Procesando depósito';
    if (pasoDeposito === 'resultado') return 'Resultado del depósito';
    return 'Depositar fondos en garantía';
  }, [pasoDeposito]);

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

  // Refresca la lista cada 5 s mientras exista algún depósito pendiente (hasta 2 minutos)
  useEffect(() => {
    const tienePendientes = items.some((p) => p.estado_escrow === 'pendiente');
    if (!tienePendientes) return undefined;

    let transcurrido = 0;
    const intervalId = setInterval(() => {
      transcurrido += 5000;
      cargar(true);
      if (transcurrido >= 120000) {
        clearInterval(intervalId);
      }
    }, 5000);

    return () => clearInterval(intervalId);
  }, [items, id]);

  const depositosValidos = useMemo(
    () => items.filter((p) => p.estado_escrow !== 'fallido'),
    [items],
  );
  const intentosNoCompletados = useMemo(
    () => items.filter((p) => p.estado_escrow === 'fallido'),
    [items],
  );

  const entregablesAprobados = useMemo(
    () => (contrato?.entregables || []).filter((e) => e.estado === 'aprobado'),
    [contrato],
  );

  const puedeDepositar = useMemo(() => {
    if (!esCliente || !contrato || !resumen) return false;
    if (!['aceptado', 'en_progreso', 'entregado'].includes(contrato.estado)) return false;
    return parseMonto(resumen.por_depositar) > 0;
  }, [esCliente, contrato, resumen]);

  function validarDatosPago() {
    const numero = formDeposito.numero.replace(/\s/g, '');
    if (!/^\d{13,19}$/.test(numero)) return 'Los datos del medio de pago no son válidos.';
    if (!/^\d{2}\/\d{2}$/.test(formDeposito.vencimiento)) return 'El vencimiento debe tener formato MM/AA.';
    if (!/^\d{3,4}$/.test(formDeposito.cvc)) return 'El código de seguridad no es válido.';
    return null;
  }

  async function registrarDeposito(e) {
    e.preventDefault();
    const errMonto = validarMontoDeposito(formDeposito.monto);
    setErrorCampoDeposito(errMonto || '');
    if (errMonto) return;
    const err = validarDatosPago();
    if (err) { setErrorModal(err); return; }
    setEnviando(true);
    setMensaje('');
    setErrorAccion('');
    setErrorModal('');
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

      const pagoCreado = datos.pago;
      setPagoActual(pagoCreado);
      setFormDeposito({ monto: '', numero: '', vencimiento: '', cvc: '' });
      await cargar(true);

      if (pagoCreado?.requiere_verificacion) {
        setPasoDeposito('verificacion');
        setEnviando(false);
      } else if (pagoCreado?.estado_escrow === 'pendiente') {
        setPasoDeposito('procesando');
        setEnviando(false);
        let intentos = 0;
        if (intervaloRef.current) clearInterval(intervaloRef.current);
        intervaloRef.current = setInterval(async () => {
          intentos += 1;
          try {
            const actualizado = await pagosApi.obtener(pagoCreado.id);
            setPagoActual(actualizado.pago);
            if (actualizado.pago.estado_escrow !== 'pendiente' || intentos >= 15) {
              if (intervaloRef.current) {
                clearInterval(intervaloRef.current);
                intervaloRef.current = null;
              }
              setPasoDeposito('resultado');
              await cargar(true);
            }
          } catch {
            if (intervaloRef.current) {
              clearInterval(intervaloRef.current);
              intervaloRef.current = null;
            }
            setPasoDeposito('resultado');
          }
        }, 1500);
      } else {
        setPasoDeposito('resultado');
        setEnviando(false);
      }
    } catch (err2) {
      setErrorModal(mensajeError(err2));
      setEnviando(false);
    }
  }

  async function verificar() {
    if (!pagoActual) return;
    setEnviando(true);
    setErrorModal('');
    try {
      const datos = await pagosApi.verificar(pagoActual.id, codigo);
      setPagoActual(datos.pago);
      setMensaje('Pago verificado correctamente.');
      setCodigo('');
      setPasoDeposito('resultado');
      await cargar(true);
    } catch (err) {
      setErrorModal(mensajeError(err));
      try {
        const actualizado = await pagosApi.obtener(pagoActual.id);
        setPagoActual(actualizado.pago);
        if (actualizado.pago.estado_escrow === 'fallido') {
          setPasoDeposito('resultado');
        }
      } catch {
        // noop
      }
      await cargar(true);
    } finally {
      setEnviando(false);
    }
  }

  function prepararRevisionLiberacion(e) {
    e.preventDefault();
    const err = validarMontoLiberacion(formLiberar.monto, modalLiberar?.disponible);
    setErrorCampoLiberar(err || '');
    if (err) return;
    setConfirmadoTodo(false);
    setPasoLiberar('revision');
  }

  async function confirmarLiberacion() {
    if (!modalLiberar || ejecutandoLiberacionRef.current || enviando) return;
    const err = validarMontoLiberacion(formLiberar.monto, modalLiberar.disponible);
    if (err) {
      setErrorCampoLiberar(err);
      setPasoLiberar('formulario');
      return;
    }
    const centavos = montoACentavos(formLiberar.monto);
    const disponibleCentavos = montoACentavos(modalLiberar.disponible);
    if (centavos === disponibleCentavos && !confirmadoTodo) return;

    ejecutandoLiberacionRef.current = true;
    setEnviando(true);
    setErrorAccion('');
    try {
      await pagosApi.crearLiberacion({
        id_pago: modalLiberar.id,
        monto_liberado: centavosAMonto(centavos),
        id_entregable: formLiberar.id_entregable && formLiberar.id_entregable !== OPCION_SELECCIONA
          ? Number(formLiberar.id_entregable)
          : undefined,
        motivo: formLiberar.motivo || undefined,
      });
      setMensaje('Liberación registrada correctamente.');
      setModalLiberar(null);
      setPasoLiberar('formulario');
      setConfirmadoTodo(false);
      setErrorCampoLiberar('');
      setFormLiberar({ monto: '', id_entregable: OPCION_SELECCIONA, motivo: '' });
      await cargar(true);
    } catch (err) {
      setErrorCampoLiberar(mensajeError(err));
      setPasoLiberar('formulario');
    } finally {
      ejecutandoLiberacionRef.current = false;
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

  const disponibleLiberarCentavos = montoACentavos(modalLiberar?.disponible);
  const montoLiberarCentavos = montoACentavos(formLiberar.monto);
  const restanteLiberarCentavos = Math.max(0, disponibleLiberarCentavos - montoLiberarCentavos);
  const esLiberacionTotal = disponibleLiberarCentavos > 0 && montoLiberarCentavos === disponibleLiberarCentavos;
  const montoLiberarValido = Boolean(modalLiberar) && !validarMontoLiberacion(formLiberar.monto, modalLiberar.disponible);

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
      </div>

      {resumen && (
        <section className="card contrato-section" aria-label="Resumen de fondos">
          <h2 className="contrato-section-title">Resumen de fondos</h2>
          <div className="contrato-escrow-breakdown" style={{ gridTemplateColumns: 'repeat(auto-fit,minmax(160px,1fr))' }}>
            <div><span>Costo acordado</span><strong>{formatMonto(resumen.costo_acordado, moneda)}</strong></div>
            <div><span>Depositado</span><strong className={parseMonto(resumen.depositado) <= 0 ? 'pagos-cifra-sin-fondos' : ''}>{formatMonto(resumen.depositado, moneda)}</strong></div>
            <div><span>En custodia</span><strong className={parseMonto(resumen.en_custodia) <= 0 ? 'pagos-cifra-sin-fondos' : ''}>{formatMonto(resumen.en_custodia, moneda)}</strong></div>
            <div><span>Liberado</span><strong className={parseMonto(resumen.liberado) <= 0 ? 'pagos-cifra-sin-fondos' : ''}>{formatMonto(resumen.liberado, moneda)}</strong></div>
            <div><span>Por depositar</span><strong className={parseMonto(resumen.por_depositar) <= 0 ? 'pagos-cifra-sin-fondos' : ''}>{formatMonto(resumen.por_depositar, moneda)}</strong></div>
          </div>
          {esCliente && (
            <div className="pagos-actions-group" style={{ marginTop: '1rem' }}>
              {puedeDepositar ? (
                <button type="button" className="btn btn-primary" onClick={abrirModalDeposito}>
                  Depositar fondos
                </button>
              ) : estadoContrato === 'borrador' ? (
                <p className="contrato-accion-nota" style={{ margin: 0 }}>
                  El contrato está en borrador; debe formalizarse y ser aceptado antes de poder realizar depósitos en garantía.
                </p>
              ) : estadoContrato === 'pendiente' ? (
                <p className="contrato-accion-nota" style={{ margin: 0 }}>
                  Falta la firma del desarrollador para poder depositar.
                </p>
              ) : parseMonto(resumen.por_depositar) <= 0 ? (
                <p className="contrato-accion-nota" style={{ margin: 0 }}>
                  No hay monto pendiente por depositar.
                </p>
              ) : !['aceptado', 'en_progreso', 'entregado'].includes(estadoContrato || '') ? (
                <p className="contrato-accion-nota" style={{ margin: 0 }}>
                  Los depósitos no están disponibles en el estado actual del contrato.
                </p>
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

      <section aria-label="Depósitos y liberaciones" style={{ marginTop: '1rem' }}>
        <h2 className="contrato-section-title">Depósitos</h2>
        {depositosValidos.length === 0 ? (
          <div className="card contrato-empty">
            <h3 className="contrato-empty-title">Sin depósitos registrados</h3>
            <p className="contrato-empty-text">
              {esCliente ? 'Aún no se han depositado fondos en garantía para este contrato.' : 'No hay depósitos registrados para este contrato.'}
            </p>
          </div>
        ) : (
          <div className="contratos-grid">
            {depositosValidos.map((pago, idx) => {
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
                    <span className={disponible <= 0 ? 'pagos-cifra-sin-fondos' : ''}>
                      Disponible: <strong>{formatMonto(pago.disponible, pago.moneda || moneda)}</strong>
                    </span>
                    <span className={liberadoPago <= 0 ? 'pagos-cifra-sin-fondos' : ''}>
                      Liberado: {formatMonto(pago.liberado, pago.moneda || moneda)}
                    </span>
                    <span>Fecha: {formatFechaHora(pago.fecha_pago)}</span>
                  </div>

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

                  <div className="pagos-actions-group" style={{ marginTop: '.75rem' }}>
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
                    {esCliente && pago.requiere_verificacion && (
                      <button type="button" className="btn btn-warning btn-sm" onClick={() => abrirModalVerificacion(pago)}>
                        Completar verificación
                      </button>
                    )}
                    {esCliente && pago.estado_escrow === 'retenido' && disponible <= 0 && (
                      <span className="pagos-cifra-sin-fondos" style={{ fontSize: '.85rem' }}>Sin saldo disponible para liberar.</span>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}

        {intentosNoCompletados.length > 0 && (
          <details className="card" style={{ marginTop: '1.25rem', padding: '1rem' }}>
            <summary style={{ cursor: 'pointer', fontWeight: 600 }}>
              Intentos no completados ({intentosNoCompletados.length})
            </summary>
            <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              {intentosNoCompletados.map((intento, idx) => (
                <div
                  key={intento.id || idx}
                  style={{
                    padding: '0.75rem',
                    border: '1px solid var(--zaas-border, #e2e8f0)',
                    borderRadius: '6px',
                    backgroundColor: '#f8fafc',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <strong>{formatMonto(intento.monto, intento.moneda || moneda)}</strong>
                    <span className="contrato-badge contrato-badge--neutral">No completado</span>
                  </div>
                  <p style={{ margin: '0.35rem 0 0', fontSize: '0.9rem', color: 'var(--zaas-text-muted, #64748b)' }}>
                    Fecha: {formatFechaHora(intento.fecha_pago || intento.created_at)}
                  </p>
                  <p style={{ margin: '0.35rem 0 0', fontSize: '0.9rem' }}>
                    <strong>Motivo:</strong> {motivoFallo(intento)}
                  </p>
                </div>
              ))}
            </div>
          </details>
        )}
      </section>

      <ModalPagos
        titulo={tituloModalDeposito}
        abierto={modalDeposito}
        onCerrar={cerrarModalDeposito}
        procesando={enviando || pasoDeposito === 'procesando'}
        cerrarEnFondo={false}
      >
        {pasoDeposito === 'formulario' && (
          <>
            <p className="catalogo-muted" style={{ marginTop: 0 }}>
              Ingresa el monto y los datos del medio de pago. No se almacenan datos sensibles.
            </p>
            {errorModal && <div className="alert alert-danger" role="alert" style={{ marginBottom: '1rem' }}>{errorModal}</div>}
            <form onSubmit={registrarDeposito}>
              <CampoMonto
                id="dep-monto"
                label="Monto a depositar"
                value={formDeposito.monto}
                error={errorCampoDeposito}
                ayuda={resumen && <p className="form-hint">Por depositar: {formatMonto(resumen.por_depositar, moneda)}</p>}
                onChange={(v) => {
                  setFormDeposito({ ...formDeposito, monto: v });
                  setErrorCampoDeposito(validarMontoDeposito(v) || '');
                }}
                onBlur={() => validarCampoDeposito(formDeposito.monto)}
              />
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
              <div className="pagos-modal-footer">
                <button type="button" className="btn btn-secondary" disabled={enviando} onClick={cerrarModalDeposito}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary" disabled={enviando}>
                  {enviando ? 'Procesando...' : 'Depositar en garantía'}
                </button>
              </div>
            </form>
          </>
        )}

        {pasoDeposito === 'procesando' && (
          <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
            <h3 style={{ marginTop: 0 }}>Procesando…</h3>
            <p className="catalogo-muted">
              Estamos procesando tu depósito en garantía. Por favor, espera un momento.
            </p>
            <div className="zaas-spinner" style={{ margin: '1.5rem auto' }} aria-hidden="true" />
          </div>
        )}

        {pasoDeposito === 'verificacion' && (
          <div>
            <p className="catalogo-muted" style={{ marginTop: 0 }}>
              Esta verificación es requerida por el emisor de tu tarjeta para validar la autenticidad de la transacción antes de retener los fondos en garantía.
            </p>
            <div className="alert alert-info" style={{ marginBottom: '1rem' }}>
              <div>Código de prueba: <strong>123456</strong></div>
              <div style={{ marginTop: '.25rem' }}>
                Intentos restantes: <strong>{pagoActual?.intentos_restantes ?? 3}</strong>
              </div>
            </div>
            {errorModal && <div className="alert alert-danger" role="alert" style={{ marginBottom: '1rem' }}>{errorModal}</div>}
            <form onSubmit={(e) => { e.preventDefault(); verificar(); }}>
              <div className="form-group" style={{ maxWidth: 320 }}>
                <label htmlFor="codigo-verificacion">Código de verificación</label>
                <input
                  id="codigo-verificacion"
                  type="text"
                  value={codigo}
                  onChange={(e) => setCodigo(e.target.value)}
                  placeholder="123456"
                  autoComplete="one-time-code"
                  disabled={enviando}
                />
              </div>
              <div className="pagos-modal-footer">
                <button type="button" className="btn btn-secondary" disabled={enviando} onClick={cerrarModalDeposito}>
                  Cancelar
                </button>
                <button type="submit" className="btn btn-primary" disabled={enviando || !codigo.trim()}>
                  {enviando ? 'Verificando...' : 'Verificar depósito'}
                </button>
              </div>
            </form>
          </div>
        )}

        {pasoDeposito === 'resultado' && (
          <div>
            {pagoActual?.estado_escrow === 'retenido' ? (
              <>
                <div className="alert alert-success" style={{ marginBottom: '1rem' }}>
                  <strong>¡Depósito exitoso!</strong> Los fondos por {formatMonto(pagoActual?.monto, pagoActual?.moneda || moneda)} han sido retenidos en garantía de forma segura.
                </div>
                <p className="catalogo-muted">
                  Los fondos permanecerán en custodia hasta que autorices su liberación tras recibir los entregables pactados.
                </p>
                <div className="pagos-modal-footer">
                  {pagoActual?.recibo && (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => {
                        const r = pagoActual.recibo;
                        const p = pagoActual;
                        cerrarModalDeposito();
                        setModalRecibo({ pago: p, recibo: r });
                      }}
                    >
                      Ver recibo
                    </button>
                  )}
                  <button type="button" className="btn btn-primary" onClick={cerrarModalDeposito}>
                    Aceptar
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className="alert alert-danger" style={{ marginBottom: '1rem' }}>
                  <strong>No se pudo completar el depósito.</strong>
                  <div style={{ marginTop: '.25rem' }}>
                    {pagoActual?.mensaje_fallo || 'La transacción no pudo ser autorizada.'}
                  </div>
                </div>
                <div className="pagos-modal-footer">
                  <button type="button" className="btn btn-primary" onClick={cerrarModalDeposito}>
                    Entendido
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </ModalPagos>

      <ModalPagos
        titulo="Liberar fondos"
        abierto={Boolean(modalLiberar)}
        onCerrar={cerrarModalLiberar}
        procesando={enviando}
        cerrarEnFondo={false}
      >
        {modalLiberar && pasoLiberar === 'formulario' && (
          <form onSubmit={prepararRevisionLiberacion}>
            <CampoMonto
              id="lib-monto"
              label="Monto a liberar"
              value={formLiberar.monto}
              error={errorCampoLiberar}
              ayuda={<p className="form-hint">Disponible para liberar: {formatMonto(modalLiberar.disponible, modalLiberar.moneda || moneda)}</p>}
              onChange={(v) => {
                setFormLiberar({ ...formLiberar, monto: v });
                setErrorCampoLiberar(validarMontoLiberacion(v, modalLiberar.disponible) || '');
              }}
              onBlur={() => validarCampoLiberar(formLiberar.monto)}
            />
            <div className="form-group">
              <label htmlFor="lib-entregable">Entregable asociado (opcional)</label>
              <select
                id="lib-entregable"
                value={entregablesAprobados.length ? formLiberar.id_entregable : ''}
                onChange={(e) => setFormLiberar({ ...formLiberar, id_entregable: e.target.value })}
              >
                {entregablesAprobados.length > 0 && (
                  <option value={OPCION_SELECCIONA} disabled>Selecciona un entregable</option>
                )}
                <option value="">Sin entregable asociado</option>
                {entregablesAprobados.map((e) => (
                  <option key={e.id} value={e.id}>{e.titulo || 'Entregable aprobado'}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="lib-motivo">Motivo (opcional)</label>
              <input id="lib-motivo" type="text" value={formLiberar.motivo} onChange={(e) => setFormLiberar({ ...formLiberar, motivo: e.target.value })} placeholder="Ej. Entregable aprobado" />
            </div>
            <div className="pagos-modal-footer">
              <button type="button" className="btn btn-secondary" disabled={enviando} onClick={cerrarModalLiberar}>Cancelar</button>
              <button type="submit" className="btn btn-primary" disabled={enviando || !montoLiberarValido}>Revisar liberación</button>
            </div>
          </form>
        )}

        {modalLiberar && pasoLiberar === 'revision' && (
          <div>
            <p style={{ marginTop: 0, fontWeight: 600 }}>
              Liberarás {formatMonto(centavosAMonto(montoLiberarCentavos), modalLiberar.moneda || moneda)} al desarrollador.{' '}
              Quedarán en custodia {formatMonto(centavosAMonto(restanteLiberarCentavos), modalLiberar.moneda || moneda)}.
            </p>
            {esLiberacionTotal && (
              <div className="alert alert-warning pagos-aviso-total" role="alert">
                <strong>Vas a liberar TODO el saldo en custodia.</strong>
              </div>
            )}
            <p className="catalogo-muted">Esta acción no se puede deshacer.</p>
            {esLiberacionTotal && (
              <label className="pagos-check-confirmar">
                <input
                  type="checkbox"
                  checked={confirmadoTodo}
                  onChange={(e) => setConfirmadoTodo(e.target.checked)}
                />
                Confirmo que quiero liberar todo el saldo
              </label>
            )}
            <div className="pagos-modal-footer">
              <button
                ref={botonVolverRef}
                type="button"
                className="btn btn-secondary"
                disabled={enviando}
                onClick={() => setPasoLiberar('formulario')}
              >
                Volver
              </button>
              <button
                type="button"
                className="btn btn-primary"
                disabled={enviando || (esLiberacionTotal && !confirmadoTodo)}
                onClick={confirmarLiberacion}
              >
                {enviando ? 'Confirmando...' : 'Confirmar liberación'}
              </button>
            </div>
          </div>
        )}
      </ModalPagos>

      <ModalPagos
        titulo="Recibo de depósito"
        abierto={Boolean(modalRecibo)}
        onCerrar={() => setModalRecibo(null)}
        cerrarEnFondo={true}
        ancho={640}
      >
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
      </ModalPagos>
    </div>
  );
}
