import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { contratosApi } from '../../services/contratosApi';
import { ShieldCheckIcon } from '../../components/icons';
import { formatDinero } from '../catalogo/catalogoUtils';
import { CargandoContratos } from './ContratoUI';

const VALORES_INICIALES = {
  costo_acordado: '',
  plantilla_id: '',
  notas: '',
};

// Relaciona cada campo del modelo con el id del control HTML (para enfocar el primer error).
const IDS_CAMPOS = {
  costo_acordado: 'contrato-costo',
  plantilla_id: 'contrato-plantilla',
  notas: 'contrato-notas',
};

function costoInicial(valor) {
  if (valor === null || valor === undefined || valor === '') return '';
  const numero = Number(valor);
  if (!Number.isFinite(numero) || numero <= 0) return '';
  return String(Math.round(numero * 100) / 100);
}

function validar(valores) {
  const errores = {};

  if (!valores.costo_acordado) {
    errores.costo_acordado = 'Indica el costo acordado.';
  } else if (!/^\d+(\.\d{1,2})?$/.test(String(valores.costo_acordado).trim())) {
    errores.costo_acordado = 'El costo debe ser un número válido (hasta 2 decimales).';
  } else if (!Number.isFinite(Number(valores.costo_acordado)) || Number(valores.costo_acordado) <= 0) {
    errores.costo_acordado = 'El costo debe ser mayor a cero.';
  }

  if (!valores.plantilla_id) {
    errores.plantilla_id = 'Selecciona un tipo de contrato.';
  }

  if (valores.notas.length > 2000) {
    errores.notas = 'Las notas no pueden superar los 2000 caracteres.';
  }

  return errores;
}

