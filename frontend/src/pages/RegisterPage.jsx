import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { registerWithEmail, loginWithGoogle } from '../services/authService';
import { useAuth } from '../context/AuthContext';
import GoogleButton from '../components/GoogleButton';
import RoleSelector from '../components/RoleSelector';

/**
 * Página de Registro con Flujo Intermedio de Selección de Rol.
 * Paso 1: Autenticación con Firebase (Email/Password o Google).
 * Paso 2 (Intermedio): Selección de tipo de usuario ('cliente' o 'desarrollador')
 * con tarjetas interactivas y borde resaltado en #991B1B antes de sincronizar con Flask.
 */
export default function RegisterPage() {
  // Estado del flujo ('credenciales' o 'seleccion_rol')
  const [paso, setPaso] = useState('credenciales');

  // Datos personales del formulario
  const [nombres, setNombres] = useState('');
  const [apellidoPaterno, setApellidoPaterno] = useState('');
  const [apellidoMaterno, setApellidoMaterno] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Rol seleccionado ('cliente' o 'desarrollador')
  const [rolSeleccionado, setRolSeleccionado] = useState('cliente');

  // Datos de autenticación retenidos tras el éxito con Firebase
  const [firebaseData, setFirebaseData] = useState(null);

  // Estados de validación y carga
  const [errores, setErrores] = useState({});
  const [errorGeneral, setErrorGeneral] = useState('');
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const { marcarAutenticado, iniciarRegistro, finalizarRegistro } = useAuth();
  useEffect(() => finalizarRegistro, [finalizarRegistro]);

  function validarPasoCredenciales() {
    const nuevosErrores = {};
    if (!nombres.trim()) {
      nuevosErrores.nombres = 'El nombre es obligatorio.';
    }
    if (!apellidoPaterno.trim()) {
      nuevosErrores.apellidoPaterno = 'El apellido paterno es obligatorio.';
    }
    if (!email.trim()) {
      nuevosErrores.email = 'El correo electrónico es obligatorio.';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      nuevosErrores.email = 'Ingresa un correo electrónico válido.';
    }
    if (!password) {
      nuevosErrores.password = 'La contraseña es obligatoria.';
    } else if (password.length < 6) {
      nuevosErrores.password = 'La contraseña debe tener al menos 6 caracteres.';
    }

    setErrores(nuevosErrores);
    return Object.keys(nuevosErrores).length === 0;
  }

  // Paso 1 con Email y Contraseña
  async function handleCredencialesSubmit(e) {
    e.preventDefault();
    setErrorGeneral('');

    if (!validarPasoCredenciales()) {
      return;
    }

    setLoading(true);
    iniciarRegistro();
    try {
      // 1. Autenticar primero con Firebase Auth
      const { user, idToken } = await registerWithEmail(email, password);

      // 2. Retener credenciales y pasar a la selección de rol (no sincronizar aún)
      setFirebaseData({ user, idToken });
      setPaso('seleccion_rol');
    } catch (err) {
      finalizarRegistro();
      if (err.code === 'auth/email-already-in-use') {
        setErrorGeneral('Este correo ya está registrado. Inicia sesión o usa otro.');
      } else if (err.code === 'auth/weak-password') {
        setErrorGeneral('La contraseña debe tener al menos 6 caracteres.');
      } else {
        setErrorGeneral(err.message || 'Error al autenticar con Firebase.');
      }
    } finally {
      setLoading(false);
    }
  }

  // Paso 1 con Google
  async function handleGoogleSubmit() {
    setErrorGeneral('');
    setLoading(true);
    iniciarRegistro();
    try {
      // 1. Autenticar con Google Provider
      const { user, idToken } = await loginWithGoogle();

      // Rellenar nombres sugeridos desde el perfil de Google si están vacíos
      if (user.displayName) {
        const partes = user.displayName.split(' ');
        if (!nombres) setNombres(partes[0] || '');
        if (!apellidoPaterno) setApellidoPaterno(partes.slice(1).join(' ') || 'Zaas');
      }
      if (!email && user.email) {
        setEmail(user.email);
      }

      // 2. Retener credenciales y abrir selector de rol
      setFirebaseData({ user, idToken });
      setPaso('seleccion_rol');
    } catch (err) {
      finalizarRegistro();
      setErrorGeneral(err.message || 'Error al iniciar con Google.');
    } finally {
      setLoading(false);
    }
  }

  // Paso 2: Confirmar Rol y Sincronizar con el Backend en Flask
  async function handleConfirmarRol() {
    if (!firebaseData || !rolSeleccionado) return;

    setErrorGeneral('');
    setLoading(true);

    try {
      const response = await fetch('/auth/registro/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          id_token: await firebaseData.user.getIdToken(),
          tipo_usuario: rolSeleccionado,
          nombres: nombres.trim() || firebaseData.user.displayName?.split(' ')[0] || 'Usuario',
          apellido_paterno: apellidoPaterno.trim() || firebaseData.user.displayName?.split(' ').slice(1).join(' ') || 'Zaas',
          apellido_materno: apellidoMaterno.trim() || '',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.error || 'Error al sincronizar tu cuenta con Zaas');
      }

      await response.json();
      // Marcar la sesión de Firebase como activa antes de navegar para evitar
      // que ProtectedRoute rebote a /login por una condición de carrera.
      marcarAutenticado(firebaseData.user);
      navigate('/', { replace: true });
    } catch (err) {
      setErrorGeneral(err.message || 'Error al guardar tu cuenta en el servidor.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrapper">
      {paso === 'credenciales' ? (
        <div className="auth-container zaas-auth-card">
          <div className="auth-header-brand">
            <span className="auth-brand-logo">Zaas<span className="brand-dot">.</span></span>
            <h1>Crear Cuenta</h1>
            <p className="auth-subtitle">
              Únete al marketplace de SaaS y talento tecnológico con garantía Escrow.
            </p>
          </div>

          {errorGeneral && (
            <div className="error" role="alert">
              {errorGeneral}
            </div>
          )}

          <form onSubmit={handleCredencialesSubmit} noValidate aria-label="Formulario de registro">
            <div className="form-group">
              <label htmlFor="reg-nombres">
                Nombres <span className="zaas-required-asterisk">*</span>
              </label>
              <input
                id="reg-nombres"
                type="text"
                placeholder="Ej. Juan Carlos"
                value={nombres}
                onChange={(e) => {
                  setNombres(e.target.value);
                  if (errores.nombres) setErrores((prev) => ({ ...prev, nombres: '' }));
                }}
                className={errores.nombres ? 'input-error' : ''}
                aria-invalid={Boolean(errores.nombres)}
                aria-describedby={errores.nombres ? 'err-reg-nombres' : undefined}
                required
              />
              {errores.nombres && (
                <small className="field-error" id="err-reg-nombres" role="alert">
                  {errores.nombres}
                </small>
              )}
            </div>

            <div className="zaas-form-grid-2">
              <div className="form-group">
                <label htmlFor="reg-paterno">
                  Apellido Paterno <span className="zaas-required-asterisk">*</span>
                </label>
                <input
                  id="reg-paterno"
                  type="text"
                  placeholder="Ej. Pérez"
                  value={apellidoPaterno}
                  onChange={(e) => {
                    setApellidoPaterno(e.target.value);
                    if (errores.apellidoPaterno) setErrores((prev) => ({ ...prev, apellidoPaterno: '' }));
                  }}
                  className={errores.apellidoPaterno ? 'input-error' : ''}
                  aria-invalid={Boolean(errores.apellidoPaterno)}
                  aria-describedby={errores.apellidoPaterno ? 'err-reg-paterno' : undefined}
                  required
                />
                {errores.apellidoPaterno && (
                  <small className="field-error" id="err-reg-paterno" role="alert">
                    {errores.apellidoPaterno}
                  </small>
                )}
              </div>

              <div className="form-group">
                <label htmlFor="reg-materno">Apellido Materno</label>
                <input
                  id="reg-materno"
                  type="text"
                  placeholder="Ej. González"
                  value={apellidoMaterno}
                  onChange={(e) => setApellidoMaterno(e.target.value)}
                />
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="reg-email">
                Correo Electrónico <span className="zaas-required-asterisk">*</span>
              </label>
              <input
                id="reg-email"
                type="email"
                placeholder="tu@correo.com"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value);
                  if (errores.email) setErrores((prev) => ({ ...prev, email: '' }));
                }}
                className={errores.email ? 'input-error' : ''}
                aria-invalid={Boolean(errores.email)}
                aria-describedby={errores.email ? 'err-reg-email' : undefined}
                required
              />
              {errores.email && (
                <small className="field-error" id="err-reg-email" role="alert">
                  {errores.email}
                </small>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="reg-password">
                Contraseña <span className="zaas-required-asterisk">*</span>
              </label>
              <input
                id="reg-password"
                type="password"
                placeholder="Mínimo 6 caracteres"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errores.password) setErrores((prev) => ({ ...prev, password: '' }));
                }}
                className={errores.password ? 'input-error' : ''}
                aria-invalid={Boolean(errores.password)}
                aria-describedby={errores.password ? 'err-reg-password' : undefined}
                required
                minLength={6}
              />
              {errores.password && (
                <small className="field-error" id="err-reg-password" role="alert">
                  {errores.password}
                </small>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary btn-auth-submit"
              aria-busy={loading}
            >
              {loading ? (
                <>
                  <span className="zaas-button-spinner" aria-hidden="true" />
                  <span>Verificando credenciales...</span>
                </>
              ) : (
                <span>Continuar a Selección de Rol →</span>
              )}
            </button>
          </form>

          <div className="divider" aria-hidden="true">
            <span>o</span>
          </div>

          <GoogleButton
            label="Registrarse con Google"
            onClick={handleGoogleSubmit}
            disabled={loading}
          />

          <p className="auth-footer-text">
            ¿Ya tienes cuenta? <Link to="/login">Inicia sesión aquí</Link>
          </p>
        </div>
      ) : (
        /* Paso 2: Selector de Rol Intermedio */
        <div className="zaas-role-page-wrapper">
          <div className="zaas-role-modal-container">
            <RoleSelector
              rolSeleccionado={rolSeleccionado}
              onSeleccionarRol={setRolSeleccionado}
              onConfirmar={handleConfirmarRol}
              onVolver={() => setPaso('credenciales')}
              cargando={loading}
              error={errorGeneral}
            />
          </div>
        </div>
      )}
    </div>
  );
}
