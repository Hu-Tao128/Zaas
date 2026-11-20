import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useComunicacionResource } from '../hooks/useComunicacionResource';

const ESTADOS = {
  proyectos: { activo: 'Activo', cerrado: 'Cerrado' },
  ofertas: { abierto: 'Abierta', en_progreso: 'En progreso', cerrado: 'Cerrada' },
};
const moneda = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' });
const fecha = new Intl.DateTimeFormat('es-MX', { dateStyle: 'medium' });

function Listado({ tipo, estado, pagina, setPagina }) {
  const params = new URLSearchParams({ tipo, estado, page: pagina, per_page: 10 });
  const resource = useComunicacionResource(`/admin/catalogo?${params}`);
  const { result, loading, error } = resource;
  const proyectos = tipo === 'proyectos';

  if (loading) return <p role="status">Cargando publicaciones…</p>;
  if (error) return <div className="alert alert-danger" role="alert">
    <p>{error}</p>
    <button className="btn btn-secondary" type="button" onClick={resource.reload}>Reintentar</button>
  </div>;
  if (!result) return null;

  return <>
    <div className="admin-catalogo-conteos" aria-label="Totales del catálogo">
      <span><strong>{result.conteos.proyectos.total}</strong> proyectos</span>
      <span><strong>{result.conteos.ofertas.total}</strong> ofertas</span>
      {Object.entries(ESTADOS[tipo]).map(([id, etiqueta]) =>
        <span className="admin-status" key={id}>{etiqueta} · {result.conteos[tipo].estados[id] ?? 0}</span>)}
    </div>
    {result.data.length ? <div className="catalogo-table-wrapper">
      <table aria-label={proyectos ? 'Proyectos registrados' : 'Ofertas registradas'}>
        <thead><tr>
          <th scope="col">{proyectos ? 'Proyecto' : 'Oferta'}</th>
          <th scope="col">{proyectos ? 'Autor' : 'Cliente'}</th>
          <th scope="col">Estado</th>
          <th scope="col">{proyectos ? 'Precio' : 'Presupuesto'}</th>
          <th scope="col">Publicación</th>
        </tr></thead>
        <tbody>{result.data.map(item => <tr key={item.id}>
          <td><Link to={`/${proyectos ? 'proyecto' : 'oferta'}/${item.id}`}>{item.titulo}</Link></td>
          <td>{item.responsable?.nombre || 'Sin responsable'}</td>
          <td><span className="admin-status">{ESTADOS[tipo][item.estado] || item.estado || 'Sin estado'}</span></td>
          <td>{item.monto == null ? 'Sin definir' : moneda.format(item.monto)}</td>
          <td>{item.fecha_publicacion ? fecha.format(new Date(item.fecha_publicacion)) : 'Sin fecha'}</td>
        </tr>)}</tbody>
      </table>
    </div> : <p className="admin-empty">No hay publicaciones que coincidan con el filtro.</p>}
    {result.meta.pages > 1 && <div className="admin-catalogo-paginacion">
      <button className="btn btn-secondary" type="button" disabled={pagina === 1}
        onClick={() => setPagina(pagina - 1)}>Anterior</button>
      <span>Página {pagina} de {result.meta.pages}</span>
      <button className="btn btn-secondary" type="button" disabled={!result.meta.has_next}
        onClick={() => setPagina(pagina + 1)}>Siguiente</button>
    </div>}
  </>;
}

export default function AdminCatalogo() {
  const [tipo, setTipo] = useState('proyectos');
  const [estado, setEstado] = useState('');
  const [pagina, setPagina] = useState(1);
  return <section className="card admin-reports" id="catalogo-admin" aria-labelledby="admin-catalogo-title">
    <div className="admin-reports-heading"><div>
      <h2 id="admin-catalogo-title">Catálogo y ofertas</h2>
      <p>Consulta las publicaciones del equipo, incluidas las cerradas.</p>
    </div></div>
    <div className="admin-catalogo-filtros">
      <label>Tipo de publicación
        <select value={tipo} onChange={event => {
          setTipo(event.target.value);
          setEstado('');
          setPagina(1);
        }}>
          <option value="proyectos">Proyectos</option>
          <option value="ofertas">Ofertas</option>
        </select>
      </label>
      <label>Estado
        <select value={estado} onChange={event => {
          setEstado(event.target.value);
          setPagina(1);
        }}>
          <option value="">Todos los estados</option>
          {Object.entries(ESTADOS[tipo]).map(([id, etiqueta]) =>
            <option key={id} value={id}>{etiqueta}</option>)}
        </select>
      </label>
    </div>
    <Listado key={`${tipo}:${estado}:${pagina}`} tipo={tipo} estado={estado} pagina={pagina} setPagina={setPagina} />
  </section>;
}
