export const ESTADOS_PAGO_LABEL = {
  pendiente: 'Pendiente de confirmación',
  retenido: 'Fondos en garantía',
  fallido: 'Pago no completado',
  liberado: 'Fondos liberados',
  reembolsado: 'Fondos devueltos',
  dividido: 'Fondos divididos',
};

export const ESTADOS_DISPUTA_LABEL = {
  abierta: 'Abierta',
  en_revision: 'En revisión',
  resuelta: 'Resuelta',
  cerrada: 'Cerrada',
};

export const TIPOS_DISPUTA_LABEL = {
  pago: 'Pago',
  entregable: 'Entregable',
  contrato: 'Contrato en general',
  incumplimiento: 'Incumplimiento',
  otro: 'Otro',
};

export const DECISIONES_LABEL = {
  liberar: 'Liberar fondos al desarrollador',
  reembolsar: 'Reembolsar fondos al cliente',
  dividir: 'Dividir fondos',
};

const CODIGOS_ERROR = {
  sin_conexion: 'No se pudo conectar con el servidor. Verifica tu conexión e inténtalo de nuevo.',
  error_interno: 'Ocurrió un problema al procesar tu solicitud. Inténtalo de nuevo más tarde.',
  contrato_no_encontrado: 'No se encontró el contrato solicitado.',
  pago_no_encontrado: 'No se encontró el pago solicitado.',
  disputa_no_encontrada: 'No se encontró la disputa solicitada.',
  permisos: 'No tienes permisos para realizar esta acción.',
  no_autenticado: 'Tu sesión no es válida o ha expirado. Inicia sesión nuevamente.',
  validacion: 'Revisa la información ingresada e inténtalo de nuevo.',
  estado_invalido: 'La operación no está disponible en el estado actual.',
  saldo_insuficiente: 'El monto indicado supera el saldo disponible.',
  monto_invalido: 'El monto indicado no es válido.',
  idempotencia_conflicto: 'Ya se está procesando una operación similar. Espera un momento e inténtalo de nuevo.',
};

const CODIGOS_FALLO = {
  expirado: 'El tiempo para confirmar el pago expiró. Puedes intentar un nuevo depósito.',
  fondos_insuficientes: 'El medio de pago no tiene fondos suficientes.',
  tarjeta_rechazada: 'El medio de pago fue rechazado.',
  verificacion_fallida: 'No se pudo verificar el pago. Revisa el código e inténtalo de nuevo.',
  verificacion_requerida: 'Se requiere verificación para completar el pago.',
};

export function mensajeError(err) {
  if (!err) return 'Ocurrió un problema. Inténtalo de nuevo.';
  const codigo = err.codigo;
  const errores = err.errores || {};
  const codigoFallo = errores.codigo_fallo || (err.data && err.data.codigo_fallo);
  if (codigoFallo && CODIGOS_FALLO[codigoFallo]) return CODIGOS_FALLO[codigoFallo];
  if (codigo && CODIGOS_ERROR[codigo]) return CODIGOS_ERROR[codigo];
  if (err.status === 401 || err.status === 403) return CODIGOS_ERROR.permisos;
  if (err.status === 404) return CODIGOS_ERROR.contrato_no_encontrado;
  if (typeof err.message === 'string' && err.message && !/^\s*$/.test(err.message)) {
    // evitar mostrar mensajes técnicos crudos obvios
    if (/Error del servidor|\(\d{3}\)/i.test(err.message)) return CODIGOS_ERROR.error_interno;
    return err.message;
  }
  return CODIGOS_ERROR.error_interno;
}

export function parseMonto(valor) {
  if (valor == null || valor === '') return 0;
  const n = Number(String(valor));
  return Number.isFinite(n) ? n : 0;
}

export function formatMonto(valor, moneda = 'MXN') {
  const n = parseMonto(valor);
  try {
    return new Intl.NumberFormat('es-MX', { style: 'currency', currency: moneda }).format(n);
  } catch {
    return `$${n.toFixed(2)} ${moneda}`;
  }
}
