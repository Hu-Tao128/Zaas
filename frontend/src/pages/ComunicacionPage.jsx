import { useEffect, useState } from 'react';
import { Link, Navigate, useSearchParams } from 'react-router-dom';
import { guardar } from '../services/comunicacionService';
import { useComunicacionResource as useResource } from '../hooks/useComunicacionResource';
import Navbar from '../components/Navbar';
import './catalogo/catalogo.css';
import './comunicacion.css';

const TABS = {
  mensajes: 'Mensajes', demos: 'Solicitudes de demo', calificaciones: 'Calificaciones',
};
const date = value => value ? new Date(value).toLocaleString('es-MX') : '';

function useList(path) {
  const [page, setPage] = useState(1);
  const resource = useResource(`${path}${path.includes('?') ? '&' : '?'}page=${page}`);
  return { ...resource, page, setPage };
}

function useAction() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  async function run(action, message, after) {
    setPending(true); setError(''); setSuccess('');
    try {
      const result = await action();
      setSuccess(message);
      after?.(result);
    } catch (err) { setError(err.message); }
    finally { setPending(false); }
  }
  return { pending, error, success, run };
}

function Feedback({ action }) {
  return <div aria-live="polite">
    {action.error && <p className="comm-error" role="alert">{action.error}</p>}
    {action.success && <p className="comm-success">{action.success}</p>}
  </div>;
}

function Collection({ resource, empty, children }) {
  return <>
    <div className="comm-list-toolbar">
      <span>{resource.result ? `${resource.result.meta.total} registros` : ''}</span>
      <button type="button" onClick={resource.reload} disabled={resource.loading}>Recargar</button>
    </div>
    {resource.loading && <p role="status">Cargando…</p>}
    {resource.error && <p className="comm-error" role="alert">{resource.error}</p>}
    {!resource.loading && resource.result && (
      resource.result.data.length ? children(resource.result.data) : <p className="comm-empty">{empty}</p>
    )}
    {resource.result && resource.result.meta.pages > 1 && <div className="comm-pagination">
      <button type="button" disabled={resource.page <= 1 || resource.loading}
        onClick={() => resource.setPage(p => p - 1)}>Anterior</button>
      <span>Página {resource.page} de {resource.result.meta.pages}</span>
      <button type="button" disabled={!resource.result.meta.has_next || resource.loading}
        onClick={() => resource.setPage(p => p + 1)}>Siguiente</button>
    </div>}
  </>;
}

