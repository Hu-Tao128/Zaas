import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { contratosApi } from '../../services/contratosApi';
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

  const [mostrandoConfirmacion, setMostrandoConfirmacion] = useState(false);
  const [acepto, setAcepto] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [mensajeAccion, setMensajeAccion] = useState('');
  const [errorAccion, setErrorAccion] = useState('');

  if (loading) return <CargandoContratos mensaje="Cargando contrato..." />;
  if (error) {
    return (
      <div className="contratos-page">
        <ErrorContratos error={error} onReintentar={recargar} />
        <Link to="/contratos" className="btn btn-secondary">Volver a contratos</Link>
      </div>
    );
  }

  const contrato = data.contrato;
  const acciones = contrato.acciones;
  const etiquetaAceptar = acciones.soy_cliente && contrato.escrow.estado === 'sin_deposito'
    ? 'Aceptar y Depositar en Escrow'
    : 'Aceptar y Firmar Contrato';

  async function handleAceptar() {
    if (!acepto || enviando) return;
    setEnviando(true);
    setErrorAccion('');
    setMensajeAccion('');
    try {
      const respuesta = await contratosApi.aceptar(contrato.id);
      setMensajeAccion(respuesta.mensaje || 'Contrato aceptado.');
      setMostrandoConfirmacion(false);
      setAcepto(false);
      recargar();
    } catch (err) {
      setErrorAccion(err.message || 'No se pudo aceptar el contrato.');
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

      {mensajeAccion && (
        <div className="alert alert-success" role="status">{mensajeAccion}</div>
      )}
      {errorAccion && (
        <div className="alert alert-danger" role="alert">{errorAccion}</div>
      )}

      <header className="card contrato-header-card">
        <div className="contrato-header-top">
          <div className="contrato-header-tags">
            <EstadoContratoBadge estado={contrato.estado} />
            <RolBadge rol={contrato.rol} />
            <EscrowBadge estado={contrato.escrow.estado} />
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm no-print"
            onClick={() => window.print()}
          >
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
        </div>
      </header>

      <div className="contrato-detalle-layout">
        <section className="contrato-detalle-main" aria-label="Documento y firmas del contrato">
          <article className="card contrato-documento-card">
            <div className="contrato-documento-header">
              <h2 className="contrato-section-title">Documento del contrato</h2>
              <span className="contrato-documento-copy">
                Copia inmutable de los términos aceptados
              </span>
            </div>

            <div className="contrato-documento-scroll" tabIndex={0} aria-label="Documento legal del contrato">
              {contrato.documento_html ? (
                <div
                  className="contrato-documento"
                  // El HTML proviene de la plantilla del servidor; los datos del usuario
                  // ya se escapan en render_plantilla() antes de llegar aquí.
                  dangerouslySetInnerHTML={{ __html: contrato.documento_html }}
                />
              ) : (
                <div className="alert alert-warning">
                  Este contrato todavía no tiene términos generados.
                </div>
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

          {contrato.entregables.length > 0 && (
            <section className="card contrato-section" aria-label="Entregables del contrato">
              <h2 className="contrato-section-title">Entregables</h2>
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
                      <a
                        href={entregable.url_archivo}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="contrato-entregable-link"
                      >
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
                  </article>
                ))}
              </div>
            </section>
          )}
        </section>

        <aside className="contrato-detalle-sidebar" aria-label="Estado Escrow y acciones del contrato">
          <div className="card contrato-escrow-card">
            <span className="contrato-summary-label">Monto en custodia</span>
            <strong className="contrato-escrow-total">
              {formatDinero(contrato.costo_acordado)}
            </strong>
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
              <button
                type="button"
                className="btn btn-primary contrato-main-cta"
                onClick={() => setMostrandoConfirmacion(true)}
              >
                <ShieldCheckIcon size={17} />
                <span>{etiquetaAceptar}</span>
              </button>
            )}

            {acciones.puede_firmar && mostrandoConfirmacion && (
              <div className="contrato-confirm-box">
                <h3 className="contrato-confirm-title">Confirmar aceptación</h3>
                <p className="contrato-confirm-text">
                  Al confirmar se registra tu firma con fecha, hora y dirección IP. Esta acción
                  no se puede deshacer.
                </p>

                <label className="contrato-confirm-check">
                  <input
                    type="checkbox"
                    checked={acepto}
                    onChange={(e) => setAcepto(e.target.checked)}
                  />
                  <span>He leído y acepto los términos y condiciones de este contrato.</span>
                </label>

                <div className="contrato-confirm-actions">
                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={() => { setMostrandoConfirmacion(false); setAcepto(false); }}
                    disabled={enviando}
                  >
                    Cancelar
                  </button>
                  <button
                    type="button"
                    className="btn btn-primary"
                    onClick={handleAceptar}
                    disabled={!acepto || enviando}
                    aria-busy={enviando}
                  >
                    {enviando ? 'Procesando...' : 'Confirmar aceptación'}
                  </button>
                </div>
              </div>
            )}

            {!acciones.puede_firmar && acciones.ya_firme && (
              <p className="contrato-accion-nota contrato-accion-nota--ok">
                Ya firmaste este contrato.
              </p>
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

            <Link to="/contratos" className="contrato-back-link">
              ← Volver a contratos
            </Link>
          </div>
        </aside>
      </div>
    </div>
  );
}
