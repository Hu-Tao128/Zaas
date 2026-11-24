import { useCallback, useEffect, useRef, useState } from 'react';
import { useCatalogo } from '../context/CatalogoContext';
import { enviarMensaje } from '../services/agenteApi';
import './agente.css';

const ACCIONES_RAPIDAS = [
  { id: 'estado', etiqueta: 'Estado del ECBD', texto: '¿Cuál es el estado del ECBD?' },
  { id: 'etl', etiqueta: 'Ejecutar ETL', texto: 'Ejecuta el ETL', soloAdmin: true },
  { id: 'dataset', etiqueta: 'Dataset (50)', texto: 'Genera un dataset de 50 registros' },
];

const MENSAJE_INICIAL = {
  rol: 'agente',
  texto:
    'Hola, soy el agente del ECBD de Zaas. Puedo consultar el estado del sistema, ' +
    'ejecutar el ETL de saneamiento y generar datasets analíticos. ¿Qué necesitas?',
  accion: null,
};

function etiquetaAccion(accion) {
  switch (accion) {
    case 'estado_ecbd':
      return 'Consulta de estado';
    case 'etl':
      return 'ETL ejecutado';
    case 'etl_denegado':
      return 'Permiso insuficiente';
    case 'dataset':
      return 'Dataset generado';
    case 'ayuda':
      return 'Ayuda';
    default:
      return null;
  }
}

export default function AgenteChatPage() {
  const { usuario } = useCatalogo();
  const esAdmin = usuario?.tipo_usuario === 'admin';
  const [mensajes, setMensajes] = useState([MENSAJE_INICIAL]);
  const [borrador, setBorrador] = useState('');
  const [enviando, setEnviando] = useState(false);
  const finRef = useRef(null);

  useEffect(() => {
    finRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [mensajes, enviando]);

  const enviar = useCallback(
    async (texto) => {
      const limpio = texto.trim();
      if (!limpio || enviando) return;

      setMensajes((actuales) => [...actuales, { rol: 'usuario', texto: limpio }]);
      setBorrador('');
      setEnviando(true);

      try {
        const resultado = await enviarMensaje(limpio);
        setMensajes((actuales) => [
          ...actuales,
          {
            rol: 'agente',
            texto: resultado.respuesta,
            accion: resultado.accion,
          },
        ]);
      } catch (error) {
        setMensajes((actuales) => [
          ...actuales,
          {
            rol: 'agente',
            texto:
              error?.status === 401
                ? 'Tu sesión expiró. Vuelve a iniciar sesión para hablar con el agente.'
                : error?.message || 'No pude completar la acción. Inténtalo de nuevo.',
            accion: 'error',
            error: true,
          },
        ]);
      } finally {
        setEnviando(false);
      }
    },
    [enviando],
  );

  function manejarEnvio(event) {
    event.preventDefault();
    enviar(borrador);
  }

  function manejarTecla(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      enviar(borrador);
    }
  }

  return (
    <section className="agente-page" aria-labelledby="agente-titulo">
      <header className="agente-encabezado">
        <div>
          <span className="agente-eyebrow">Asistente del sistema</span>
          <h1 id="agente-titulo">Agente ECBD</h1>
          <p className="agente-descripcion">
            Conversa en lenguaje natural para consultar el estado del ECBD, ejecutar
            el saneamiento de telemetrías y generar datasets analíticos. El agente
            reutiliza las mismas herramientas que el servidor MCP del proyecto.
          </p>
        </div>
        <span className={`agente-rol ${esAdmin ? 'agente-rol--admin' : ''}`}>
          {esAdmin ? 'Administrador' : 'Usuario'}
        </span>
      </header>

      <div className="agente-chat card">
        <div className="agente-mensajes" role="log" aria-live="polite" aria-label="Conversación con el agente">
          {mensajes.map((mensaje, indice) => (
            <article
              key={`${mensaje.rol}-${indice}`}
              className={`agente-mensaje agente-mensaje--${mensaje.rol} ${
                mensaje.error ? 'agente-mensaje--error' : ''
              }`}
            >
              <div className="agente-burbuja">
                {mensaje.rol === 'agente' && etiquetaAccion(mensaje.accion) && (
                  <span className="agente-accion">{etiquetaAccion(mensaje.accion)}</span>
                )}
                <p className="agente-texto">{mensaje.texto}</p>
              </div>
            </article>
          ))}

          {enviando && (
            <div className="agente-mensaje agente-mensaje--agente">
              <div className="agente-burbuja agente-typing" role="status">
                <span className="agente-punto" />
                <span className="agente-punto" />
                <span className="agente-punto" />
                <span className="agente-typing-texto">El agente está analizando…</span>
              </div>
            </div>
          )}
          <div ref={finRef} />
        </div>

        <div className="agente-sugerencias" aria-label="Acciones rápidas">
          {ACCIONES_RAPIDAS.map((accion) => {
            const bloqueada = accion.soloAdmin && !esAdmin;
            return (
              <button
                key={accion.id}
                type="button"
                className="agente-chip"
                onClick={() => enviar(accion.texto)}
                disabled={enviando || bloqueada}
                title={bloqueada ? 'Solo disponible para administradores' : undefined}
              >
                {accion.etiqueta}
              </button>
            );
          })}
        </div>

        <form className="agente-form" onSubmit={manejarEnvio}>
          <label className="agente-label" htmlFor="agente-input">
            Escribe tu mensaje
          </label>
          <div className="agente-form-fila">
            <textarea
              id="agente-input"
              className="agente-input"
              value={borrador}
              onChange={(event) => setBorrador(event.target.value)}
              onKeyDown={manejarTecla}
              placeholder="Ej. ¿Cuál es el estado del ECBD?"
              rows={2}
              maxLength={500}
              disabled={enviando}
            />
            <button
              type="submit"
              className="btn btn-primary agente-enviar"
              disabled={enviando || !borrador.trim()}
            >
              {enviando ? 'Enviando…' : 'Enviar'}
            </button>
          </div>
          <p className="agente-ayuda-texto">
            Enter para enviar · Shift + Enter para salto de línea
          </p>
        </form>
      </div>
    </section>
  );
}
