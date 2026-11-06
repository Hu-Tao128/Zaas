import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { useCatalogo } from '../../context/CatalogoContext';
import { useApi } from '../../hooks/useApi';
import { catalogoApi } from '../../services/catalogoApi';
import { Badge, BadgeEstado, Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';
import Toast from '../../components/Toast';
import { formatDinero, formatFecha } from './catalogoUtils';

/**
 * Componente de Perfil de Usuario de Zaas (/perfil y /perfil/:id).
 * Mapea los modelos reales de SQLAlchemy (Usuario, Perfil, Calificacion, Contrato).
 * Incluye navegación por pestañas accesibles (role="tablist"),
 * vista pública adaptada por rol (Cliente/Desarrollador) y formulario controlado
 * de edición con validaciones y notificaciones toast.
 */
export default function PerfilPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const { usuario: usuarioAutenticado } = useCatalogo();

  // Si hay id en la URL cargamos ese perfil; si no, cargamos el perfil del usuario actual
  const { data, loading, error, recargar } = useApi(
    () => (id ? catalogoApi.obtenerPerfil(id) : catalogoApi.miPerfil()),
    [id]
  );

  const [pestañaActiva, setPestañaActiva] = useState('publico');
  const [toastMensaje, setToastMensaje] = useState('');
  const [toastTipo, setToastTipo] = useState('success');

  // Si cambia de usuario o ID, volvemos a la pestaña de vista pública
  useEffect(() => {
    setPestañaActiva('publico');
  }, [id]);

  if (loading) return <Cargando />;
  if (error) return <ErrorCard error={error} volverA="/" volverTexto="Volver al catálogo" />;
  if (!data?.usuario) return <ErrorCard error={new Error('No se encontró el perfil')} />;

  const { usuario, perfil, estadisticas, proyectos = [], ofertas = [], calificaciones = [], contratos = [], es_propio } = data;
  const esDesarrollador = usuario.tipo_usuario === 'desarrollador';
  const nombreCompleto = `${usuario.nombres} ${usuario.apellido_paterno} ${usuario.apellido_materno || ''}`.trim();
  const inicial = usuario.nombres?.charAt(0)?.toUpperCase() || 'U';

  // Habilidades y enlaces mapeados de campos de texto
  const listaHabilidades = perfil.habilidades
    ? perfil.habilidades.split(',').map((h) => h.trim()).filter(Boolean)
    : [];

  const listaEnlaces = perfil.enlaces
    ? perfil.enlaces.split(',').map((e) => e.trim()).filter(Boolean)
    : [];

  function mostrarToast(mensaje, tipo = 'success') {
    setToastMensaje(mensaje);
    setToastTipo(tipo);
  }

  return (
    <div className="zaas-profile-container">
      {/* Notificación Toast accesible para confirmaciones */}
      <Toast
        mensaje={toastMensaje}
        tipo={toastTipo}
        onClose={() => setToastMensaje('')}
      />

      {/* Cabecera Principal del Perfil */}
      <header className="card zaas-profile-header" role="region" aria-label="Encabezado del perfil de usuario">
        <div className="zaas-profile-header-main">
          {/* Avatar del usuario con inicial */}
          <div className="zaas-profile-avatar" aria-hidden="true">
            {inicial}
          </div>

          <div className="zaas-profile-title-block">
            <div className="zaas-profile-name-row">
              <h1 className="zaas-profile-name">{nombreCompleto}</h1>
              <span className={`navbar-role-badge navbar-role-badge--${usuario.tipo_usuario}`}>
                {esDesarrollador ? 'Desarrollador' : 'Cliente'}
              </span>
              {es_propio && <span className="zaas-badge zaas-badge--propio">Tu Perfil</span>}
            </div>

            {perfil.empresa && (
              <p className="zaas-profile-company">
                <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                  <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
                </svg>
                <span>{perfil.empresa}</span>
              </p>
            )}

            <p className="zaas-profile-joined">
              Miembro de Zaas desde {formatFecha(usuario.fecha_registro)}
            </p>
          </div>
        </div>

        {/* Panel de Estadísticas y Reputación */}
        <div className="zaas-profile-stats-grid">
          <div className="zaas-profile-stat-box">
            <span className="stat-value">{estadisticas.contratos_completados || 0}</span>
            <span className="stat-label">Contratos Escrow</span>
          </div>

          <div className="zaas-profile-stat-box">
            <span className="stat-value">
              {estadisticas.promedio_calificacion ? `${estadisticas.promedio_calificacion} ★` : 'Nuevo'}
            </span>
            <span className="stat-label">
              {estadisticas.total_calificaciones
                ? `${estadisticas.total_calificaciones} valoraciones`
                : 'Sin calificaciones'}
            </span>
          </div>

          {esDesarrollador ? (
            <div className="zaas-profile-stat-box">
              <span className="stat-value">{estadisticas.total_proyectos || 0}</span>
              <span className="stat-label">SaaS en Venta</span>
            </div>
          ) : (
            <div className="zaas-profile-stat-box">
              <span className="stat-value">{estadisticas.total_ofertas || 0}</span>
              <span className="stat-label">Ofertas Publicadas</span>
            </div>
          )}
        </div>
      </header>

      {/* Navegación interna por pestañas (Heurística Nielsen #7 y WCAG Tabs) */}
      <nav className="zaas-tabs-nav" role="tablist" aria-label="Secciones del perfil">
        <button
          type="button"
          id="tab-publico"
          role="tab"
          aria-selected={pestañaActiva === 'publico'}
          aria-controls="panel-publico"
          className={`zaas-tab-button ${pestañaActiva === 'publico' ? 'zaas-tab-button--active' : ''}`}
          onClick={() => setPestañaActiva('publico')}
        >
          <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          <span>Información Pública</span>
        </button>

        {es_propio && (
          <button
            type="button"
            id="tab-configuracion"
            role="tab"
            aria-selected={pestañaActiva === 'configuracion'}
            aria-controls="panel-configuracion"
            className={`zaas-tab-button ${pestañaActiva === 'configuracion' ? 'zaas-tab-button--active' : ''}`}
            onClick={() => setPestañaActiva('configuracion')}
          >
            <svg aria-hidden="true" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 20h9" />
              <path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z" />
            </svg>
            <span>Configuración / Editar Perfil</span>
          </button>
        )}
      </nav>

      {/* Panel 1: Información Pública */}
      {pestañaActiva === 'publico' && (
        <div
          id="panel-publico"
          role="tabpanel"
          aria-labelledby="tab-publico"
          className="zaas-tab-panel"
        >
          <div className="zaas-profile-public-layout">
            {/* Columna Izquierda: Biografía, Habilidades, Stack y Enlaces */}
            <div className="zaas-profile-col-left">
              {/* Biografía / Acerca de mí */}
              <section className="card zaas-profile-section" aria-label="Biografía">
                <h2 className="zaas-section-heading">Acerca de</h2>
                <div className="zaas-bio-content">
                  {perfil.descripcion ? (
                    perfil.descripcion.split('\n').map((p, idx) =>
                      p.trim() ? <p key={idx}>{p}</p> : null
                    )
                  ) : (
                    <p className="catalogo-muted">Este usuario aún no ha agregado una descripción.</p>
                  )}
                </div>
              </section>

              {/* Habilidades Técnicas */}
              {listaHabilidades.length > 0 && (
                <section className="card zaas-profile-section" aria-label="Habilidades">
                  <h2 className="zaas-section-heading">Habilidades y Especialidades</h2>
                  <div className="zaas-skills-cloud">
                    {listaHabilidades.map((habilidad, idx) => (
                      <span key={`h-${idx}`} className="zaas-tag zaas-tag--category">
                        {habilidad}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {/* Stack Tecnológico */}
              {perfil.stack_tecnologico && (
                <section className="card zaas-profile-section" aria-label="Stack tecnológico">
                  <h2 className="zaas-section-heading">Stack Tecnológico y Herramientas</h2>
                  <p className="zaas-stack-text">{perfil.stack_tecnologico}</p>
                </section>
              )}

              {/* Enlaces Profesionales */}
              {listaEnlaces.length > 0 && (
                <section className="card zaas-profile-section" aria-label="Enlaces externos">
                  <h2 className="zaas-section-heading">Enlaces y Portafolio Externo</h2>
                  <ul className="zaas-links-list">
                    {listaEnlaces.map((enlace, idx) => {
                      const urlLimpia = enlace.startsWith('http') ? enlace : `https://${enlace}`;
                      return (
                        <li key={`link-${idx}`}>
                          <a
                            href={urlLimpia}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="zaas-external-link"
                          >
                            <svg aria-hidden="true" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
                            </svg>
                            <span>{enlace}</span>
                            <span className="catalogo-sr-only">(se abre en una nueva pestaña)</span>
                          </a>
                        </li>
                      );
                    })}
                  </ul>
                </section>
              )}
            </div>

            {/* Columna Derecha: Portafolio / Ofertas y Calificaciones */}
            <div className="zaas-profile-col-right">
              {/* Para Desarrolladores: Portafolio de SaaS en venta */}
              {esDesarrollador && (
                <section className="card zaas-profile-section" aria-label="Portafolio de SaaS">
                  <div className="zaas-section-header-row">
                    <h2 className="zaas-section-heading">Portafolio SaaS ({proyectos.length})</h2>
                    {es_propio && (
                      <Link to="/proyecto/nuevo" className="btn btn-primary btn-sm">
                        + Publicar SaaS
                      </Link>
                    )}
                  </div>

                  {proyectos.length > 0 ? (
                    <div className="zaas-portfolio-list">
                      {proyectos.map((proy) => (
                        <article key={proy.id} className="zaas-portfolio-item">
                          <div className="portfolio-item-content">
                            <h3 className="portfolio-item-title">
                              <Link to={`/proyecto/${proy.id}`}>{proy.titulo}</Link>
                            </h3>
                            <p className="portfolio-item-desc">
                              {proy.descripcion?.slice(0, 90)}...
                            </p>
                            <div className="portfolio-item-footer">
                              <strong className="portfolio-item-price">{formatDinero(proy.precio)}</strong>
                              <span className="zaas-escrow-badge">
                                <svg aria-hidden="true" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                                </svg>
                                <span>Escrow</span>
                              </span>
                            </div>
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="catalogo-muted">Aún no hay proyectos SaaS publicados en el catálogo.</p>
                  )}
                </section>
              )}

              {/* Para Clientes: Ofertas de trabajo publicadas */}
              {!esDesarrollador && (
                <section className="card zaas-profile-section" aria-label="Ofertas de empleo publicadas">
                  <div className="zaas-section-header-row">
                    <h2 className="zaas-section-heading">Ofertas Publicadas ({ofertas.length})</h2>
                    {es_propio && (
                      <Link to="/oferta/nueva" className="btn btn-primary btn-sm">
                        + Nueva Oferta
                      </Link>
                    )}
                  </div>

                  {ofertas.length > 0 ? (
                    <div className="zaas-portfolio-list">
                      {ofertas.map((of) => (
                        <article key={of.id} className="zaas-portfolio-item">
                          <div className="portfolio-item-content">
                            <h3 className="portfolio-item-title">
                              <Link to={`/oferta/${of.id}`}>{of.titulo}</Link>
                            </h3>
                            <p className="portfolio-item-desc">
                              {of.descripcion_requerimientos?.slice(0, 90)}...
                            </p>
                            <div className="portfolio-item-footer">
                              <strong className="portfolio-item-price">
                                {of.presupuesto ? formatDinero(of.presupuesto) : 'Por convenir'}
                              </strong>
                              <BadgeEstado estado={of.estado} />
                            </div>
                          </div>
                        </article>
                      ))}
                    </div>
                  ) : (
                    <p className="catalogo-muted">No hay ofertas de trabajo publicadas.</p>
                  )}
                </section>
              )}

              {/* Calificaciones y Reseñas de Clientes / Desarrolladores */}
              <section className="card zaas-profile-section" aria-label="Calificaciones y reputación">
                <h2 className="zaas-section-heading">
                  Calificaciones y Reputación ({calificaciones.length})
                </h2>

                {calificaciones.length > 0 ? (
                  <div className="zaas-reviews-list">
                    {calificaciones.map((rev) => (
                      <article key={rev.id} className="zaas-review-item">
                        <div className="zaas-review-header">
                          <div className="zaas-review-stars" aria-label={`Puntaje: ${rev.puntaje} de 5 estrellas`}>
                            {'★'.repeat(rev.puntaje)}{'☆'.repeat(5 - rev.puntaje)}
                          </div>
                          <span className="zaas-review-date">{formatFecha(rev.fecha_hora)}</span>
                        </div>
                        {rev.comentarios && (
                          <p className="zaas-review-comment">"{rev.comentarios}"</p>
                        )}
                        {rev.evaluador && (
                          <span className="zaas-review-author">
                            Por {rev.evaluador.nombres} {rev.evaluador.apellido_paterno}
                          </span>
                        )}
                      </article>
                    ))}
                  </div>
                ) : (
                  <p className="catalogo-muted">
                    Aún no cuenta con valoraciones en contratos finalizados.
                  </p>
                )}
              </section>

              {/* Historial de Contratos con Garantía Escrow */}
              {contratos.length > 0 && (
                <section className="card zaas-profile-section" aria-label="Historial de contratos">
                  <h2 className="zaas-section-heading">Historial de Contratos Escrow ({contratos.length})</h2>
                  <div className="zaas-contracts-summary-list">
                    {contratos.slice(0, 5).map((c) => (
                      <div key={c.id} className="zaas-contract-row">
                        <div className="contract-row-info">
                          <span className="contract-row-title">{c.titulo}</span>
                          <span className="contract-row-date">{formatFecha(c.fecha_creacion)}</span>
                        </div>
                        <div className="contract-row-status">
                          <strong className="contract-row-price">{formatDinero(c.costo_acordado)}</strong>
                          <BadgeEstado estado={c.estado} />
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Panel 2: Configuración / Editar Perfil */}
      {pestañaActiva === 'configuracion' && es_propio && (
        <div
          id="panel-configuracion"
          role="tabpanel"
          aria-labelledby="tab-configuracion"
          className="zaas-tab-panel"
        >
          <FormularioEditarPerfil
            usuario={usuario}
            perfil={perfil}
            onGuardadoExitoso={(perfilActualizado) => {
              recargar();
              mostrarToast('¡Perfil actualizado exitosamente con la garantía Zaas!');
              setPestañaActiva('publico');
            }}
          />
        </div>
      )}
    </div>
  );
}

/**
 * Formulario controlado para la edición de perfil con renderizado condicional por rol
 * (Cliente vs Desarrollador), sugerencias interactivas de autocompletado,
 * validaciones y prevención de errores (WCAG y Heurísticas de Nielsen #5 & #9).
 */
function FormularioEditarPerfil({ usuario, perfil, onGuardadoExitoso }) {
  const esDesarrollador = usuario.tipo_usuario === 'desarrollador';

  const [datos, setDatos] = useState({
    nombres: usuario.nombres || '',
    apellido_paterno: usuario.apellido_paterno || '',
    apellido_materno: usuario.apellido_materno || '',
    empresa: perfil.empresa || '',
    descripcion: perfil.descripcion || '',
    habilidades: perfil.habilidades || '',
    stack_tecnologico: perfil.stack_tecnologico || '',
    enlaces: perfil.enlaces || '',
  });

  const [errores, setErrores] = useState({});
  const [errorGeneral, setErrorGeneral] = useState('');
  const [guardando, setGuardando] = useState(false);

  // Sugerencias de autocompletado para desarrolladores
  const sugerenciasHabilidades = [
    'React', 'Python', 'FastAPI', 'Node.js', 'Next.js', 'TypeScript',
    'PostgreSQL', 'Docker', 'AWS', 'Tailwind CSS', 'GraphQL', 'Flask', 'Redis'
  ];

  function agregarSugerenciaHabilidad(sugerencia) {
    const actuales = datos.habilidades
      ? datos.habilidades.split(',').map((s) => s.trim()).filter(Boolean)
      : [];

    if (!actuales.includes(sugerencia)) {
      const nuevo = [...actuales, sugerencia].join(', ');
      setDatos((prev) => ({ ...prev, habilidades: nuevo }));
    }
  }

  function agregarSugerenciaStack(sugerencia) {
    const actual = datos.stack_tecnologico.trim();
    if (!actual.includes(sugerencia)) {
      const nuevo = actual ? `${actual}, ${sugerencia}` : sugerencia;
      setDatos((prev) => ({ ...prev, stack_tecnologico: nuevo }));
    }
  }

  function handleChange(e) {
    const { name, value } = e.target;
    setDatos((prev) => ({ ...prev, [name]: value }));
    // Limpieza de error en tiempo real
    if (errores[name]) {
      setErrores((prev) => ({ ...prev, [name]: '' }));
    }
  }

  function validar() {
    const nuevos = {};
    if (!datos.nombres.trim()) {
      nuevos.nombres = 'El nombre es obligatorio.';
    } else if (datos.nombres.trim().length > 100) {
      nuevos.nombres = 'El nombre no puede superar 100 caracteres.';
    }

    if (!datos.apellido_paterno.trim()) {
      nuevos.apellido_paterno = 'El apellido paterno es obligatorio.';
    } else if (datos.apellido_paterno.trim().length > 100) {
      nuevos.apellido_paterno = 'El apellido paterno no puede superar 100 caracteres.';
    }

    if (datos.empresa.trim().length > 150) {
      nuevos.empresa = 'El nombre de empresa no puede superar 150 caracteres.';
    }

    setErrores(nuevos);
    return Object.keys(nuevos).length === 0;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setErrorGeneral('');

    if (!validar()) {
      return;
    }

    setGuardando(true);
    try {
      // Si el usuario es cliente, nos aseguramos de no enviar datos técnicos
      const datosAEnviar = esDesarrollador
        ? datos
        : {
            ...datos,
            habilidades: '',
            stack_tecnologico: '',
            enlaces: '',
          };

      const resp = await catalogoApi.actualizarPerfil(datosAEnviar);
      onGuardadoExitoso?.(resp.perfil_data);
    } catch (err) {
      setErrores(err.errores || {});
      setErrorGeneral(err.message || 'Error al actualizar el perfil.');
    } finally {
      setGuardando(false);
    }
  }

  return (
    <div className="card zaas-profile-edit-card">
      <div className="profile-edit-header">
        <div className="profile-edit-badge-row">
          <h2 className="zaas-section-heading">Configuración de Perfil</h2>
          <span className={`navbar-role-badge navbar-role-badge--${usuario.tipo_usuario}`}>
            Cuenta {esDesarrollador ? 'Desarrollador' : 'Cliente'}
          </span>
        </div>
        <p className="catalogo-muted">
          {esDesarrollador
            ? 'Personaliza tu perfil profesional, habilidades técnicas y stack para destacar ante clientes que buscan adquirir SaaS o contratar servicios con garantía Escrow.'
            : 'Actualiza tus datos personales y los de tu empresa para tus contratos de adquisición de SaaS y encargos de desarrollo con protección Escrow.'}
        </p>
      </div>

      {errorGeneral && (
        <div className="alert alert-danger" role="alert">
          {errorGeneral}
        </div>
      )}

      <form onSubmit={handleSubmit} noValidate aria-label="Formulario de edición de perfil">
        {/* Sección: Datos Personales (Común para ambos roles) */}
        <fieldset className="zaas-form-fieldset">
          <legend className="zaas-form-legend">Datos Personales</legend>

          <div className="zaas-form-grid-3">
            <div className="form-group">
              <label htmlFor="perfil-nombres">
                Nombres <span className="zaas-required-asterisk">*</span>
              </label>
              <input
                id="perfil-nombres"
                name="nombres"
                type="text"
                value={datos.nombres}
                onChange={handleChange}
                maxLength={100}
                required
                className={errores.nombres ? 'input-error' : ''}
                aria-invalid={Boolean(errores.nombres)}
                aria-describedby={errores.nombres ? 'error-nombres' : undefined}
              />
              {errores.nombres && (
                <small className="field-error" id="error-nombres" role="alert">
                  {errores.nombres}
                </small>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="perfil-apellido-paterno">
                Apellido Paterno <span className="zaas-required-asterisk">*</span>
              </label>
              <input
                id="perfil-apellido-paterno"
                name="apellido_paterno"
                type="text"
                value={datos.apellido_paterno}
                onChange={handleChange}
                maxLength={100}
                required
                className={errores.apellido_paterno ? 'input-error' : ''}
                aria-invalid={Boolean(errores.apellido_paterno)}
                aria-describedby={errores.apellido_paterno ? 'error-apellido-paterno' : undefined}
              />
              {errores.apellido_paterno && (
                <small className="field-error" id="error-apellido-paterno" role="alert">
                  {errores.apellido_paterno}
                </small>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="perfil-apellido-materno">Apellido Materno</label>
              <input
                id="perfil-apellido-materno"
                name="apellido_materno"
                type="text"
                value={datos.apellido_materno}
                onChange={handleChange}
                maxLength={100}
              />
            </div>
          </div>

          <div className="zaas-form-grid-2">
            <div className="form-group">
              <label htmlFor="perfil-email">
                Correo Electrónico (No modificable)
              </label>
              <input
                id="perfil-email"
                type="email"
                value={usuario.email || ''}
                disabled
                className="input-disabled"
                title="El correo electrónico está vinculado a tu cuenta de autenticación y no es modificable"
              />
              <small className="form-hint">
                El correo electrónico no puede ser alterado por motivos de seguridad en los contratos Escrow.
              </small>
            </div>

            <div className="form-group">
              <label htmlFor="perfil-tipo-cuenta">Tipo de Cuenta</label>
              <input
                id="perfil-tipo-cuenta"
                type="text"
                value={esDesarrollador ? 'Desarrollador' : 'Cliente'}
                disabled
                className="input-disabled"
              />
            </div>
          </div>
        </fieldset>

        {/* Sección de Datos de Empresa / Biografía */}
        <fieldset className="zaas-form-fieldset">
          <legend className="zaas-form-legend">
            {esDesarrollador ? 'Perfil Profesional y Biografía' : 'Datos de Empresa y Contacto'}
          </legend>

          <div className="form-group">
            <label htmlFor="perfil-empresa">
              {esDesarrollador ? 'Empresa / Agencia o Independiente' : 'Empresa / Startup / Razón Social'}
            </label>
            <input
              id="perfil-empresa"
              name="empresa"
              type="text"
              value={datos.empresa}
              onChange={handleChange}
              placeholder={esDesarrollador ? 'Ej. DevStudio, Independiente, Freelancer' : 'Ej. Acme Corp, Growth Labs'}
              maxLength={150}
              className={errores.empresa ? 'input-error' : ''}
            />
            {errores.empresa && (
              <small className="field-error" role="alert">{errores.empresa}</small>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="perfil-descripcion">
              {esDesarrollador ? 'Biografía y Trayectoria' : 'Acerca de tu Empresa / Necesidades'}
            </label>
            <textarea
              id="perfil-descripcion"
              name="descripcion"
              value={datos.descripcion}
              onChange={handleChange}
              placeholder={
                esDesarrollador
                  ? 'Describe tu experiencia construyendo micro-SaaS, arquitecturas con las que trabajas y tipos de proyectos en los que te especializas...'
                  : 'Describe el giro de tu empresa y el tipo de plataformas SaaS o talento tecnológico que buscas contratar...'
              }
              rows={4}
            />
            <small className="form-hint">
              Una descripción detallada aumenta la confianza de contrapartes en contratos con custodia Escrow.
            </small>
          </div>
        </fieldset>

        {/* RENDERIZADO CONDICIONAL: Solo para DESARROLLADOR */}
        {esDesarrollador && (
          <fieldset className="zaas-form-fieldset">
            <legend className="zaas-form-legend">
              Habilidades Técnicas y Stack (Solo Desarrolladores)
            </legend>

            {/* Habilidades con Autocompletado / Sugerencias interactivas */}
            <div className="form-group">
              <label htmlFor="perfil-habilidades">
                Habilidades Técnicas (separadas por comas)
              </label>
              <input
                id="perfil-habilidades"
                name="habilidades"
                type="text"
                value={datos.habilidades}
                onChange={handleChange}
                placeholder="Ej. React, Python, FastAPI, Docker, UI/UX, Escrow"
              />
              <small className="form-hint">
                Ingresa tus habilidades separadas por comas. Se mostrarán como etiquetas públicas.
              </small>

              {/* Chips de sugerencias interactivas */}
              <div className="zaas-suggestions-box">
                <span className="zaas-suggestions-label">Sugerencias rápidas:</span>
                <div className="zaas-suggestions-chips">
                  {sugerenciasHabilidades.map((sug) => (
                    <button
                      key={sug}
                      type="button"
                      className="zaas-chip-btn"
                      onClick={() => agregarSugerenciaHabilidad(sug)}
                      aria-label={`Añadir habilidad ${sug}`}
                    >
                      + {sug}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Stack Tecnológico */}
            <div className="form-group">
              <label htmlFor="perfil-stack">Stack Tecnológico Detallado</label>
              <textarea
                id="perfil-stack"
                name="stack_tecnologico"
                value={datos.stack_tecnologico}
                onChange={handleChange}
                placeholder="Ej. Frontend en React/Next.js, Backend en Python Flask/FastAPI, PostgreSQL, AWS, Tailwind CSS..."
                rows={3}
              />
              <div className="zaas-suggestions-box">
                <span className="zaas-suggestions-label">Sugerencias de tecnologías:</span>
                <div className="zaas-suggestions-chips">
                  {['React', 'Next.js', 'FastAPI', 'PostgreSQL', 'Docker', 'AWS'].map((sug) => (
                    <button
                      key={`st-${sug}`}
                      type="button"
                      className="zaas-chip-btn"
                      onClick={() => agregarSugerenciaStack(sug)}
                      aria-label={`Añadir tecnología ${sug} al stack`}
                    >
                      + {sug}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Enlaces Externos */}
            <div className="form-group">
              <label htmlFor="perfil-enlaces">
                Enlaces Externos (GitHub, LinkedIn, Portafolio)
              </label>
              <input
                id="perfil-enlaces"
                name="enlaces"
                type="text"
                value={datos.enlaces}
                onChange={handleChange}
                placeholder="https://github.com/tu-usuario, https://linkedin.com/in/tu-perfil, https://tuportafolio.dev"
              />
              <small className="form-hint">
                Ingresa URLs separadas por comas. Los clientes podrán ver tu trabajo verificado.
              </small>
            </div>
          </fieldset>
        )}

        {/* Botones de acción del formulario */}
        <div className="zaas-form-actions">
          <button
            type="submit"
            className="btn btn-primary btn-save-profile"
            disabled={guardando}
            aria-busy={guardando}
          >
            {guardando ? (
              <>
                <span className="zaas-button-spinner" aria-hidden="true" />
                <span>Guardando cambios...</span>
              </>
            ) : (
              <span>Guardar Cambios</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
