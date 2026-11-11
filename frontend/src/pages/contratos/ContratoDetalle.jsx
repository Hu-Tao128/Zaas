import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { contratosApi } from '../../services/contratosApi';
import { comunicacionApi } from '../../services/comunicacionApi';
import { CalendarIcon, ShieldCheckIcon } from '../../components/icons';
import { formatDinero, formatFecha, formatFechaHora } from '../catalogo/catalogoUtils';
import {
  CargandoContratos,
  ErrorContratos,
  EscrowBadge,
  EstadoContratoBadge,
  EstadoEntregableBadge,
  RolBadge,
} from './ContratoUI';

export default function ContratoDetalle() {
  const { id } = useParams();
  const { data, loading, error, recargar } = useApi(() => contratosApi.detalle(id), [id]);
  const contrato = data?.contrato;

  const [mostrandoConfirmacion, setMostrandoConfirmacion] = useState(false);
  const [acepto, setAcepto] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [mensajeAccion, setMensajeAccion] = useState('');
  const [errorAccion, setErrorAccion] = useState('');

  const [mostrarEntregable, setMostrarEntregable] = useState(false);
  const [entregableForm, setEntregableForm] = useState({ titulo: '', descripcion: '', url_archivo: '' });
  const [comentariosRevision, setComentariosRevision] = useState({});

  const [mostrarDisputa, setMostrarDisputa] = useState(false);
  const [disputaForm, setDisputaForm] = useState({ tipo: 'pago', descripcion: '' });
  const [resolucionForm, setResolucionForm] = useState({ decision: 'liberar', porcentaje_desarrollador: 50, notas: '' });
  const [disputaAResolver, setDisputaAResolver] = useState(null);

  const [mostrarCalificar, setMostrarCalificar] = useState(false);
  const [calificacionForm, setCalificacionForm] = useState({ puntaje: 5, comentarios: '' });

  const [chat, setChat] = useState({ mensajes: [], cargando: true, error: null });
  const [nuevoMensaje, setNuevoMensaje] = useState('');

  const esParte = Boolean(contrato?.acciones?.es_parte);
  const esAdmin = Boolean(contrato?.acciones?.es_admin);

  useEffect(() => {
    if (!contrato || !esParte) {
      setChat({ mensajes: [], cargando: false, error: null });
      return undefined;
    }
    let vigente = true;
    setChat((actual) => ({ ...actual, cargando: true }));
    comunicacionApi.chat(id)
      .then((respuesta) => {
        if (vigente) setChat({ mensajes: respuesta.mensajes || [], cargando: false, error: null });
      })
      .catch((err) => {
        if (vigente) setChat({ mensajes: [], cargando: false, error: err });
      });
    return () => { vigente = false; };
  }, [id, contrato, esParte]);

  if (loading) return <CargandoContratos mensaje="Cargando contrato..." />;
  if (error) {
    return (
      <div className="contratos-page">
        <ErrorContratos error={error} onReintentar={recargar} />
        <Link to="/contratos" className="btn btn-secondary">Volver a contratos</Link>
      </div>
    );
  }

  const acciones = contrato.acciones;
  const etiquetaAceptar = acciones.soy_cliente && contrato.escrow.estado === 'sin_deposito'
    ? 'Aceptar y Depositar en Escrow'
    : 'Aceptar y Firmar Contrato';

  async function ejecutar(accion, mensajeExito) {
    setEnviando(true);
    setErrorAccion('');
    setMensajeAccion('');
    try {
      const respuesta = await accion();
      setMensajeAccion(respuesta.mensaje || mensajeExito);
      recargar();
      return respuesta;
    } catch (err) {
      setErrorAccion(err.message || 'No se pudo completar la acción.');
      return null;
    } finally {
      setEnviando(false);
    }
  }

  async function handleAceptar() {
    if (!acepto || enviando) return;
    const respuesta = await ejecutar(() => contratosApi.aceptar(contrato.id), 'Contrato aceptado.');
    if (respuesta) {
      setMostrandoConfirmacion(false);
      setAcepto(false);
    }
  }

  async function handleEntregable(event) {
    event.preventDefault();
    if (enviando) return;
    const respuesta = await ejecutar(
      () => contratosApi.crearEntregable(contrato.id, entregableForm),
      'Entregable subido.',
    );
    if (respuesta) {
      setEntregableForm({ titulo: '', descripcion: '', url_archivo: '' });
      setMostrarEntregable(false);
    }
  }

  async function revisarEntregable(idEntregable, aprobar) {
    if (enviando) return;
    await ejecutar(
      () => contratosApi.revisarEntregable(idEntregable, {
        aprobar,
        comentario: comentariosRevision[idEntregable] || '',
      }),
      aprobar ? 'Entregable aprobado.' : 'Entregable rechazado.',
    );
    setComentariosRevision((actual) => ({ ...actual, [idEntregable]: '' }));
  }

  async function handleLiberar() {
    if (enviando) return;
    await ejecutar(() => contratosApi.liberar(contrato.id), 'Fondos liberados.');
  }

  async function handleDisputa(event) {
    event.preventDefault();
    if (enviando) return;
    const respuesta = await ejecutar(
      () => contratosApi.abrirDisputa(contrato.id, disputaForm),
      'Disputa creada.',
    );
    if (respuesta) {
      setMostrarDisputa(false);
      setDisputaForm({ tipo: 'pago', descripcion: '' });
    }
  }

  async function handleResolverDisputa(event) {
    event.preventDefault();
    if (!disputaAResolver || enviando) return;
    const respuesta = await ejecutar(
      () => contratosApi.resolverDisputa(disputaAResolver.id, resolucionForm),
      'Disputa resuelta.',
    );
    if (respuesta) {
      setDisputaAResolver(null);
      setResolucionForm({ decision: 'liberar', porcentaje_desarrollador: 50, notas: '' });
    }
  }

  async function handleCalificar(event) {
    event.preventDefault();
    if (enviando) return;
    const respuesta = await ejecutar(
      () => comunicacionApi.calificar(contrato.id, calificacionForm),
      'Calificación enviada.',
    );
    if (respuesta) setMostrarCalificar(false);
  }

  async function handleMensaje(event) {
    event.preventDefault();
    const contenido = nuevoMensaje.trim();
    if (!contenido || enviando) return;
    setEnviando(true);
    setErrorAccion('');
    try {
      const respuesta = await comunicacionApi.enviarMensaje(contrato.id, contenido);
      setChat((actual) => ({ ...actual, mensajes: [...actual.mensajes, respuesta.mensaje_enviado] }));
      setNuevoMensaje('');
    } catch (err) {
      setErrorAccion(err.message || 'No se pudo enviar el mensaje.');
    } finally {
      setEnviando(false);
    }
  }

  const firmas = [
    {
      parte: 'Cliente',
      nombre: contrato.cliente?.nombre_completo,
      firmado: contrato.firmas.cliente,
      folio: contrato.firma_cliente,
    },
    {
      parte: 'Desarrollador',
      nombre: contrato.desarrollador?.nombre_completo,
      firmado: contrato.firmas.desarrollador,
      folio: contrato.firma_desarrollador,
    },
  ];

  return (
    <div className="contratos-page">
      <nav aria-label="Migas de pan" className="proyecto-breadcrumbs">
        <Link to="/contratos">Contratos</Link>
        <span aria-hidden="true">/</span>
        <span className="current" aria-current="page">Contrato #{contrato.id}</span>
      </nav>

      {mensajeAccion && <div className="alert alert-success" role="status">{mensajeAccion}</div>}
      {errorAccion && <div className="alert alert-danger" role="alert">{errorAccion}</div>}

      <header className="card contrato-header-card">
        <div className="contrato-header-top">
          <div className="contrato-header-tags">
            <EstadoContratoBadge estado={contrato.estado} />
            <RolBadge rol={contrato.rol} />
            <EscrowBadge estado={contrato.escrow.estado} />
          </div>
          <button type="button" className="btn btn-secondary btn-sm no-print" onClick={() => window.print()}>
            Imprimir documento
          </button>
        </div>

        <h1 className="proyecto-detalle-title">Contrato #{contrato.id}</h1>
        <p className="contrato-header-object">{contrato.objeto}</p>

        <div className="contrato-header-meta">
          <span><strong>Cliente:</strong> {contrato.cliente?.nombre_completo}</span>
          <span><strong>Desarrollador:</strong> {contrato.desarrollador?.nombre_completo}</span>
          <span><strong>Monto:</strong> {formatDinero(contrato.costo_acordado)} MXN</span>
          <span>
            <CalendarIcon size={14} />
            <strong>Creado:</strong> {formatFecha(contrato.fecha_creacion)}
          </span>
          {contrato.plantilla && (
            <span><strong>Plantilla:</strong> {contrato.plantilla.nombre}</span>
          )}
        </div>
      </header>

      <div className="contrato-detalle-layout">
        <section className="contrato-detalle-main" aria-label="Documento y firmas del contrato">
          <article className="card contrato-documento-card">
            <div className="contrato-documento-header">
              <h2 className="contrato-section-title">Documento del contrato</h2>
              <span className="contrato-documento-copy">Copia inmutable de los términos aceptados</span>
            </div>

            <div className="contrato-documento-scroll" tabIndex={0} aria-label="Documento legal del contrato">
              {contrato.documento_html ? (
                <div className="contrato-documento" dangerouslySetInnerHTML={{ __html: contrato.documento_html }} />
              ) : (
                <div className="alert alert-warning">Este contrato todavía no tiene términos generados.</div>
              )}
            </div>
          </article>

          <section className="card contrato-section" aria-label="Firmas del contrato">
            <h2 className="contrato-section-title">Firmas</h2>
            <div className="contrato-firmas-grid">
              {firmas.map((firma) => (
                <div key={firma.parte} className="contrato-firma-item">
                  <span className="contrato-firma-parte">{firma.parte}</span>
                  <strong className="contrato-firma-nombre">{firma.nombre}</strong>
                  <span className={`contrato-firma-estado ${firma.firmado ? 'is-signed' : ''}`}>
                    {firma.firmado ? 'Firmado' : 'Pendiente'}
                  </span>
                  <code className="contrato-firma-folio">{firma.folio || '—'}</code>
                </div>
              ))}
            </div>

            {contrato.aceptaciones.length > 0 && (
              <div className="contrato-aceptaciones">
                <h3 className="contrato-subsection-title">Registro de aceptaciones</h3>
                <ul className="contrato-aceptaciones-list">
                  {contrato.aceptaciones.map((aceptacion) => (
                    <li key={aceptacion.id}>
                      <strong>{aceptacion.usuario?.nombre_completo}</strong> —{' '}
                      {formatFechaHora(aceptacion.fecha_hora)} — IP: {aceptacion.ip || 'no disponible'}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </section>

          <section className="card contrato-section" aria-label="Entregables del contrato">
            <div className="contrato-documento-header">
              <h2 className="contrato-section-title">Entregables</h2>
              {acciones.puede_subir_entregable && (
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={() => setMostrarEntregable((valor) => !valor)}
                >
                  {mostrarEntregable ? 'Cancelar' : 'Subir entregable'}
                </button>
              )}
            </div>

            {mostrarEntregable && acciones.puede_subir_entregable && (
              <form className="form-group" onSubmit={handleEntregable}>
                <label htmlFor="entregable-titulo">Título *</label>
                <input
                  id="entregable-titulo"
                  value={entregableForm.titulo}
                  onChange={(e) => setEntregableForm({ ...entregableForm, titulo: e.target.value })}
                  maxLength={200}
                  required
                />
                <label htmlFor="entregable-descripcion">Descripción</label>
                <textarea
                  id="entregable-descripcion"
                  rows="2"
                  value={entregableForm.descripcion}
                  onChange={(e) => setEntregableForm({ ...entregableForm, descripcion: e.target.value })}
                />
                <label htmlFor="entregable-url">URL del archivo</label>
                <input
                  id="entregable-url"
                  value={entregableForm.url_archivo}
                  onChange={(e) => setEntregableForm({ ...entregableForm, url_archivo: e.target.value })}
                />
                <button type="submit" className="btn btn-primary" disabled={enviando}>
                  {enviando ? 'Subiendo...' : 'Guardar entregable'}
                </button>
              </form>
            )}

            {contrato.entregables.length > 0 ? (
              <div className="contrato-entregables-list">
                {contrato.entregables.map((entregable) => (
                  <article key={entregable.id} className="contrato-entregable">
                    <div className="contrato-entregable-top">
                      <strong>{entregable.titulo}</strong>
                      <EstadoEntregableBadge estado={entregable.estado} />
                    </div>
                    {entregable.descripcion && (
                      <p className="contrato-entregable-desc">{entregable.descripcion}</p>
                    )}
                    {entregable.url_archivo && (
                      <a href={entregable.url_archivo} target="_blank" rel="noopener noreferrer" className="contrato-entregable-link">
                        Ver archivo
                      </a>
                    )}
                    {entregable.comentario_revision && (
                      <p className="contrato-entregable-comment">
                        <strong>Revisión:</strong> {entregable.comentario_revision}
                      </p>
                    )}
                    <small className="contrato-entregable-date">
                      Subido: {formatFechaHora(entregable.fecha_subida)}
                    </small>

                    {acciones.puede_revisar_entregables && entregable.estado === 'pendiente' && (
                      <div className="form-group">
                        <textarea
                          rows="2"
                          placeholder="Comentario de revisión (opcional)"
                          value={comentariosRevision[entregable.id] || ''}
                          onChange={(e) => setComentariosRevision((actual) => ({
                            ...actual,
                            [entregable.id]: e.target.value,
                          }))}
                        />
                        <div className="catalogo-actions-group">
                          <button type="button" className="btn btn-primary btn-sm" disabled={enviando} onClick={() => revisarEntregable(entregable.id, true)}>
                            Aprobar
                          </button>
                          <button type="button" className="btn btn-secondary btn-sm" disabled={enviando} onClick={() => revisarEntregable(entregable.id, false)}>
                            Rechazar
                          </button>
                        </div>
                      </div>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <p className="catalogo-muted">Aún no hay entregables registrados.</p>
            )}
          </section>

          <section className="card contrato-section" aria-label="Pagos y liberaciones">
            <h2 className="contrato-section-title">Pagos y liberaciones</h2>
            {(contrato.pagos || []).length === 0 ? (
              <p className="catalogo-muted">Aún no se ha depositado dinero en Escrow.</p>
            ) : (
              <div className="contrato-entregables-list">
                {contrato.pagos.map((pago) => (
                  <article key={pago.id} className="contrato-entregable">
                    <div className="contrato-entregable-top">
                      <strong>{formatDinero(pago.monto)} MXN</strong>
                      <EscrowBadge estado={pago.estado_escrow} />
                    </div>
                    <p className="contrato-entregable-desc">
                      Método: {pago.metodo_pago || 'no especificado'} · Transacción: {pago.transaccion_id || '—'}
                    </p>
                    {pago.recibo && (
                      <p className="contrato-entregable-desc">
                        Recibo <strong>{pago.recibo.folio}</strong> · Total {formatDinero(pago.recibo.total)} MXN
                      </p>
                    )}
                    {(pago.liberaciones || []).map((liberacion) => (
                      <p key={liberacion.id} className="contrato-entregable-comment">
                        Liberación: {formatDinero(liberacion.monto_liberado)} MXN — {liberacion.motivo || 'sin motivo'} — {formatFechaHora(liberacion.fecha_hora)}
                      </p>
                    ))}
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="card contrato-section" aria-label="Disputas del contrato">
            <div className="contrato-documento-header">
              <h2 className="contrato-section-title">Disputas</h2>
              {acciones.puede_disputar && (
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setMostrarDisputa((valor) => !valor)}>
                  {mostrarDisputa ? 'Cancelar' : 'Abrir disputa'}
                </button>
              )}
            </div>

            {mostrarDisputa && acciones.puede_disputar && (
              <form className="form-group" onSubmit={handleDisputa}>
                <label htmlFor="disputa-tipo">Tipo</label>
                <select
                  id="disputa-tipo"
                  value={disputaForm.tipo}
                  onChange={(e) => setDisputaForm({ ...disputaForm, tipo: e.target.value })}
                >
                  <option value="pago">Pago</option>
                  <option value="entregable">Entregable</option>
                  <option value="incumplimiento">Incumplimiento</option>
                  <option value="otro">Otro</option>
                </select>
                <label htmlFor="disputa-descripcion">Descripción *</label>
                <textarea
                  id="disputa-descripcion"
                  rows="3"
                  value={disputaForm.descripcion}
                  onChange={(e) => setDisputaForm({ ...disputaForm, descripcion: e.target.value })}
                  required
                />
                <button type="submit" className="btn btn-primary" disabled={enviando}>
                  {enviando ? 'Enviando...' : 'Crear disputa'}
                </button>
              </form>
            )}

            {(contrato.disputas || []).length === 0 ? (
              <p className="catalogo-muted">No hay disputas registradas.</p>
            ) : (
              <div className="contrato-entregables-list">
                {contrato.disputas.map((disputa) => (
                  <article key={disputa.id} className="contrato-entregable">
                    <div className="contrato-entregable-top">
                      <strong>Disputa #{disputa.id} — {disputa.tipo}</strong>
                      <span className="contrato-badge contrato-badge--neutral">{disputa.estado}</span>
                    </div>
                    <p className="contrato-entregable-desc">{disputa.descripcion}</p>
                    <small className="contrato-entregable-date">
                      {formatFechaHora(disputa.fecha_hora_publicacion)}
                    </small>
                    {disputa.arbitraje && (
                      <p className="contrato-entregable-comment">
                        <strong>Decisión:</strong> {disputa.arbitraje.decision} · {disputa.arbitraje.notas || 'sin notas'}
                      </p>
                    )}
                    {esAdmin && ['abierta', 'en_revision'].includes(disputa.estado) && (
                      <div className="form-group">
                        {disputaAResolver?.id === disputa.id ? (
                          <form onSubmit={handleResolverDisputa}>
                            <label htmlFor={`decision-${disputa.id}`}>Decisión</label>
                            <select
                              id={`decision-${disputa.id}`}
                              value={resolucionForm.decision}
                              onChange={(e) => setResolucionForm({ ...resolucionForm, decision: e.target.value })}
                            >
                              <option value="liberar">Liberar al desarrollador</option>
                              <option value="reembolsar">Reembolsar al cliente</option>
                              <option value="dividir">Dividir fondos</option>
                            </select>
                            {resolucionForm.decision === 'dividir' && (
                              <>
                                <label htmlFor={`porcentaje-${disputa.id}`}>% para el desarrollador</label>
                                <input
                                  id={`porcentaje-${disputa.id}`}
                                  type="number"
                                  min="0"
                                  max="100"
                                  value={resolucionForm.porcentaje_desarrollador}
                                  onChange={(e) => setResolucionForm({ ...resolucionForm, porcentaje_desarrollador: Number(e.target.value) })}
                                />
                              </>
                            )}
                            <label htmlFor={`notas-${disputa.id}`}>Notas</label>
                            <textarea
                              id={`notas-${disputa.id}`}
                              rows="2"
                              value={resolucionForm.notas}
                              onChange={(e) => setResolucionForm({ ...resolucionForm, notas: e.target.value })}
                            />
                            <div className="catalogo-actions-group">
                              <button type="submit" className="btn btn-primary btn-sm" disabled={enviando}>Resolver</button>
                              <button type="button" className="btn btn-secondary btn-sm" onClick={() => setDisputaAResolver(null)}>Cancelar</button>
                            </div>
                          </form>
                        ) : (
                          <button type="button" className="btn btn-secondary btn-sm" onClick={() => setDisputaAResolver(disputa)}>
                            Resolver disputa
                          </button>
                        )}
                      </div>
                    )}
                  </article>
                ))}
              </div>
            )}
          </section>

          {esParte && (
            <section className="card contrato-section" aria-label="Mensajes del contrato">
              <h2 className="contrato-section-title">Mensajes</h2>
              {chat.cargando && <p className="catalogo-muted">Cargando mensajes...</p>}
              {chat.error && <div className="alert alert-danger">{chat.error.message}</div>}
              <div className="contrato-entregables-list">
                {chat.mensajes.map((mensaje) => (
                  <article key={mensaje.id} className="contrato-entregable">
                    <div className="contrato-entregable-top">
                      <strong>{mensaje.emisor?.nombre_completo || `Usuario ${mensaje.id_emisor}`}</strong>
                      <small className="contrato-entregable-date">{formatFechaHora(mensaje.fecha_hora)}</small>
                    </div>
                    <p className="contrato-entregable-desc">{mensaje.contenido}</p>
                  </article>
                ))}
                {!chat.cargando && chat.mensajes.length === 0 && (
                  <p className="catalogo-muted">Aún no hay mensajes en este contrato.</p>
                )}
              </div>
              <form className="form-group" onSubmit={handleMensaje}>
                <label htmlFor="nuevo-mensaje">Nuevo mensaje</label>
                <textarea
                  id="nuevo-mensaje"
                  rows="2"
                  value={nuevoMensaje}
                  onChange={(e) => setNuevoMensaje(e.target.value)}
                  placeholder="Escribe un mensaje para la otra parte..."
                />
                <button type="submit" className="btn btn-primary" disabled={enviando || !nuevoMensaje.trim()}>
                  {enviando ? 'Enviando...' : 'Enviar mensaje'}
                </button>
              </form>
            </section>
          )}
        </section>

        <aside className="contrato-detalle-sidebar" aria-label="Estado Escrow y acciones del contrato">
          <div className="card contrato-escrow-card">
            <span className="contrato-summary-label">Monto en custodia</span>
            <strong className="contrato-escrow-total">{formatDinero(contrato.costo_acordado)}</strong>
            <EscrowBadge estado={contrato.escrow.estado} />

            <div className="contrato-escrow-breakdown">
              <div>
                <span>Retenido</span>
                <strong>{formatDinero(contrato.escrow.monto_retenido)}</strong>
              </div>
              <div>
                <span>Liberado</span>
                <strong>{formatDinero(contrato.escrow.monto_liberado)}</strong>
              </div>
            </div>

            <div className="escrow-guarantee-badge">
              <ShieldCheckIcon size={15} />
              <span>Protección al comprador y al desarrollador</span>
            </div>
            <p className="escrow-guarantee-hint">
              El dinero permanece en custodia hasta que el cliente valide los entregables.
            </p>
          </div>

          <div className="card contrato-acciones-card">
            {acciones.puede_firmar && !mostrandoConfirmacion && (
              <button type="button" className="btn btn-primary contrato-main-cta" onClick={() => setMostrandoConfirmacion(true)}>
                <ShieldCheckIcon size={17} />
                <span>{etiquetaAceptar}</span>
              </button>
            )}

            {acciones.puede_firmar && mostrandoConfirmacion && (
              <div className="contrato-confirm-box">
                <h3 className="contrato-confirm-title">Confirmar aceptación</h3>
                <p className="contrato-confirm-text">
                  Al confirmar se registra tu firma con fecha, hora y dirección IP. Esta acción no se puede deshacer.
                </p>
                <label className="contrato-confirm-check">
                  <input type="checkbox" checked={acepto} onChange={(e) => setAcepto(e.target.checked)} />
                  <span>He leído y acepto los términos y condiciones de este contrato.</span>
                </label>
                <div className="contrato-confirm-actions">
                  <button type="button" className="btn btn-secondary" onClick={() => { setMostrandoConfirmacion(false); setAcepto(false); }} disabled={enviando}>
                    Cancelar
                  </button>
                  <button type="button" className="btn btn-primary" onClick={handleAceptar} disabled={!acepto || enviando} aria-busy={enviando}>
                    {enviando ? 'Procesando...' : 'Confirmar aceptación'}
                  </button>
                </div>
              </div>
            )}

            {acciones.puede_liberar && (
              <button type="button" className="btn btn-primary contrato-main-cta" onClick={handleLiberar} disabled={enviando}>
                <ShieldCheckIcon size={17} />
                <span>{enviando ? 'Liberando...' : 'Liberar fondos al desarrollador'}</span>
              </button>
            )}

            {acciones.puede_calificar && (
              <div className="form-group">
                {mostrarCalificar ? (
                  <form onSubmit={handleCalificar}>
                    <label htmlFor="calificacion-puntaje">Calificación</label>
                    <select
                      id="calificacion-puntaje"
                      value={calificacionForm.puntaje}
                      onChange={(e) => setCalificacionForm({ ...calificacionForm, puntaje: Number(e.target.value) })}
                    >
                      {[5, 4, 3, 2, 1].map((valor) => (
                        <option key={valor} value={valor}>{valor} estrellas</option>
                      ))}
                    </select>
                    <label htmlFor="calificacion-comentarios">Comentarios</label>
                    <textarea
                      id="calificacion-comentarios"
                      rows="2"
                      value={calificacionForm.comentarios}
                      onChange={(e) => setCalificacionForm({ ...calificacionForm, comentarios: e.target.value })}
                    />
                    <div className="catalogo-actions-group">
                      <button type="submit" className="btn btn-primary btn-sm" disabled={enviando}>Enviar</button>
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setMostrarCalificar(false)}>Cancelar</button>
                    </div>
                  </form>
                ) : (
                  <button type="button" className="btn btn-secondary" onClick={() => setMostrarCalificar(true)}>
                    Calificar contrato
                  </button>
                )}
              </div>
            )}

            {!acciones.puede_firmar && acciones.ya_firme && (
              <p className="contrato-accion-nota contrato-accion-nota--ok">Ya firmaste este contrato.</p>
            )}

            {!acciones.es_parte && (
              <p className="contrato-accion-nota">
                Solo las partes del contrato pueden firmar o gestionar este acuerdo.
              </p>
            )}

            {!acciones.puede_firmar && !acciones.ya_firme && acciones.es_parte && (
              <p className="contrato-accion-nota">
                Este contrato ya no requiere tu firma en su estado actual.
              </p>
            )}

            <Link to="/contratos" className="contrato-back-link">← Volver a contratos</Link>
          </div>
        </aside>
      </div>
    </div>
  );
}
