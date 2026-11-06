import { Outlet } from 'react-router-dom';
import { useCatalogo } from '../../context/CatalogoContext';
import AppNavbar from '../AppNavbar';

export default function CatalogoLayout() {
  const { usuario } = useCatalogo();

  return (
    <div className="catalogo-app">
      <AppNavbar usuario={usuario} />
      <main className="catalogo-container">
        <Outlet />
      </main>
    </div>
  );
}
