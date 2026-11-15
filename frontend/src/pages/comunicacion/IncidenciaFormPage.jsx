import { useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { comunicacionApi, mensajeErrorIncidencia } from '../../services/comunicacionApi';
import { Cargando, ErrorCard } from '../../components/catalogo/CatalogoUI';

const TIPOS = [
  { value: 'acoso', label: 'Acoso' },
  { value: 'fraude', label: 'Fraude' },
  { value: 'incumplimiento', label: 'Incumplimiento' },
  { value: 'bug', label: 'Bug del sistema' },
  { value: 'otro', label: 'Otro' },
];

const TIPOS_REQUIEREN_CONTRATO = new Set(['fraude', 'incumplimiento']);
const SIN_CONTRATO = '__sin_contrato__';

const FORM_INICIAL = {
  tipo: '',
  id_contrato: '',
  tipo_detalle: '',
  descripcion: '',
};

function etiquetaContrato(item) {
  if (!item) return '';
  if (item.etiqueta) return item.etiqueta;
  const estado = item.estado_etiqueta || item.estado || '';
  return estado ? `${item.objeto || 'Contrato'} — ${estado}` : (item.objeto || 'Contrato');
}

function validarForm(form) {
  const errores = {};
  if (!form.tipo) {
    errores.tipo = 'Selecciona el tipo de incidencia.';
  }
  if (form.tipo && TIPOS_REQUIEREN_CONTRATO.has(form.tipo) && (!form.id_contrato || form.id_contrato === SIN_CONTRATO)) {
    errores.id_contrato = 'Este tipo de incidencia requiere un contrato.';
  }
  if (form.tipo === 'otro' && !form.tipo_detalle.trim()) {
    errores.tipo_detalle = 'Indica qué tipo de incidencia es.';
  }
  if (form.tipo === 'otro' && form.tipo_detalle.trim().length > 100) {
    errores.tipo_detalle = 'El detalle no puede superar 100 caracteres.';
  }
  const descripcion = form.descripcion.trim();
  if (!descripcion) {
    errores.descripcion = 'La descripción es obligatoria.';
  } else if (descripcion.length < 10) {
    errores.descripcion = 'La descripción debe tener al menos 10 caracteres.';
  } else if (descripcion.length > 1000) {
    errores.descripcion = 'La descripción no puede superar 1000 caracteres.';
  }
  return errores;
}

export default function IncidenciaFormPage() {
  const navigate = useNavigate();
  const {
    data: contratosData,
    loading: cargandoContratos,
    error: errorContratos,
  } = useApi(() => comunicacionApi.incidenciasContratos(), []);

  const [form, setForm] = useState(FORM_INICIAL);
  const [touched, setTouched] = useState({});
  const [intentoEnvio, setIntentoEnvio] = useState(false);
  const [erroresServidor, setErroresServidor] = useState({});
  const [errorGeneral, setErrorGeneral] = useState('');
  const [enviando, setEnviando] = useState(false);

  const contratos = useMemo(() => contratosData?.items || [], [contratosData]);
  const errores = useMemo(() => validarForm(form), [form]);

  if (errorContratos) {
    return <ErrorCard error={{ message: mensajeErrorIncidencia(errorContratos) }} volverA="/incidencias" volverTexto="Volver a incidencias" />;
  }

  const requiereContrato = TIPOS_REQUIEREN_CONTRATO.has(form.tipo);
  const sinContratos = !cargandoContratos && contratos.length === 0;
  const selectDeshabilitado = sinContratos || cargandoContratos;

  function actualizar(campo, valor) {
    setForm((actual) => {
      const siguiente = { ...actual, [campo]: valor };
      if (campo === 'tipo') {
        // Al cambiar de tipo se oculta y limpia el detalle de "Otro".
        siguiente.tipo_detalle = '';
      }
      return siguiente;
    });
    setErroresServidor((actual) => ({ ...actual, [campo]: undefined }));
    setErrorGeneral('');
  }

  function marcarTocado(campo) {
    setTouched((actual) => ({ ...actual, [campo]: true }));
  }

  function mostrarError(campo) {
    if (erroresServidor[campo]) return erroresServidor[campo];
    return (intentoEnvio || touched[campo]) ? errores[campo] : undefined;
  }

  async function crearIncidencia(event) {
    event.preventDefault();
    if (enviando) return;
    setIntentoEnvio(true);
    setErrorGeneral('');
    setErroresServidor({});

    if (Object.keys(errores).length > 0) return;

    setEnviando(true);
    try {
      const payload = {
        tipo: form.tipo,
        descripcion: form.descripcion.trim(),
      };
      if (form.tipo === 'otro') payload.tipo_detalle = form.tipo_detalle.trim();
      if (form.id_contrato && form.id_contrato !== SIN_CONTRATO) {
        payload.id_contrato = Number(form.id_contrato);
      }
      await comunicacionApi.crearIncidencia(payload);
      navigate('/incidencias', { state: { mensaje: 'Incidencia reportada.' } });
    } catch (err) {
      setErrorGeneral(mensajeErrorIncidencia(err));
      if (err.errores) setErroresServidor(err.errores);
    } finally {
      setEnviando(false);
    }
  }

  if (cargandoContratos) return <Cargando />;

  return (
    <div className="contratos-page">
      <nav aria-label="Migas de pan" className="proyecto-breadcrumbs">
        <Link to="/incidencias">Incidencias</Link>
        <span aria-hidden="true">/</span>
        <span className="current" aria-current="page">Reportar incidencia</span>
      </nav>

      <header className="contratos-header">
        <div>
          <h1 className="catalogo-page-title">Reportar incidencia</h1>
          <p className="catalogo-page-subtitle">
            Describe el problema para que el equipo de Zaas lo revise.
          </p>
        </div>
      </header>

      <form className="card contrato-form-card" onSubmit={crearIncidencia} noValidate>
        <h2 className="contrato-form-title">Nueva incidencia</h2>

        {errorGeneral && <div className="alert alert-danger" role="alert">{errorGeneral}</div>}

        <div className="form-group">
          <label htmlFor="incidencia-tipo">Tipo <span className="zaas-required-asterisk">*</span></label>
          <select
            id="incidencia-tipo"
            value={form.tipo}
            onChange={(e) => actualizar('tipo', e.target.value)}
            onBlur={() => marcarTocado('tipo')}
            aria-invalid={Boolean(mostrarError('tipo'))}
            aria-describedby="incidencia-tipo-error"
          >
            <option value="" disabled>Selecciona un tipo</option>
            {TIPOS.map((tipo) => (
              <option key={tipo.value} value={tipo.value}>{tipo.label}</option>
            ))}
          </select>
          {mostrarError('tipo') && (
            <small className="field-error" id="incidencia-tipo-error" role="alert">
              {mostrarError('tipo')}
            </small>
          )}
        </div>

        <div className="form-group">
          <label htmlFor="incidencia-contrato">
            Contrato relacionado {requiereContrato
              ? <span className="zaas-required-asterisk">*</span>
              : <span className="form-hint">(opcional)</span>}
          </label>
          <select
            id="incidencia-contrato"
            value={form.id_contrato}
            onChange={(e) => actualizar('id_contrato', e.target.value)}
            onBlur={() => marcarTocado('id_contrato')}
            disabled={selectDeshabilitado}
            aria-invalid={Boolean(mostrarError('id_contrato'))}
            aria-describedby="incidencia-contrato-hint"
          >
            <option value="" disabled>
              {cargandoContratos ? 'Cargando contratos...' : 'Selecciona un contrato'}
            </option>
            {!requiereContrato && (
              <option value={SIN_CONTRATO}>Sin contrato relacionado</option>
            )}
            {contratos.map((contrato) => (
              <option key={contrato.id} value={contrato.id}>
                {etiquetaContrato(contrato)}
              </option>
            ))}
          </select>
          {sinContratos && (
            <small className="form-hint" id="incidencia-contrato-hint">
              Aún no tienes contratos.
            </small>
          )}
          {requiereContrato && !sinContratos && (
            <small className="form-hint" id="incidencia-contrato-hint">
              Este tipo de incidencia requiere un contrato.
            </small>
          )}
          {mostrarError('id_contrato') && (
            <small className="field-error" role="alert">{mostrarError('id_contrato')}</small>
          )}
        </div>

        {form.tipo === 'otro' && (
          <div className="form-group">
            <label htmlFor="incidencia-tipo-detalle">
              ¿Qué tipo de incidencia es? <span className="zaas-required-asterisk">*</span>
            </label>
            <input
              id="incidencia-tipo-detalle"
              type="text"
              maxLength={100}
              value={form.tipo_detalle}
              onChange={(e) => actualizar('tipo_detalle', e.target.value)}
              onBlur={() => marcarTocado('tipo_detalle')}
              aria-invalid={Boolean(mostrarError('tipo_detalle'))}
              aria-describedby="incidencia-tipo-detalle-hint"
            />
            <small className="form-hint" id="incidencia-tipo-detalle-hint">
              {form.tipo_detalle.trim().length}/100 caracteres.
            </small>
            {mostrarError('tipo_detalle') && (
              <small className="field-error" role="alert">{mostrarError('tipo_detalle')}</small>
            )}
          </div>
        )}

        <div className="form-group">
          <label htmlFor="incidencia-descripcion">
            Descripción <span className="zaas-required-asterisk">*</span>
          </label>
          <textarea
            id="incidencia-descripcion"
            rows="4"
            maxLength={1000}
            value={form.descripcion}
            onChange={(e) => actualizar('descripcion', e.target.value)}
            onBlur={() => marcarTocado('descripcion')}
            aria-invalid={Boolean(mostrarError('descripcion'))}
            aria-describedby="incidencia-descripcion-hint"
          />
          <small className="form-hint" id="incidencia-descripcion-hint">
            {form.descripcion.trim().length}/1000 caracteres (mínimo 10).
          </small>
          {mostrarError('descripcion') && (
            <small className="field-error" role="alert">{mostrarError('descripcion')}</small>
          )}
        </div>

        <div className="contrato-form-actions">
          <Link to="/incidencias" className="btn btn-secondary">Cancelar</Link>
          <button
            type="submit"
            className="btn btn-primary contrato-submit"
            disabled={enviando || (requiereContrato && (!form.id_contrato || form.id_contrato === SIN_CONTRATO || sinContratos))}
            aria-busy={enviando}
          >
            {enviando ? 'Enviando...' : 'Reportar incidencia'}
          </button>
        </div>
      </form>
    </div>
  );
}
