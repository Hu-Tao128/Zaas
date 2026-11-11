import { consultar, guardar } from './comunicacionService';

export const comunicacionApi = {
  notificaciones: async () => {
    const { data, no_leidas } = await consultar('/notificaciones?per_page=50');
    return { items: data, no_leidas };
  },
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

  incidencias: async (todas) => {
    const { data } = await consultar(`/incidencias?per_page=100&todas=${todas}`);
    return { items: data };
  },
  crearIncidencia: (datos) => guardar('/incidencias', datos),
  resolverIncidencia: (id, resolucion) =>
    guardar(`/incidencias/${id}/resolver`, { resolucion }, 'PATCH'),
};
