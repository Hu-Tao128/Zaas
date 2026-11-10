import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { contratosApi } from '../../services/contratosApi';
import { ShieldCheckIcon } from '../../components/icons';
import { formatDinero } from '../catalogo/catalogoUtils';
import { CargandoContratos } from './ContratoUI';

const VALORES_INICIALES = {
  id_desarrollador: '',
  id_producto: '',
  id_encargo: '',
  costo_acordado: '',
  plantilla_id: '',
  notas: '',
};

// Relaciona cada campo del modelo con el id del control HTML (para enfocar el primer error).
const IDS_CAMPOS = {
  id_desarrollador: 'contrato-desarrollador',
  id_producto: 'contrato-producto',
  id_encargo: 'contrato-oferta',
  costo_acordado: 'contrato-costo',
  plantilla_id: 'contrato-plantilla',
  notas: 'contrato-notas',
};

function validar(valores, productos) {
  const errores = {};

  if (!valores.id_desarrollador) {
    errores.id_desarrollador = 'Selecciona un desarrollador.';
  }

  if (!valores.costo_acordado) {
    errores.costo_acordado = 'Indica el costo acordado.';
  } else if (!Number.isFinite(Number(valores.costo_acordado)) || Number(valores.costo_acordado) <= 0) {
    errores.costo_acordado = 'El costo debe ser mayor a cero.';
  }

  if (!valores.plantilla_id) {
    errores.plantilla_id = 'Selecciona una plantilla de contrato.';
  }

  if (valores.notas.length > 2000) {
    errores.notas = 'Las notas no pueden superar los 2000 caracteres.';
  }

  // Regla del MR: exactamente uno de producto / encargo.
  if (!valores.id_producto && !valores.id_encargo) {
    errores.id_producto = 'Selecciona un producto o una oferta.';
    errores.id_encargo = 'Selecciona un producto o una oferta.';
  } else if (valores.id_producto && valores.id_encargo) {
    errores.id_producto = 'Selecciona solo un producto o una oferta, no ambos.';
    errores.id_encargo = 'Selecciona solo un producto o una oferta, no ambos.';
  }

  if (valores.id_producto && valores.id_desarrollador) {
    const producto = productos.find((p) => p.id === Number(valores.id_producto));
    if (producto && producto.id_usuario !== Number(valores.id_desarrollador)) {
      errores.id_producto = 'El producto debe pertenecer al desarrollador seleccionado.';
    }
  }

  return errores;
}

