import { consultar, guardar } from './comunicacionService';

export function mensajeErrorIncidencia(error) {
  if (error?.status === 401) return 'Vuelve a iniciar sesión para continuar.';
  if (error?.status === 403) return 'No tienes permiso para realizar esta acción.';
  if (error?.status === 422) return error.message;
  return 'No se pudo procesar la incidencia. Inténtalo de nuevo.';
}

export const comunicacionApi = {
  notificaciones: async (pagina = 1, soloNoLeidas = false) => {
    const params = new URLSearchParams({ page: pagina, per_page: 20, solo_no_leidas: soloNoLeidas });
    const { data, meta, no_leidas } = await consultar(`/notificaciones?${params}`);
    return { items: data, meta, no_leidas };
  },
  marcarNotificacionLeida: (id) => guardar(`/notificaciones/${id}/leer`, {}, 'PATCH'),
  marcarNotificacionesLeidas: () => guardar('/notificaciones/leer'),

  chat: async (idContrato) => {
    const { data } = await consultar(`/contratos/${idContrato}/mensajes?per_page=100`);
    return { mensajes: data.reverse() };
  },
  enviarMensaje: async (idContrato, contenido) => {
    const { data: conversacion } = await guardar(`/contratos/${idContrato}/conversacion`);
    const { data: mensaje } = await guardar(`/conversaciones/${conversacion.id}/mensajes`, { contenido });
    return { mensaje_enviado: mensaje };
  },
  calificar: (idContrato, datos) =>
    guardar(`/contratos/${idContrato}/calificaciones`, { ...datos, puntaje: Number(datos.puntaje) }),

  incidencias: async (todas, pagina = 1, estado = '') => {
    const params = new URLSearchParams({ todas, page: pagina, per_page: todas ? 12 : 100, estado });
    const { data, meta } = await consultar(`/incidencias?${params}`);
    return { items: data, meta };
  },
  incidenciasContratos: () => consultar('/incidencias/contratos'),
  crearIncidencia: (datos) => guardar('/incidencias', datos),
  resolverIncidencia: (id, resolucion) =>
    guardar(`/incidencias/${id}/resolver`, { resolucion }, 'PATCH'),
};
