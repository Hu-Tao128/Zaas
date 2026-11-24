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

// Etiqueta de la resolución ya aplicada, en lenguaje natural para el detalle.
export const RESOLUCION_LABEL = {
  liberar: 'Pagar al desarrollador',
  reembolsar: 'Devolver al cliente',
  dividir: 'Repartir fondos',
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
  tarjeta_no_admitida: 'Esta tarjeta no está admitida en el modo demostración.',
  idempotencia_conflicto: 'Ya se está procesando una operación similar. Espera un momento e inténtalo de nuevo.',
};

const CODIGOS_FALLO = {
  tarjeta_no_admitida: 'Esta tarjeta no está admitida en el modo demostración.',
  expirado: 'El tiempo para confirmar el pago expiró. Puedes intentar un nuevo depósito.',
  fondos_insuficientes: 'El medio de pago no tiene fondos suficientes.',
  tarjeta_rechazada: 'El medio de pago fue rechazado.',
  verificacion_fallida: 'No se pudo verificar el pago. Revisa el código e inténtalo de nuevo.',
  verificacion_requerida: 'Se requiere verificación para completar el pago.',
};

export function mensajeError(err) {
  if (!err) return 'Ocurrió un problema. Inténtalo de nuevo.';
  const codigo = err.codigo || (err.data && err.data.codigo);
  const errores = err.errores || {};
  const codigoFallo = errores.codigo_fallo || (err.data && err.data.codigo_fallo);
  if (codigo === 'tarjeta_no_admitida' || codigoFallo === 'tarjeta_no_admitida') {
    return 'Esta tarjeta no está admitida en el modo demostración.';
  }
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

export function montoACentavos(valor) {
  if (valor == null || valor === '') return 0;
  const s = String(valor).trim();
  if (!s) return 0;
  const partes = s.split('.');
  const entero = parseInt(partes[0] || '0', 10);
  const decimalStr = (partes[1] || '').padEnd(2, '0').slice(0, 2);
  const decimal = parseInt(decimalStr, 10);
  return (Number.isNaN(entero) ? 0 : entero) * 100 + (Number.isNaN(decimal) ? 0 : decimal);
}

// Convierte centavos enteros a cadena decimal sin pasar por coma flotante.
export function centavosAMonto(centavos) {
  const n = Number.isFinite(centavos) ? Math.trunc(centavos) : 0;
  const signo = n < 0 ? '-' : '';
  const abs = Math.abs(n);
  return `${signo}${Math.trunc(abs / 100)}.${String(abs % 100).padStart(2, '0')}`;
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