function ContractSelector({ value, onChange, finalized = false }) {
  const resource = useList('/contratos');
  return <div className="comm-contract-selector">
    <label>Contrato
      <select value={value} onChange={e => onChange(e.target.value)} disabled={resource.loading}>
        <option value="">Selecciona un contrato</option>
        {value && !resource.result?.data.some(c => String(c.id) === value) &&
          <option value={value}>Contrato #{value}</option>}
        {resource.result?.data.filter(c => !finalized || c.estado === 'finalizado').map(c =>
          <option key={c.id} value={c.id}>#{c.id} · {c.contraparte.nombre} · {c.estado}</option>)}
      </select>
    </label>
    {resource.loading && <p role="status">Cargando contratos…</p>}
    {resource.error && <p className="comm-error" role="alert">{resource.error}
      <button type="button" onClick={resource.reload}>Reintentar</button></p>}
    {resource.result?.data.length === 0 && <p className="comm-empty">Todavía no tienes contratos.</p>}
    {finalized && resource.result?.data.length > 0 &&
      !resource.result.data.some(c => c.estado === 'finalizado') &&
      <p className="comm-empty">No hay contratos finalizados en esta página.</p>}
    {resource.result?.meta.pages > 1 && <div className="comm-pagination">
      <button type="button" disabled={resource.page <= 1 || resource.loading}
        onClick={() => resource.setPage(p => p - 1)}>Contratos anteriores</button>
      <span>{resource.page} / {resource.result.meta.pages}</span>
      <button type="button" disabled={!resource.result.meta.has_next || resource.loading}
        onClick={() => resource.setPage(p => p + 1)}>Más contratos</button>
    </div>}
  </div>;
}

function Chat({ conversation, me }) {
  const resource = useList(`/conversaciones/${conversation.id}/mensajes`);
  const action = useAction();
  const [text, setText] = useState('');
  function send(e) {
    e.preventDefault();
    action.run(() => guardar(`/conversaciones/${conversation.id}/mensajes`, { contenido: text }),
      'Mensaje enviado.', () => { setText(''); resource.setPage(1); resource.reload(); });
  }
  return <section className="comm-panel" aria-label="Conversación">
    <h2>Contrato #{conversation.contrato.id} · {conversation.contrato.contraparte.nombre}</h2>
    <p className="comm-muted">Usa Recargar para ver mensajes nuevos. La página 1 contiene los más recientes.</p>
    <Feedback action={action} />
    <Collection resource={resource} empty="Todavía no hay mensajes. Puedes enviar el primero.">
      {items => <ol className="comm-messages">{[...items].reverse().map(m =>
        <li key={m.id} className={m.id_emisor === me.id ? 'comm-message mine' : 'comm-message'}>
          <strong>{m.id_emisor === me.id ? 'Tú' : conversation.contrato.contraparte.nombre}</strong>
          <p>{m.contenido}</p><small>{date(m.fecha_hora)} · {m.leido ? 'Leído' : 'Sin leer'}</small>
        </li>)}</ol>}
    </Collection>
    <button type="button" disabled={action.pending} onClick={() => action.run(
      () => guardar(`/conversaciones/${conversation.id}/leer`), 'Mensajes recibidos marcados como leídos.', resource.reload
    )}>Marcar recibidos como leídos</button>
    <form onSubmit={send} className="comm-form">
      <label>Mensaje<textarea value={text} onChange={e => setText(e.target.value)}
        required maxLength={5000} rows={3} placeholder="Escribe al otro participante del contrato" /></label>
      <button className="comm-primary" disabled={action.pending || !text.trim()}>
        {action.pending ? 'Guardando…' : 'Enviar mensaje'}</button>
    </form>
  </section>;
}

function Messages({ me, initialContract }) {
  const [contract, setContract] = useState(initialContract);
  const [conversation, setConversation] = useState(null);
  const list = useList('/conversaciones');
  const action = useAction();
  const [requestedContract, setRequestedContract] = useState('');
  function open(id) {
    setRequestedContract(id);
    action.run(() => guardar(`/contratos/${id}/conversacion`), '', ({ data }) => {
      setConversation(data); list.reload();
    });
  }
  return <>
    <section className="comm-panel">
      <h2>Mensajería por contrato</h2>
      <p>Las conversaciones son privadas entre el cliente y el desarrollador del contrato.</p>
      <ContractSelector value={contract} onChange={setContract} />
      <button className="comm-primary" type="button" disabled={!contract || action.pending}
        onClick={() => open(contract)}>Abrir conversación</button>
      <Feedback action={action} />
      <Collection resource={list} empty="Aún no hay conversaciones. Abre una usando un contrato.">
        {items => <ul className="comm-records">{items.map(item => <li key={item.id}>
          <span>Contrato #{item.contrato.id} · {item.contrato.contraparte.nombre}
            <small>{item.no_leidos} mensajes sin leer</small></span>
          <button type="button" disabled={action.pending} onClick={() => {
            setContract(String(item.contrato.id)); open(String(item.contrato.id));
          }}>Abrir</button>
        </li>)}</ul>}
      </Collection>
    </section>
    {conversation && <Chat key={`${conversation.id}-${requestedContract}`} conversation={conversation} me={me} />}
  </>;
}

function DemoForm({ me, onSaved }) {
  const projects = useList('/proyectos-demo');
  const action = useAction();
  const [project, setProject] = useState('');
  const [name, setName] = useState(me.nombre);
  const [email, setEmail] = useState(me.email);
  useEffect(() => { setProject(''); }, [projects.page]);
  function submit(e) {
    e.preventDefault();
    action.run(() => guardar(`/proyectos/${project}/solicitudes-demo`,
      { nombre_contacto: name, correo_contacto: email }), 'Solicitud de demo enviada.',
    () => { setProject(''); onSaved(); });
  }
  return <section className="comm-panel">
    <h2>Solicitar una demo</h2>
    <Feedback action={action} />
    <form className="comm-form" onSubmit={submit}>
      <label>Proyecto<select required value={project} onChange={e => setProject(e.target.value)}>
        <option value="">Selecciona un proyecto con demo</option>
        {projects.result?.data.map(p => <option key={p.id} value={p.id}>{p.titulo} · {p.autor.nombre}</option>)}
      </select></label>
      <Collection resource={projects} empty="No hay proyectos con demo disponible.">
        {() => <p className="comm-muted">Selecciona un proyecto de esta página.</p>}
      </Collection>
      <label>Nombre de contacto<input required maxLength={150} value={name} onChange={e => setName(e.target.value)} /></label>
      <label>Correo de contacto<input required type="email" maxLength={150} value={email}
        onChange={e => setEmail(e.target.value)} /></label>
      <button className="comm-primary" disabled={action.pending || projects.loading || !project}>Enviar solicitud</button>
    </form>
  </section>;
}

function Demos({ me }) {
  const resource = useList('/solicitudes-demo');
  return <>
    {me.tipo_usuario === 'cliente' && <DemoForm me={me} onSaved={() => { resource.setPage(1); resource.reload(); }} />}
    <section className="comm-panel">
      <h2>Solicitudes enviadas y recibidas</h2>
      <Collection resource={resource} empty="Todavía no tienes solicitudes de demo.">
        {items => <ul className="comm-records">{items.map(d => <li key={d.id}><div>
          <strong>{d.proyecto}</strong><span className="comm-badge">{d.id_cliente === me.id ? 'Enviada' : 'Recibida'}</span>
          <p>{d.nombre_contacto} · {d.correo_contacto}</p><small>{date(d.fecha_solicitud)}</small>
        </div></li>)}</ul>}
      </Collection>
    </section>
  </>;
}

function Ratings({ me, initialContract }) {
  const resource = useList('/calificaciones');
  const action = useAction();
  const [contract, setContract] = useState(initialContract);
  const [score, setScore] = useState('5');
  const [comment, setComment] = useState('');
  function submit(e) {
    e.preventDefault();
    action.run(() => guardar(`/contratos/${contract}/calificaciones`,
      { puntaje: Number(score), comentarios: comment }), 'Calificación enviada.',
    () => { setComment(''); setContract(''); resource.setPage(1); resource.reload(); });
  }
  return <>
    <section className="comm-panel">
      <h2>Calificar un contrato finalizado</h2>
      <p>Cada participante puede calificar una sola vez a su contraparte.</p>
      <Feedback action={action} />
      <form className="comm-form" onSubmit={submit}>
        <ContractSelector value={contract} onChange={setContract} finalized />
        <label>Puntaje<select value={score} onChange={e => setScore(e.target.value)}>
          {[5, 4, 3, 2, 1].map(n => <option key={n} value={n}>{n} de 5</option>)}
        </select></label>
        <label>Comentarios (opcional)<textarea maxLength={2000} rows={3} value={comment}
          onChange={e => setComment(e.target.value)} /></label>
        <button className="comm-primary" disabled={action.pending || !contract}>Enviar calificación</button>
      </form>
    </section>
    <section className="comm-panel">
      <h2>Calificaciones enviadas y recibidas</h2>
      <Collection resource={resource} empty="Aún no hay calificaciones.">
        {items => <ul className="comm-records">{items.map(c => <li key={c.id}><div>
          <strong>{c.puntaje} / 5 · Contrato #{c.id_contrato}</strong>
          <span className="comm-badge">{c.id_evaluador === me.id ? 'Enviada' : 'Recibida'}</span>
          <p>{c.evaluador.nombre} → {c.evaluado.nombre}</p>
          <p>{c.comentarios || 'Sin comentarios.'}</p><small>{date(c.fecha_hora)}</small>
        </div></li>)}</ul>}
      </Collection>
    </section>
  </>;
}

export default function ComunicacionPage() {
  const [params, setParams] = useSearchParams();
  const requestedTab = params.get('tab');
  if (requestedTab === 'incidencias' || requestedTab === 'notificaciones') {
    return <Navigate to={`/${requestedTab}`} replace />;
  }
  const tab = Object.hasOwn(TABS, requestedTab) ? requestedTab : 'mensajes';
  const contract = /^\d+$/.test(params.get('contrato') || '') ? params.get('contrato') : '';
  return <Comunicacion tab={tab} contract={contract} onChangeTab={id => setParams({ tab: id })} />;
}

function Comunicacion({ tab, contract, onChangeTab }) {
  const session = useResource('/sesion');
  const me = session.result?.data;
  return <div className="catalogo-app comm-page">
    <Navbar usuario={me} />
    <header className="comm-header"><div><Link to="/">← Inicio de Zaas</Link>
      <h1>Comunicación</h1><p>Mensajes, solicitudes de demo y calificaciones.</p></div>
      {me && <span className="comm-badge">{me.tipo_usuario === 'admin' ? 'Administrador' : me.tipo_usuario}</span>}
    </header>
    <nav className="comm-tabs" aria-label="Secciones de comunicación">{Object.entries(TABS).map(([id, label]) =>
      <button key={id} type="button" aria-current={tab === id ? 'page' : undefined}
        onClick={() => onChangeTab(id)}>{label}</button>)}</nav>
    <main className="comm-content">
      {session.loading && <p role="status">Cargando tu sesión…</p>}
      {session.error && <section className="comm-panel"><p className="comm-error" role="alert">{session.error}</p>
        <button type="button" onClick={session.reload}>Reintentar</button> <Link to="/login">Ir a iniciar sesión</Link></section>}
      {me && <div key={`${tab}-${contract}`}>
        {tab === 'mensajes' && <Messages me={me} initialContract={contract} />}
        {tab === 'demos' && <Demos me={me} />}
        {tab === 'calificaciones' && <Ratings me={me} initialContract={contract} />}
      </div>}
    </main>
  </div>;
}
