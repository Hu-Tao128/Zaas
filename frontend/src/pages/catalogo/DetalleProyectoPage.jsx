import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { AlertaError, Badge, BadgeEstado, Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import { formatDinero, formatFecha, urlContratarProyecto } from './catalogoUtils';

/**
 * Vista de Detalles del Proyecto SaaS refactorizada.
 * Implementa un layout de dos columnas, jerarquía visual de alto contraste,
 * precio focal con insignia Escrow, enlace al perfil del autor,
 * previsualización estética y llamadas a la acción (CTA) unificadas.
 */
export default function DetalleProyectoPage() {
  const { id } = useParams();
  const { usuario } = useCatalogo();
  const navigate = useNavigate();
  const location = useLocation();
  const { data, loading, error } = useApi(() => catalogoApi.proyecto(id), [id]);
  const [errorAccion, setErrorAccion] = useState('');

  if (loading) return <Cargando />;
  if (error) return <ErrorCard error={error} />;

  const { proyecto, es_dueno: esDueno } = data;

  async function handleCerrar() {
    if (!window.confirm('¿Cerrar este proyecto? Dejará de aparecer en el catálogo público.')) return;
    setErrorAccion('');
    try {
      const respuesta = await catalogoApi.cerrarProyecto(proyecto.id);
      navigate('/mis-productos', { state: { mensaje: respuesta.mensaje } });
    } catch (err) {
      setErrorAccion(err.message);
    }
  }

  const autorNombreCompleto = `${proyecto.autor.nombres} ${proyecto.autor.apellido_paterno}`;
  const inicialAutor = proyecto.autor.nombres?.charAt(0)?.toUpperCase() || 'D';

  return (
    <div className="proyecto-detalle-container">
      {/* Mensajes de feedback accesibles */}
      {location.state?.mensaje && (
        <div className="alert alert-success" role="status">
          {location.state.mensaje}
        </div>
      )}
      <AlertaError>{errorAccion}</AlertaError>

      {/* Navegación de migas de pan (Breadcrumbs) accesible */}
      <nav aria-label="Migas de pan" className="proyecto-breadcrumbs">
        <Link to="/">Catálogo</Link>
        <span aria-hidden="true">/</span>
        <span className="current" aria-current="page">{proyecto.titulo}</span>
      </nav>

      {/* Layout de dos columnas en escritorio */}
      <div className="proyecto-detalle-layout">
        {/* Columna Principal (Izquierda) */}
        <section className="proyecto-detalle-main" aria-label="Información principal del SaaS">
          {/* Contenedor de Portada o Previsualización Estética */}
          <div className="proyecto-cover-wrapper">
            {proyecto.imagen_url ? (
              <img
                src={proyecto.imagen_url}
                alt={`Captura de pantalla de la plataforma ${proyecto.titulo}`}
                className="proyecto-cover-image"
              />
            ) : (
              <div className="proyecto-cover-fallback" role="img" aria-label={`Previsualización gráfica de ${proyecto.titulo}`}>
                {/* Patrón SVG decorativo usando Rojo suave (#F87171) y Gris claro (#F5F5F5) */}
                <svg
                  className="proyecto-cover-pattern"
                  aria-hidden="true"
                  width="100%"
                  height="100%"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <defs>
                    <pattern
                      id="saas-grid-pattern"
                      width="32"
                      height="32"
                      patternUnits="userSpaceOnUse"
                    >
                      <path
                        d="M 32 0 L 0 0 0 32"
                        fill="none"
                        stroke="rgba(248, 113, 113, 0.22)"
                        strokeWidth="1"
                      />
                      <circle cx="16" cy="16" r="1.5" fill="rgba(248, 113, 113, 0.35)" />
                    </pattern>
                  </defs>
                  <rect width="100%" height="100%" fill="#F5F5F5" />
                  <rect width="100%" height="100%" fill="url(#saas-grid-pattern)" />
                </svg>

                {/* Mockup visual representativo de SaaS */}
                <div className="proyecto-cover-mockup">
                  <div className="mockup-header" aria-hidden="true">
                    <span className="mockup-dot mockup-dot--red" />
                    <span className="mockup-dot mockup-dot--yellow" />
                    <span className="mockup-dot mockup-dot--green" />
                    <span className="mockup-title-bar">{proyecto.titulo}.app</span>
                  </div>
                  <div className="mockup-body" aria-hidden="true">
                    <div className="mockup-icon-badge">
                      <svg
                        width="36"
                        height="36"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="#991B1B"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                        <line x1="8" y1="21" x2="16" y2="21" />
                        <line x1="12" y1="17" x2="12" y2="21" />
                        <polyline points="7 10 10 13 17 7" />
                      </svg>
                    </div>
                    <span className="mockup-caption">Plataforma SaaS Verificada</span>
                  </div>
                </div>

                <div className="proyecto-cover-tag" aria-hidden="true">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  </svg>
                  <span>Transferencia Segura en Escrow</span>
                </div>
              </div>
            )}
          </div>

          {/* Encabezado y Título Principal */}
          <div className="proyecto-header-block card">
            <div className="proyecto-status-row">
              {proyecto.estado === 'activo' ? (
                <span className="zaas-badge zaas-badge--abierto">
                  <span className="status-indicator status-indicator--green" aria-hidden="true" />
                  <span>Disponible para compra</span>
                </span>
              ) : (
                <span className="zaas-badge zaas-badge--cerrado">
                  <span className="status-indicator status-indicator--gray" aria-hidden="true" />
                  <span>Cerrado / No disponible</span>
                </span>
              )}

              {proyecto.demo_habilitada && (
                <span className="zaas-badge zaas-badge--demo" title="Demostración disponible para probar este SaaS">
                  <svg className="zaas-badge-icon" aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                  <span>Demo interactiva habilitada</span>
                </span>
              )}
            </div>

            {/* Título focal en alto contraste: text-[#171717] y tipografía destacada */}
            <h1 className="proyecto-detalle-title">{proyecto.titulo}</h1>

            {/* Categorías y Tecnologías */}
            {(proyecto.categorias?.length > 0 || proyecto.tecnologias?.length > 0) && (
              <div className="proyecto-tags-container" aria-label="Categorías y tecnologías del producto">
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
          </div>

          {/* Descripción detallada */}
          <article className="proyecto-description-card card">
            <h2 className="proyecto-card-subtitle">Descripción del SaaS</h2>
            <div className="proyecto-description-text">
              {proyecto.descripcion ? (
                proyecto.descripcion.split('\n').map((parrafo, i) =>
                  parrafo.trim() ? <p key={i}>{parrafo}</p> : null
                )
              ) : (
                <p className="catalogo-muted">Sin descripción detallada disponible.</p>
              )}
            </div>

            {/* Beneficios de la compra protegida por Escrow */}
            <div className="proyecto-escrow-explainer">
              <h3 className="escrow-explainer-title">
                <svg
                  aria-hidden="true"
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="#991B1B"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                  <path d="m9 12 2 2 4-4" />
                </svg>
                <span>¿Cómo funciona la Garantía Escrow de Zaas?</span>
              </h3>
              <ol className="escrow-steps-list">
                <li>
                  <strong>1. Depósito en Garantía:</strong> Al hacer clic en <em>Contratar</em>, tus fondos se resguardan de forma segura en la cuenta de fideicomiso Escrow de Zaas.
                </li>
                <li>
                  <strong>2. Transferencia de Activos:</strong> El desarrollador te transfiere el repositorio de código, bases de datos, credenciales y dominios asociados.
                </li>
                <li>
                  <strong>3. Validación y Liberación:</strong> Tras comprobar el funcionamiento del software, apruebas la entrega y el pago se libera al desarrollador.
                </li>
              </ol>
            </div>
          </article>
        </section>

        {/* Columna Derecha (Barra Lateral de Resumen y CTAs) */}
        <aside className="proyecto-detalle-sidebar" aria-label="Resumen de adquisición y acciones">
          <div className="card proyecto-summary-card">
            {/* Elemento Focal: Precio Grande con Badge de Escrow */}
            <div className="proyecto-price-section">
              <span className="proyecto-price-caption">Precio de Adquisición</span>
              <div className="proyecto-price-highlight" aria-label={`Precio: ${formatDinero(proyecto.precio)}`}>
                {formatDinero(proyecto.precio)}
              </div>

              {/* Insignia Escrow Prominente */}
              <div className="escrow-guarantee-badge">
                <svg
                  aria-hidden="true"
                  width="16"
                  height="16"
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
                <span>Protegido al 100% por Escrow</span>
              </div>
              <p className="escrow-guarantee-hint">
                Tus fondos no se transfieren al vendedor hasta que recibas y valides todo el código fuente.
              </p>
            </div>

            <hr className="proyecto-sidebar-divider" />

            {/* Autor convertido en Enlace a su Perfil */}
            <div className="proyecto-author-section">
              <span className="sidebar-meta-label">Desarrollador / Vendedor</span>
              <Link
                to={`/perfil/${proyecto.autor.id}`}
                className="proyecto-author-link"
                title={`Ver el perfil y reputación de ${autorNombreCompleto}`}
              >
                <div className="author-avatar-badge" aria-hidden="true">
                  {inicialAutor}
                </div>
                <div className="author-info">
                  <span className="author-name">{autorNombreCompleto}</span>
                  <span className="author-profile-action">Ver perfil y reputación →</span>
                </div>
              </Link>
            </div>

            {/* Metadatos adicionales */}
            <div className="proyecto-meta-section">
              <div className="meta-item">
                <span className="sidebar-meta-label">Fecha de publicación</span>
                <span className="sidebar-meta-value">
                  <svg
                    aria-hidden="true"
                    width="14"
                    height="14"
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
                  <span>{formatFecha(proyecto.fecha_publicacion)}</span>
                </span>
              </div>

              <div className="meta-item">
                <span className="sidebar-meta-label">Estado actual</span>
                <span className="sidebar-meta-value">
                  <BadgeEstado estado={proyecto.estado} />
                </span>
              </div>
            </div>

            <hr className="proyecto-sidebar-divider" />

            {/* Llamadas a la Acción (CTAs) con colores oficiales */}
            <div className="proyecto-sidebar-actions">
              {proyecto.estado !== 'activo' ? (
                <div className="alert alert-warning">
                  Este SaaS está cerrado y no se encuentra disponible para compra.
                </div>
              ) : !esDueno ? (
                <>
                  {/* CTA Primario: 'Contratar' en Rojo Principal (#DC2626) con texto blanco */}
                  {usuario.tipo_usuario === 'cliente' ? (
                    <Link
                      to={urlContratarProyecto(proyecto)}
                      className="btn btn-primary btn-contratar-cta"
                      aria-label={`Iniciar contrato de compra con Escrow para ${proyecto.titulo}`}
                    >
                      <svg
                        aria-hidden="true"
                        width="18"
                        height="18"
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
                      <span>Contratar con Escrow</span>
                    </Link>
                  ) : (
                    <div className="catalogo-muted" style={{ fontSize: '0.85rem', textAlign: 'center', marginBottom: '0.5rem' }}>
                      Inicia sesión como cliente para adquirir este SaaS con Escrow.
                    </div>
                  )}

                  {/* Botón de Demostración */}
                  {proyecto.demo_habilitada && (
                    <Link
                      to={`/proyecto/${proyecto.id}/demo`}
                      className="btn btn-secondary btn-demo-action"
                    >
                      <svg
                        aria-hidden="true"
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="currentColor"
                      >
                        <polygon points="5 3 19 12 5 21 5 3" />
                      </svg>
                      <span>Solicitar Demo</span>
                    </Link>
                  )}
                </>
              ) : null}

              {/* Acciones para el Propietario */}
              {esDueno && (
                <div className="proyecto-owner-actions">
                  <Link
                    to={`/proyecto/${proyecto.id}/editar`}
                    className="btn btn-secondary btn-sm"
                  >
                    Editar proyecto
                  </Link>
                  {proyecto.estado === 'activo' && (
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={handleCerrar}
                    >
                      Cerrar proyecto
                    </button>
                  )}
                  <Link to="/mis-productos" className="btn btn-secondary btn-sm">
                    Mis productos
                  </Link>
                </div>
              )}

              {/* CTA Secundario: 'Ver catálogo' con fondo transparente, borde y texto en #404040 */}
              <Link to="/" className="btn btn-secondary btn-ver-catalogo">
                Ver catálogo
              </Link>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
