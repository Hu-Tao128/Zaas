import { Link, useLocation, useSearchParams } from 'react-router-dom';
import { useComunicacionResource } from '../hooks/useComunicacionResource';
import { formatDinero, formatFecha } from './catalogo/catalogoUtils';

function etiqueta(valor) {
  return valor?.replaceAll('_', ' ') || 'Sin especificar';
}

function estado(valor) {
  return <span className="admin-status">{etiqueta(valor)}</span>;
}

function contrato(id, texto, regreso, seccion = '') {
  return <Link to={`/contratos/${id}${seccion}`} state={{ adminOrigen: regreso }}>{texto}</Link>;
}

const vistas = {
  contratos: {
    titulo: 'Contratos y entregables',
    descripcion: 'Consulta los acuerdos de la plataforma y abre su detalle para revisar los entregables.',
    filtro: 'Estado',
    opciones: ['borrador', 'pendiente', 'aceptado', 'en_progreso', 'entregado', 'finalizado', 'cancelado'],
    columnas: [
      ['Contrato', (item, regreso) => contrato(item.id, `#${item.id} · ${item.objeto}`, regreso)],
      ['Cliente', item => item.cliente],
      ['Desarrollador', item => item.desarrollador],
      ['Estado', item => estado(item.estado)],
      ['Entregables aprobados', item => `${item.aprobados} de ${item.entregables}`],
      ['Creación', item => formatFecha(item.fecha)],
    ],
  },
  pagos: {
    titulo: 'Pagos y disputas',
    descripcion: 'Consulta los pagos en Escrow y los recibos desde el detalle de cada contrato.',
    filtro: 'Estado',
    opciones: ['retenido', 'liberado', 'reembolsado', 'dividido'],
    columnas: [
      ['Pago', item => `#${item.id}`],
      ['Contrato', (item, regreso) => contrato(item.id_contrato, `#${item.id_contrato}`, regreso, '#pagos')],
      ['Monto', item => `${formatDinero(item.monto)} MXN`],
      ['Estado', item => estado(item.estado)],
      ['Método', item => etiqueta(item.metodo)],
      ['Fecha de pago', item => formatFecha(item.fecha)],
    ],
  },
  disputas: {
    titulo: 'Pagos y disputas',
    descripcion: 'Abre una disputa para revisar el caso y resolverlo desde el contrato asociado.',
    filtro: 'Estado',
    opciones: ['abierta', 'en_revision', 'resuelta', 'cerrada'],
    columnas: [
      ['Disputa', (item, regreso) => contrato(item.id_contrato, `#${item.id}`, regreso, `#disputa-${item.id}`)],
      ['Contrato', item => `#${item.id_contrato}`],
      ['Tipo', item => etiqueta(item.tipo)],
      ['Reportante', item => item.reportante || 'Sin reportante'],
      ['Estado', item => estado(item.estado)],
      ['Apertura', item => formatFecha(item.fecha)],
    ],
  },
  usuarios: {
    titulo: 'Usuarios y permisos',
    descripcion: 'Consulta las cuentas registradas y el rol asignado a cada usuario.',
    filtro: 'Rol',
    opciones: ['cliente', 'desarrollador', 'admin'],
    columnas: [
      ['Usuario', item => <Link to={`/perfil/${item.id}`}>{item.nombre}</Link>],
      ['Correo', item => item.email],
      ['Rol', item => estado(item.rol === 'admin' ? 'Administrador' : item.rol)],
      ['Registro', item => formatFecha(item.fecha)],
    ],
  },
};

function Listado({ modulo, vista, filtro, pagina, cambiarPagina, regreso }) {
  const params = new URLSearchParams({ [vista.filtro.toLowerCase()]: filtro, page: pagina, per_page: 10 });
  const { result, loading, error, reload } = useComunicacionResource(`/admin/${modulo}?${params}`);

  if (loading) return <p role="status">Cargando registros…</p>;
  if (error) return <div className="alert alert-danger" role="alert">
    <p>{error}</p>
    <button className="btn btn-secondary" type="button" onClick={reload}>Reintentar</button>
  </div>;
  if (!result) return null;

  return <>
    <p>{result.meta.total} registros</p>
    {result.data.length ? <div className="catalogo-table-wrapper">
      <table aria-label={modulo === 'pagos' ? 'Pagos' : modulo === 'disputas' ? 'Disputas' : vista.titulo}>
        <thead><tr>{vista.columnas.map(([nombre]) => <th scope="col" key={nombre}>{nombre}</th>)}</tr></thead>
        <tbody>{result.data.map(item => <tr key={item.id}>
          {vista.columnas.map(([nombre, mostrar]) => <td key={nombre}>{mostrar(item, regreso)}</td>)}
        </tr>)}</tbody>
      </table>
    </div> : <p className="admin-empty">No hay registros en esta página para el filtro seleccionado.</p>}
    {(result.meta.pages > 1 || pagina > 1) && <div className="admin-catalogo-paginacion">
      <button className="btn btn-secondary" type="button" disabled={pagina === 1}
        onClick={() => cambiarPagina(pagina - 1)}>Anterior</button>
      <span>Página {pagina}{result.meta.pages >= pagina ? ` de ${result.meta.pages}` : ''}</span>
      <button className="btn btn-secondary" type="button" disabled={!result.meta.has_next}
        onClick={() => cambiarPagina(pagina + 1)}>Siguiente</button>
    </div>}
  </>;
}

export default function AdminRegistros({ modulo }) {
  const [params, setParams] = useSearchParams();
  const location = useLocation();
  const vista = vistas[modulo];
  const filtro = params.get('filtro') || '';
  const pagina = Math.max(1, Number.parseInt(params.get('pagina'), 10) || 1);

  function cambiarConsulta(nuevoFiltro, nuevaPagina) {
    setParams({ modulo, filtro: nuevoFiltro, pagina: nuevaPagina });
  }

  return <section className="card admin-reports" aria-labelledby="admin-registros-titulo">
    <div className="admin-reports-heading"><div>
      <h2 id="admin-registros-titulo">{vista.titulo}</h2>
      <p>{vista.descripcion}</p>
    </div><Link to="/admin" className="btn btn-secondary">Volver al panel</Link></div>
    {(modulo === 'pagos' || modulo === 'disputas') && <nav className="admin-catalogo-filtros" aria-label="Pagos y disputas">
      <Link to="?modulo=pagos" className={`btn ${modulo === 'pagos' ? 'btn-primary' : 'btn-secondary'}`}
        aria-current={modulo === 'pagos' ? 'page' : undefined}>Pagos</Link>
      <Link to="?modulo=disputas" className={`btn ${modulo === 'disputas' ? 'btn-primary' : 'btn-secondary'}`}
        aria-current={modulo === 'disputas' ? 'page' : undefined}>Disputas</Link>
    </nav>}
    <div className="admin-catalogo-filtros">
      <label>{vista.filtro}
        <select value={filtro} onChange={event => cambiarConsulta(event.target.value, 1)}>
          <option value="">{vista.filtro === 'Rol' ? 'Todos los roles' : 'Todos los estados'}</option>
          {vista.opciones.map(opcion => <option value={opcion} key={opcion}>
            {opcion === 'admin' ? 'Administrador' : etiqueta(opcion)}
          </option>)}
        </select>
      </label>
    </div>
    <Listado key={`${modulo}:${filtro}:${pagina}`} modulo={modulo} vista={vista} filtro={filtro}
      pagina={pagina} cambiarPagina={valor => cambiarConsulta(filtro, valor)}
      regreso={`${location.pathname}${location.search}`} />
  </section>;
}
