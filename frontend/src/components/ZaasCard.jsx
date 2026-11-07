import { Link } from 'react-router-dom';
import { formatDinero, formatFecha, recortar } from '../pages/catalogo/catalogoUtils';

/**
 * Componente Card reutilizable para Zaas con variantes para:
 * - 'proyecto' (Catálogo de SaaS)
 * - 'oferta' (Ofertas de Trabajo / Encargos)
 *
 * Cumple con WCAG (contraste >= 4.5:1, semántica <article>, jerarquía tipográfica)
 * y destaca el sistema de custodia Escrow y los precios de forma profesional.
 *
 * @param {Object} props
 * @param {'proyecto' | 'oferta'} props.variant - Variante de la tarjeta
 * @param {Object} props.data - Datos del proyecto o de la oferta
 * @param {Object} [props.usuario] - Datos del usuario autenticado
 */
export default function ZaasCard({ variant = 'proyecto', data, usuario }) {
  if (!data) return null;

  const esProyecto = variant === 'proyecto' || variant === 'saas';

  if (esProyecto) {
    return <ProyectoCard proyecto={data} />;
  }

  return <OfertaCard oferta={data} usuario={usuario} />;
}

/**
 * Variante de Tarjeta para Proyectos SaaS en Venta
 */
function ProyectoCard({ proyecto }) {
  const tituloId = `proyecto-card-title-${proyecto.id}`;
  const descripcionCorta = recortar(proyecto.descripcion, 130) || 'Sin descripción disponible.';

  return (
    <article
      className="card zaas-card zaas-card--proyecto"
      aria-labelledby={tituloId}
    >
      {/* Encabezado superior con insignias semánticas: Garantía Escrow y Demo */}
      <div className="zaas-card-top-bar">
        {/* Insignia Escrow Profesional */}
        <div
          className="zaas-escrow-badge"
          title="Custodia de pago Zaas Escrow: El dinero permanece seguro hasta verificar y transferir el SaaS"
        >
          <svg
            className="zaas-escrow-icon"
            aria-hidden="true"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
          <span>Garantía Escrow</span>
        </div>

        {/* Insignia Demo con Icono de Play (Heurística Nielsen #1 & #2) */}
        {proyecto.demo_habilitada && (
          <span
            className="zaas-badge zaas-badge--demo"
            title="Este SaaS cuenta con demostración interactiva disponible"
          >
            <svg
              className="zaas-badge-icon"
              aria-hidden="true"
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="currentColor"
            >
              <polygon points="5 3 19 12 5 21 5 3" />
            </svg>
            <span>Demo disponible</span>
          </span>
        )}
      </div>

      {/* Título accesible: color #404040 (contraste AAA > 7:1), hover en rojo #DC2626 con subrayado */}
      <h3 id={tituloId} className="zaas-card-title">
        <Link to={`/proyecto/${proyecto.id}`} className="zaas-card-title-link">
          {proyecto.titulo}
        </Link>
      </h3>

      {/* Descripción concisa */}
      <p className="zaas-card-description">{descripcionCorta}</p>

      {/* Etiquetas de Categorías y Tecnologías con contraste accesible */}
      {(proyecto.categorias?.length > 0 || proyecto.tecnologias?.length > 0) && (
        <div className="zaas-card-tags" aria-label="Categorías y tecnologías aplicadas">
          {proyecto.categorias?.map((cat) => (
            <span key={`cat-${cat.id}`} className="zaas-tag zaas-tag--category">
              {cat.nombre}
            </span>
          ))}
          {proyecto.tecnologias?.map((tec) => (
            <span key={`tec-${tec.id}`} className="zaas-tag zaas-tag--tech">
              {tec.nombre}
            </span>
          ))}
        </div>
      )}

      {/* Bloque inferior: Precio destacado y metadatos */}
      <div className="zaas-card-footer">
        <div className="zaas-price-block">
          <span className="zaas-price-label">Precio de venta</span>
          <strong className="zaas-price-amount">{formatDinero(proyecto.precio)}</strong>
        </div>

        <div className="zaas-card-actions">
          <Link
            to={`/proyecto/${proyecto.id}`}
            className="btn btn-secondary btn-sm"
            aria-label={`Ver detalles y adquirir ${proyecto.titulo}`}
          >
            Ver detalles
          </Link>
        </div>
      </div>

      {/* Metadatos secundarios al pie */}
      <div className="zaas-card-meta">
        <span className="zaas-card-date">
          Publicado el {formatFecha(proyecto.fecha_publicacion)}
        </span>
        {proyecto.autor && (
          <span className="zaas-card-author">
            Por {proyecto.autor.nombres} {proyecto.autor.apellido_paterno}
          </span>
        )}
      </div>
    </article>
  );
}

/**
 * Variante de Tarjeta para Ofertas de Trabajo y Contratación con Escrow
 */
