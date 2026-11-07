import { useEffect, useState } from 'react';
import { loginWithEmail, loginWithGoogle } from '../services/authService';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import GoogleButton from '../components/GoogleButton';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { user, loading: authLoading, sincronizar, marcarAutenticado } = useAuth();

  // Si la sesión ya está activa (por ejemplo, tras un rebote de redirección),
  // llevar al usuario al área privada en lugar de dejarlo en /login.
  useEffect(() => {
    if (!authLoading && user) {
      navigate('/', { replace: true });
    }
  }, [authLoading, user, navigate]);

  async function handleEmailLogin(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { user: firebaseUser } = await loginWithEmail(email, password);
      await sincronizar(firebaseUser);
      marcarAutenticado(firebaseUser);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message || 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleLogin() {
    setError('');
    setLoading(true);
    try {
      const { user: firebaseUser } = await loginWithGoogle();
      await sincronizar(firebaseUser);
      marcarAutenticado(firebaseUser);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message || 'Error con Google');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-wrapper">
      <div className="auth-container zaas-auth-card">
        <div className="auth-header-brand">
          <Link to="/" className="auth-brand-logo" aria-label="Zaas - Inicio">
            Zaas<span className="brand-dot">.</span>
          </Link>
          <h1>Iniciar Sesión</h1>
          <p className="auth-subtitle">
            Accede a tu cuenta para comprar SaaS y contratar talento con garantía Escrow.
          </p>
        </div>

        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleEmailLogin} aria-label="Formulario de inicio de sesión">
          <div className="form-group">
            <label htmlFor="login-email">Correo electrónico</label>
            <input
              id="login-email"
              type="email"
              placeholder="tu@correo.com"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="login-password">Contraseña</label>
            <input
              id="login-password"
              type="password"
              placeholder="Tu contraseña"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary btn-auth-submit"
            aria-busy={loading}
          >
            {loading ? 'Cargando...' : 'Iniciar Sesión'}
          </button>
        </form>

        <div className="divider" aria-hidden="true">
          <span>o</span>
        </div>

        <GoogleButton
          label="Continuar con Google"
          onClick={handleGoogleLogin}
          disabled={loading}
        />

        <p className="auth-footer-text">
          ¿No tienes cuenta? <Link to="/registro">Regístrate aquí</Link>
        </p>
      </div>
    </div>
  );
}
