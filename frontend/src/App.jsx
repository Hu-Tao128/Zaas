import { BrowserRouter, Routes, Route, Navigate, useLocation, useParams } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { CatalogoProvider, useCatalogo } from './context/CatalogoContext';
import CatalogoLayout from './components/catalogo/CatalogoLayout';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ComunicacionPage from './pages/ComunicacionPage';
import AdminPage from './pages/AdminPage';
import CatalogoIndexPage from './pages/catalogo/CatalogoIndexPage';
import DetalleProyectoPage from './pages/catalogo/DetalleProyectoPage';
import ProyectoFormPage from './pages/catalogo/ProyectoFormPage';
import MisProductosPage from './pages/catalogo/MisProductosPage';
import DemoFormPage from './pages/catalogo/DemoFormPage';
import OfertasPage from './pages/catalogo/OfertasPage';
import OfertaFormPage from './pages/catalogo/OfertaFormPage';
import DetalleOfertaPage from './pages/catalogo/DetalleOfertaPage';
import MisOfertasPage from './pages/catalogo/MisOfertasPage';
import PostularPage from './pages/catalogo/PostularPage';
import MisPostulacionesPage from './pages/catalogo/MisPostulacionesPage';
import DetallePostulacionPage from './pages/catalogo/DetallePostulacionPage';
import PerfilPage from './pages/catalogo/PerfilPage';
import ContratosList from './pages/contratos/ContratosList';
import ContratoForm from './pages/contratos/ContratoForm';
import ContratoDetalle from './pages/contratos/ContratoDetalle';
import './pages/catalogo/catalogo.css';
import './pages/contratos/contratos.css';

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div>Cargando...</div>;
  return user ? children : <Navigate to="/login" />;
}

function RoleRoute({ roles, children }) {
  const { usuario } = useCatalogo();
  return roles.includes(usuario.tipo_usuario) ? children : <Navigate to="/" replace />;
}

const soDesarrollador = (elemento) => <RoleRoute roles={['desarrollador']}>{elemento}</RoleRoute>;
const soCliente = (elemento) => <RoleRoute roles={['cliente']}>{elemento}</RoleRoute>;

// Las URLs antiguas (/catalogo/...) y el redirect que aún devuelve el login ("/catalogo/")
// se llevan a su equivalente en la raíz, conservando la búsqueda (?q=...).
function RedirigirDesdeCatalogo() {
  const { '*': resto } = useParams();
  const { search } = useLocation();
  return <Navigate to={`/${resto || ''}${search}`} replace />;
}

function CatalogoArea() {
  return (
    <ProtectedRoute>
      <CatalogoProvider>
        <CatalogoLayout />
      </CatalogoProvider>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/registro" element={<RegisterPage />} />
          <Route path="/comunicacion" element={
            <ProtectedRoute><ComunicacionPage /></ProtectedRoute>
          } />
          <Route path="/admin" element={<ProtectedRoute><AdminPage /></ProtectedRoute>} />
          <Route path="/catalogo/*" element={<RedirigirDesdeCatalogo />} />
          <Route path="/" element={<CatalogoArea />}>
            <Route index element={<CatalogoIndexPage />} />
            <Route path="proyecto/nuevo" element={soDesarrollador(<ProyectoFormPage />)} />
            <Route path="proyecto/:id" element={<DetalleProyectoPage />} />
            <Route path="proyecto/:id/editar" element={soDesarrollador(<ProyectoFormPage />)} />
            <Route path="proyecto/:id/demo" element={<DemoFormPage />} />
            <Route path="mis-productos" element={soDesarrollador(<MisProductosPage />)} />
            <Route path="ofertas" element={<OfertasPage />} />
            <Route path="oferta/nueva" element={soCliente(<OfertaFormPage />)} />
            <Route path="oferta/:id" element={<DetalleOfertaPage />} />
            <Route path="oferta/:id/editar" element={soCliente(<OfertaFormPage />)} />
            <Route path="oferta/:id/postular" element={soDesarrollador(<PostularPage />)} />
            <Route path="mis-ofertas" element={soCliente(<MisOfertasPage />)} />
            <Route path="mis-postulaciones" element={soDesarrollador(<MisPostulacionesPage />)} />
            <Route path="postulacion/:id" element={<DetallePostulacionPage />} />
            <Route path="contratos" element={<ContratosList />} />
            <Route path="contratos/nuevo" element={<ContratoForm />} />
            <Route path="contratos/:id" element={<ContratoDetalle />} />
            <Route path="perfil" element={<PerfilPage />} />
            <Route path="perfil/:id" element={<PerfilPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
