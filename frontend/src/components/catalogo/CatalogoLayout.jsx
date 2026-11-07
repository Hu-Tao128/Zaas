import { Outlet } from 'react-router-dom';
import Navbar from '../Navbar';
import { useCatalogo } from '../../context/CatalogoContext';

export default function CatalogoLayout() {
  const { usuario } = useCatalogo();
  return (
    <div className="catalogo-app">
      <Navbar usuario={usuario} />
      <main className="catalogo-container" id="contenido-principal">
        <Outlet />
      </main>
    </div>
  );
}
