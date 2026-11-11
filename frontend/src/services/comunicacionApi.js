import { consultar, guardar } from './comunicacionService';

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
  crearIncidencia: (datos) => guardar('/incidencias', datos),
  resolverIncidencia: (id, resolucion) =>
    guardar(`/incidencias/${id}/resolver`, { resolucion }, 'PATCH'),
};