function OfertaCard({ oferta, usuario }) {
  const tituloId = `oferta-card-title-${oferta.id}`;
  const descripcionCorta =
    recortar(oferta.descripcion_requerimientos, 140) || 'Sin descripción detallada.';
  const esDesarrollador = usuario?.tipo_usuario === 'desarrollador';

  // Configuración de estado con icono semántico y alto contraste
  const estadoConfig = {
    abierto: {
      label: 'Abierto',
      clase: 'zaas-badge--abierto',
      icono: (
        <span className="status-indicator status-indicator--green" aria-hidden="true" />
      ),
      descripcion: 'Aceptando postulaciones de desarrolladores',
    },
    en_progreso: {
      label: 'En progreso',
      clase: 'zaas-badge--progreso',
      icono: (
        <span className="status-indicator status-indicator--amber" aria-hidden="true" />
      ),
      descripcion: 'Desarrollador asignado en fase de entrega',
    },
    cerrado: {
      label: 'Cerrado',
      clase: 'zaas-badge--cerrado',
      icono: (
        <span className="status-indicator status-indicator--gray" aria-hidden="true" />
      ),
      descripcion: 'Oferta finalizada o no disponible',
    },
  };

  const estadoInfo = estadoConfig[oferta.estado] || {
    label: oferta.estado?.replaceAll('_', ' ') || 'Indefinido',
    clase: 'zaas-badge--neutral',
    icono: null,
    descripcion: '',
  };

  return (
    <article
      className="card zaas-card zaas-card--oferta"
      aria-labelledby={tituloId}
    >
      {/* Barra superior con Estado del Sistema y Protección de Contrato Escrow */}
      <div className="zaas-card-top-bar">
        {/* Estado del sistema con icono para reducir carga cognitiva (Nielsen Heuristic #1 & #2) */}
        <span
          className={`zaas-badge ${estadoInfo.clase}`}
          title={estadoInfo.descripcion}
          aria-label={`Estado de la oferta: ${estadoInfo.label}`}
        >
          {estadoInfo.icono}
          <span>{estadoInfo.label}</span>
        </span>

        {/* Insignia de Contrato Escrow */}
        <div
          className="zaas-escrow-badge"
          title="Contrato con protección Escrow: El cliente deposita los fondos en garantía y se liberan por hitos completados"
        >
          <svg
            className="zaas-escrow-icon"
            aria-hidden="true"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            <path d="m9 12 2 2 4-4" />
          </svg>
          <span>Contrato Escrow</span>
        </div>
      </div>

      {/* Título en Gris Oscuro #404040 (ratio 7:1), interacción en Rojo #DC2626 */}
      <h3 id={tituloId} className="zaas-card-title">
        <Link to={`/oferta/${oferta.id}`} className="zaas-card-title-link">
          {oferta.titulo}
        </Link>
      </h3>

      {/* Requerimientos resumidos */}
      <p className="zaas-card-description">{descripcionCorta}</p>

      {/* Información clave: Presupuesto Escrow y Fecha de Entrega */}
      <div className="zaas-card-info-grid">
        <div className="zaas-info-item">
          <span className="zaas-info-label">Presupuesto Escrow</span>
          <strong className="zaas-info-highlight">
            {oferta.presupuesto ? formatDinero(oferta.presupuesto) : 'Por convenir'}
          </strong>
        </div>

        {oferta.fecha_entrega && (
          <div className="zaas-info-item">
            <span className="zaas-info-label">Fecha límite de entrega</span>
            <span className="zaas-info-value">
              <svg
                aria-hidden="true"
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
                <line x1="16" y1="2" x2="16" y2="6" />
                <line x1="8" y1="2" x2="8" y2="6" />
                <line x1="3" y1="10" x2="21" y2="10" />
              </svg>
              <span>{formatFecha(oferta.fecha_entrega)}</span>
            </span>
          </div>
        )}
      </div>

      {/* Pie con Acciones y Enlaces */}
      <div className="zaas-card-footer">
        <div className="zaas-card-meta-text">
          <span className="zaas-card-date">
            Publicada el {formatFecha(oferta.fecha_publicacion)}
          </span>
          {typeof oferta.num_postulaciones === 'number' && (
            <span className="zaas-card-proposals">
              {oferta.num_postulaciones}{' '}
              {oferta.num_postulaciones === 1 ? 'postulación' : 'postulaciones'}
            </span>
          )}
        </div>

        <div className="zaas-card-actions">
          {esDesarrollador && oferta.estado === 'abierto' && (
            <Link
              to={`/oferta/${oferta.id}/postular`}
              className="btn btn-primary btn-sm"
              aria-label={`Postularse a la oferta ${oferta.titulo}`}
            >
              Postularme
            </Link>
          )}
          <Link
            to={`/oferta/${oferta.id}`}
            className="btn btn-secondary btn-sm"
            aria-label={`Ver detalles de la oferta ${oferta.titulo}`}
          >
            Ver oferta
          </Link>
        </div>
      </div>
    </article>
  );
}