export default function ContratoForm() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const idProducto = searchParams.get('id_producto');
  const idEncargo = searchParams.get('id_encargo');
  const costoParametro = searchParams.get('costo_acordado') || '';

  const [opciones, setOpciones] = useState(null);
  const [cargandoOpciones, setCargandoOpciones] = useState(true);
  const [errorOpciones, setErrorOpciones] = useState(null);

  const [valores, setValores] = useState(VALORES_INICIALES);
  const [touched, setTouched] = useState({});
  const [intentoEnvio, setIntentoEnvio] = useState(false);
  const [erroresServidor, setErroresServidor] = useState({});
  const [errorGeneral, setErrorGeneral] = useState('');
  const [enviando, setEnviando] = useState(false);

  const contextoFaltante = Boolean(idProducto) === Boolean(idEncargo);

  useEffect(() => {
    if (contextoFaltante) {
      const mensaje = idProducto && idEncargo
        ? 'Selecciona un solo producto u oferta para crear el contrato.'
        : 'Para crear un contrato, elige un proyecto o una oferta desde el catálogo.';
      navigate('/contratos', { replace: true, state: { mensaje } });
      return undefined;
    }

    let vigente = true;
    setCargandoOpciones(true);
    setErrorOpciones(null);
    contratosApi.opciones({ id_producto: idProducto, id_encargo: idEncargo })
      .then((data) => {
        if (!vigente) return;
        if (!data.contexto) {
          setErrorOpciones(new Error(data.mensaje || 'No se pudo preparar el contrato.'));
          setCargandoOpciones(false);
          return;
        }
        setOpciones(data);
        const tipoSugerido = data.contexto.producto ? 'licencia_software' : 'desarrollo';
        const plantillaBase = data.plantillas.find((p) => p.tipo === tipoSugerido)
          || data.plantillas.find((p) => p.es_base)
          || data.plantillas[0];
        setValores((actual) => ({
          ...actual,
          costo_acordado: actual.costo_acordado
            || costoInicial(costoParametro)
            || costoInicial(data.contexto.costo_sugerido),
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
    // Solo al montar: los parámetros de la URL definen el contrato a crear.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const contexto = opciones?.contexto;
  const producto = contexto?.producto || null;
  const oferta = contexto?.oferta || null;
  const desarrollador = contexto?.desarrollador || null;
  const objeto = producto || oferta;
  const tipoObjeto = producto ? 'Proyecto' : 'Oferta';
  const montoReferencia = producto
    ? producto.precio
    : (oferta?.costo_postulado ?? oferta?.presupuesto);
  const plantillaSeleccionada = opciones?.plantillas.find(
    (plantilla) => plantilla.id === Number(valores.plantilla_id),
  );

  const errores = useMemo(() => validar(valores), [valores]);

  const mostrarError = (campo) =>
    (intentoEnvio || touched[campo]) ? (errores[campo] || erroresServidor[campo]) : erroresServidor[campo];

  function actualizar(campo, valor) {
    setValores((actual) => ({ ...actual, [campo]: valor }));
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
        id_producto: producto ? producto.id : null,
        id_encargo: oferta ? oferta.id : null,
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

  if (contextoFaltante) return <CargandoContratos mensaje="Volviendo a contratos..." />;

  if (cargandoOpciones) return <CargandoContratos mensaje="Preparando el contrato..." />;

  if (errorOpciones) {
    return (
      <div className="card contrato-error" role="alert">
        <div className="alert alert-danger">
          {errorOpciones.message || 'No se pudo preparar el contrato.'}
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
            Revisa las partes y el objeto del acuerdo. El desarrollador y el objeto se
            toman directamente del catálogo para evitar contratos genéricos.
          </p>
        </div>
      </header>

      <div className="contrato-form-layout">
        <form className="card contrato-form-card" onSubmit={handleSubmit} noValidate>
          <h2 className="contrato-form-title">Datos del acuerdo</h2>

          {errorGeneral && (
            <div className="alert alert-danger" role="alert">{errorGeneral}</div>
          )}

          <div className="contrato-contexto" aria-label="Partes y objeto del contrato">
            <div className="contrato-contexto-item">
              <span className="contrato-summary-label">Cliente</span>
              <strong className="contrato-contexto-value">
                {opciones.usuario?.nombre_completo}
              </strong>
              <span className="contrato-contexto-note">{opciones.usuario?.email || ''}</span>
            </div>

            <div className="contrato-contexto-item">
              <span className="contrato-summary-label">Desarrollador</span>
              <strong className="contrato-contexto-value">
                {desarrollador?.nombre_completo || 'No disponible'}
              </strong>
              <span className="contrato-contexto-note">Contraparte del contrato</span>
            </div>

            <div className="contrato-contexto-item contrato-contexto-item--full">
              <span className="contrato-summary-label">{tipoObjeto} contratado</span>
              <strong className="contrato-contexto-value">{objeto?.titulo}</strong>
              <span className="contrato-contexto-note">
                {montoReferencia != null
                  ? `Monto de referencia: ${formatDinero(montoReferencia)}`
                  : 'Sin monto de referencia'}
                {' · '}
                El objeto no se puede cambiar desde este formulario.
              </span>
            </div>
          </div>

          <div className="contrato-form-grid">
            <div className="form-group">
              <label htmlFor="contrato-costo">
                Costo acordado (MXN) <span className="zaas-required-asterisk">*</span>
              </label>
              <input
                id="contrato-costo"
                type="text"
                inputMode="decimal"
                placeholder="15000.00"
                value={valores.costo_acordado}
                onChange={(e) => {
                  const v = e.target.value;
                  if (/^\d*\.?\d{0,2}$/.test(v)) actualizar('costo_acordado', v);
                }}
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
                Tipo de contrato <span className="zaas-required-asterisk">*</span>
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
                <option value="">Selecciona un tipo de contrato</option>
                {opciones.plantillas.map((plantilla) => (
                  <option key={plantilla.id} value={plantilla.id}>
                    {plantilla.etiqueta || plantilla.nombre}
                  </option>
                ))}
              </select>
              <small className="form-hint" id="contrato-plantilla-hint">
                {plantillaSeleccionada
                  ? `${plantillaSeleccionada.descripcion} Plantilla: ${plantillaSeleccionada.nombre}.`
                  : 'La plantilla legal cambia según el tipo de contrato elegido.'}
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
              disabled={enviando}
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
              {desarrollador?.nombre_completo || 'No disponible'}
            </strong>

            <hr className="proyecto-sidebar-divider" />

            <span className="contrato-summary-label">{tipoObjeto}</span>
            <strong className="contrato-summary-name">{objeto?.titulo}</strong>

            <hr className="proyecto-sidebar-divider" />

            <span className="contrato-summary-label">Tipo de contrato</span>
            <strong className="contrato-summary-name">
              {plantillaSeleccionada?.etiqueta || 'Por seleccionar'}
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
