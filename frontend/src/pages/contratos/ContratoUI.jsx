import { ShieldCheckIcon } from '../../components/icons';

const ESTADOS = {
  borrador: { label: 'Borrador', clase: 'contrato-badge--borrador' },
  pendiente: { label: 'Pendiente de firma', clase: 'contrato-badge--pendiente' },
  aceptado: { label: 'Aceptado', clase: 'contrato-badge--aceptado' },
  en_progreso: { label: 'En progreso', clase: 'contrato-badge--progreso' },
  entregado: { label: 'Entregado', clase: 'contrato-badge--entregado' },
  finalizado: { label: 'Finalizado', clase: 'contrato-badge--finalizado' },
  cancelado: { label: 'Cancelado', clase: 'contrato-badge--cancelado' },
};

export function EstadoContratoBadge({ estado }) {
  const info = ESTADOS[estado] || {
    label: (estado || 'Desconocido').replaceAll('_', ' '),
    clase: 'contrato-badge--neutral',
  };
  return (
    <span className={`contrato-badge ${info.clase}`} role="status" aria-label={`Estado: ${info.label}`}>
      {info.label}
    </span>
  );
}

const ESCROW = {
  sin_deposito: { label: 'Sin depósito', clase: 'contrato-escrow-badge--pendiente' },
  retenido: { label: 'Retenido en Escrow', clase: 'contrato-escrow-badge--retenido' },
  liberado: { label: 'Liberado', clase: 'contrato-escrow-badge--liberado' },
  reembolsado: { label: 'Reembolsado', clase: 'contrato-escrow-badge--neutral' },
  dividido: { label: 'Dividido', clase: 'contrato-escrow-badge--neutral' },
};

export function EscrowBadge({ estado }) {
  const info = ESCROW[estado] || { label: estado || 'Escrow', clase: 'contrato-escrow-badge--neutral' };
  return (
    <span className={`contrato-escrow-badge ${info.clase}`} title={`Estado Escrow: ${info.label}`}>
      <ShieldCheckIcon size={13} />
      <span>{info.label}</span>
    </span>
  );
}

const ENTREGABLES = {
  pendiente: { label: 'Pendiente', clase: 'contrato-badge--borrador' },
  aprobado: { label: 'Aprobado', clase: 'contrato-badge--aceptado' },
  rechazado: { label: 'Rechazado', clase: 'contrato-badge--cancelado' },
};

export function EstadoEntregableBadge({ estado }) {
  const info = ENTREGABLES[estado] || {
    label: estado || 'Desconocido',
    clase: 'contrato-badge--neutral',
  };
  return (
    <span className={`contrato-badge ${info.clase}`} aria-label={`Entregable: ${info.label}`}>
      {info.label}
    </span>
  );
}

export function RolBadge({ rol }) {
  const esCliente = rol === 'cliente';
  return (
    <span className={`contrato-rol-badge ${esCliente ? 'contrato-rol-badge--cliente' : 'contrato-rol-badge--dev'}`}>
      {esCliente ? 'Cliente' : 'Desarrollador'}
    </span>
  );
}

export function CargandoContratos({ mensaje = 'Cargando contratos...' }) {
  return (
    <div className="card contrato-loading" role="status" aria-live="polite">
      <div className="zaas-spinner" aria-hidden="true" />
      <p>{mensaje}</p>
    </div>
  );
}

export function ErrorContratos({ error, onReintentar }) {
  return (
    <div className="card contrato-error" role="alert">
      <div className="alert alert-danger">{error?.message || 'No se pudieron cargar los contratos.'}</div>
      {onReintentar && (
        <button type="button" className="btn btn-secondary" onClick={onReintentar}>
          Reintentar
        </button>
      )}
    </div>
  );
}