export default function ContratoForm() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const [opciones, setOpciones] = useState(null);
  const [cargandoOpciones, setCargandoOpciones] = useState(true);
  const [errorOpciones, setErrorOpciones] = useState(null);

  const [valores, setValores] = useState(VALORES_INICIALES);
  const [touched, setTouched] = useState({});
  const [intentoEnvio, setIntentoEnvio] = useState(false);
  const [erroresServidor, setErroresServidor] = useState({});
  const [errorGeneral, setErrorGeneral] = useState('');
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    let vigente = true;
    setCargandoOpciones(true);
    contratosApi.opciones()
      .then((data) => {
        if (!vigente) return;
        setOpciones(data);
        const plantillaBase = data.plantillas.find((p) => p.es_base) || data.plantillas[0];
        setValores((actual) => ({
          ...actual,
          id_desarrollador: searchParams.get('id_desarrollador') || '',
          id_producto: searchParams.get('id_producto') || '',
          id_encargo: searchParams.get('id_encargo') || '',
          costo_acordado: searchParams.get('costo_acordado') || '',
          plantilla_id: actual.plantilla_id || (plantillaBase ? String(plantillaBase.id) : ''),
        }));
        setCargandoOpciones(false);
      })
      .catch((error) => {
        if (!vigente) return;
        setErrorOpciones(error);
        setCargandoOpciones(false);
      });
    return () => { vigente = false; };
    // Solo al montar: los parámetros de la URL son el prellenado inicial.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const productos = opciones?.productos || [];

  const productosDisponibles = useMemo(() => {
    if (!valores.id_desarrollador) return productos;
    return productos.filter((p) => p.id_usuario === Number(valores.id_desarrollador));
  }, [productos, valores.id_desarrollador]);

  const errores = useMemo(() => validar(valores, productos), [valores, productos]);

  const mostrarError = (campo) =>
    (intentoEnvio || touched[campo]) ? (errores[campo] || erroresServidor[campo]) : erroresServidor[campo];

  function actualizar(campo, valor) {
    setValores((actual) => {
      const siguiente = { ...actual, [campo]: valor };
      if (campo === 'id_desarrollador') {
        const productoElegido = productos.find((p) => p.id === Number(actual.id_producto));
        if (productoElegido && productoElegido.id_usuario !== Number(valor)) {
          siguiente.id_producto = '';
        }
      }
      return siguiente;
    });
    setErroresServidor((actual) => ({ ...actual, [campo]: undefined }));
  }

  function marcarTocado(campo) {
    setTouched((actual) => ({ ...actual, [campo]: true }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setIntentoEnvio(true);
    setErrorGeneral('');
    setErroresServidor({});

    if (Object.keys(errores).length > 0) {
      const primerCampo = Object.keys(errores)[0];
      document.getElementById(IDS_CAMPOS[primerCampo])?.focus();
      return;
    }

    setEnviando(true);
    try {
      const data = await contratosApi.crear({
        id_desarrollador: Number(valores.id_desarrollador),
        id_producto: valores.id_producto ? Number(valores.id_producto) : null,
        id_encargo: valores.id_encargo ? Number(valores.id_encargo) : null,
        costo_acordado: Number(valores.costo_acordado),
        plantilla_id: Number(valores.plantilla_id),
        notas: valores.notas.trim(),
      });
      navigate(`/contratos/${data.contrato.id}`);
    } catch (error) {
      setErrorGeneral(error.message || 'No se pudo crear el contrato.');
      if (error.errores) setErroresServidor(error.errores);
    } finally {
      setEnviando(false);
    }
  }

  const desarrolladorElegido = opciones?.desarrolladores.find(
    (d) => d.id === Number(valores.id_desarrollador),
  );

  if (cargandoOpciones) return <CargandoContratos mensaje="Cargando opciones de contrato..." />;

  if (errorOpciones) {
    return (
      <div className="card contrato-error" role="alert">
        <div className="alert alert-danger">
          {errorOpciones.message || 'No se pudieron cargar las opciones del contrato.'}
        </div>
        <Link to="/contratos" className="btn btn-secondary">Volver a contratos</Link>
      </div>
    );
  }

  return (
    <div className="contratos-page">
      <nav aria-label="Migas de pan" className="proyecto-breadcrumbs">
        <Link to="/contratos">Contratos</Link>
        <span aria-hidden="true">/</span>
        <span className="current" aria-current="page">Nuevo contrato</span>
      </nav>

      <header className="contratos-header">
        <div>
          <h1 className="catalogo-page-title">Nueva propuesta de contrato</h1>
          <p className="catalogo-page-subtitle">
            Define a las partes, el monto y la plantilla legal. El contrato se creará como
            borrador y quedará protegido por Escrow al firmarse.
          </p>
        </div>
      </header>

      <div className="contrato-form-layout">
        <form className="card contrato-form-card" onSubmit={handleSubmit} noValidate>
          <h2 className="contrato-form-title">Datos del acuerdo</h2>

          {errorGeneral && (
            <div className="alert alert-danger" role="alert">{errorGeneral}</div>
          )}

          {opciones.desarrolladores.length === 0 && (
            <div className="alert alert-warning" role="status">
              No hay desarrolladores registrados todavía. Pide a un desarrollador que cree su
              cuenta antes de generar un contrato.
            </div>
          )}

          <div className="form-group">
            <label htmlFor="contrato-desarrollador">
              Desarrollador <span className="zaas-required-asterisk">*</span>
            </label>
            <select
              id="contrato-desarrollador"
              value={valores.id_desarrollador}
              onChange={(e) => actualizar('id_desarrollador', e.target.value)}
              onBlur={() => marcarTocado('id_desarrollador')}
              aria-invalid={Boolean(mostrarError('id_desarrollador'))}
              aria-describedby={`contrato-desarrollador-hint${mostrarError('id_desarrollador') ? ' contrato-desarrollador-error' : ''}`}
              required
            >
              <option value="">Selecciona un desarrollador</option>
              {opciones.desarrolladores.map((dev) => (
                <option key={dev.id} value={dev.id}>
                  {dev.nombre_completo}
                </option>
              ))}
            </select>
            <small className="form-hint" id="contrato-desarrollador-hint">
              La contraparte que ejecutará el desarrollo.
            </small>
            {mostrarError('id_desarrollador') && (
              <small className="field-error" id="contrato-desarrollador-error" role="alert">
                {mostrarError('id_desarrollador')}
              </small>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="contrato-producto">Producto relacionado (opcional)</label>
            <select
              id="contrato-producto"
              value={valores.id_producto}
              onChange={(e) => actualizar('id_producto', e.target.value)}
              onBlur={() => marcarTocado('id_producto')}
              aria-invalid={Boolean(mostrarError('id_producto'))}
              aria-describedby={`contrato-producto-hint${mostrarError('id_producto') ? ' contrato-producto-error' : ''}`}
            >
              <option value="">Sin producto relacionado</option>
              {productosDisponibles.map((producto) => (
                <option key={producto.id} value={producto.id}>
                  {producto.titulo} — {formatDinero(producto.precio)}
                </option>
              ))}
            </select>
            <small className="form-hint" id="contrato-producto-hint">
              Vincula el contrato a un SaaS del desarrollador seleccionado.
            </small>
            {mostrarError('id_producto') && (
              <small className="field-error" id="contrato-producto-error" role="alert">
                {mostrarError('id_producto')}
              </small>
            )}
          </div>

          <div className="form-group">
            <label htmlFor="contrato-oferta">Oferta relacionada (opcional)</label>
            <select
              id="contrato-oferta"
              value={valores.id_encargo}
              onChange={(e) => actualizar('id_encargo', e.target.value)}
              onBlur={() => marcarTocado('id_encargo')}
              aria-invalid={Boolean(mostrarError('id_encargo'))}
              aria-describedby={`contrato-oferta-hint${mostrarError('id_encargo') ? ' contrato-oferta-error' : ''}`}
            >
              <option value="">Sin oferta relacionada</option>
              {opciones.ofertas.map((oferta) => (
                <option key={oferta.id} value={oferta.id}>
                  {oferta.titulo}
                  {oferta.presupuesto ? ` — ${formatDinero(oferta.presupuesto)}` : ''}
                </option>
              ))}
            </select>
            <small className="form-hint" id="contrato-oferta-hint">
              Vincula el contrato a una de tus ofertas publicadas.
            </small>
            {mostrarError('id_encargo') && (
              <small className="field-error" id="contrato-oferta-error" role="alert">
                {mostrarError('id_encargo')}
              </small>
            )}
          </div>

          <div className="contrato-form-grid">
            <div className="form-group">
              <label htmlFor="contrato-costo">
                Costo acordado (MXN) <span className="zaas-required-asterisk">*</span>
              </label>
              <input
                id="contrato-costo"
                type="number"
                min="0.01"
                step="0.01"
                inputMode="decimal"
                placeholder="15000.00"
                value={valores.costo_acordado}
                onChange={(e) => actualizar('costo_acordado', e.target.value)}
                onBlur={() => marcarTocado('costo_acordado')}
                aria-invalid={Boolean(mostrarError('costo_acordado'))}
                aria-describedby={`contrato-costo-hint${mostrarError('costo_acordado') ? ' contrato-costo-error' : ''}`}
                required
              />
              <small className="form-hint" id="contrato-costo-hint">
                Monto que se retendrá en Escrow hasta validar los entregables.
              </small>
              {mostrarError('costo_acordado') && (
                <small className="field-error" id="contrato-costo-error" role="alert">
                  {mostrarError('costo_acordado')}
                </small>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="contrato-plantilla">
                Plantilla legal <span className="zaas-required-asterisk">*</span>
              </label>
              <select
                id="contrato-plantilla"
                value={valores.plantilla_id}
                onChange={(e) => actualizar('plantilla_id', e.target.value)}
                onBlur={() => marcarTocado('plantilla_id')}
                aria-invalid={Boolean(mostrarError('plantilla_id'))}
                aria-describedby={`contrato-plantilla-hint${mostrarError('plantilla_id') ? ' contrato-plantilla-error' : ''}`}
                required
              >
                <option value="">Selecciona una plantilla</option>
                {opciones.plantillas.map((plantilla) => (
                  <option key={plantilla.id} value={plantilla.id}>
                    {plantilla.nombre}
                  </option>
                ))}
              </select>
              <small className="form-hint" id="contrato-plantilla-hint">
                Se guarda una copia inmutable al crear el contrato.
              </small>
              {mostrarError('plantilla_id') && (
                <small className="field-error" id="contrato-plantilla-error" role="alert">
                  {mostrarError('plantilla_id')}
                </small>
              )}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="contrato-notas">Notas adicionales (opcional)</label>
            <textarea
              id="contrato-notas"
              rows="4"
              maxLength={2000}
              placeholder="Alcance, fechas, condiciones especiales..."
              value={valores.notas}
              onChange={(e) => actualizar('notas', e.target.value)}
              onBlur={() => marcarTocado('notas')}
              aria-invalid={Boolean(mostrarError('notas'))}
              aria-describedby={`contrato-notas-hint${mostrarError('notas') ? ' contrato-notas-error' : ''}`}
            />
            <small className="form-hint" id="contrato-notas-hint">
              {valores.notas.length}/2000 caracteres.
            </small>
            {mostrarError('notas') && (
              <small className="field-error" id="contrato-notas-error" role="alert">
                {mostrarError('notas')}
              </small>
            )}
          </div>

          <div className="contrato-form-actions">
            <Link to="/contratos" className="btn btn-secondary">Cancelar</Link>
            <button
              type="submit"
              className="btn btn-primary contrato-submit"
              disabled={enviando || opciones.desarrolladores.length === 0}
              aria-busy={enviando}
            >
              {enviando ? (
                <>
                  <span className="zaas-button-spinner" aria-hidden="true" />
                  <span>Creando contrato...</span>
                </>
              ) : (
                <span>Crear contrato</span>
              )}
            </button>
          </div>
        </form>

        <aside className="contrato-form-aside" aria-label="Resumen de la propuesta">
          <div className="card contrato-summary-card">
            <span className="contrato-summary-label">Cliente</span>
            <strong className="contrato-summary-name">
              {opciones.usuario?.nombre_completo}
            </strong>
            <span className="contrato-summary-email">{opciones.usuario?.email || ''}</span>

            <hr className="proyecto-sidebar-divider" />

            <span className="contrato-summary-label">Desarrollador</span>
            <strong className="contrato-summary-name">
              {desarrolladorElegido ? desarrolladorElegido.nombre_completo : 'Por seleccionar'}
            </strong>

            <hr className="proyecto-sidebar-divider" />

            <span className="contrato-summary-label">Monto a custodiar</span>
            <strong className="contrato-summary-amount">
              {valores.costo_acordado && Number(valores.costo_acordado) > 0
                ? formatDinero(valores.costo_acordado)
                : '$0.00'}
            </strong>

            <div className="escrow-guarantee-badge">
              <ShieldCheckIcon size={15} />
              <span>Protección Escrow</span>
            </div>
            <p className="escrow-guarantee-hint">
              Los fondos se retienen hasta que el cliente valide los entregables del contrato.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}
