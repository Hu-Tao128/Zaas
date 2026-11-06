import { Outlet } from 'react-router-dom';
import Navbar from '../Navbar';

export default function CatalogoLayout() {
  return (
    <div className="catalogo-app">
      <Navbar />
      <main className="catalogo-container" id="contenido-principal">
        <Outlet />
      </main>
    </div>
  );
}
