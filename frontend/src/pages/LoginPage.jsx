import { useState } from 'react';
import { loginWithEmail, loginWithGoogle } from '../services/authService';
import { useNavigate, Link } from 'react-router-dom';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleEmailLogin(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { idToken } = await loginWithEmail(email, password);
      const response = await fetch('/auth/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken }),
        credentials: 'include'
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Error de autenticación');
      }
      
      const data = await response.json();
      console.log('Login exitoso:', data);
      navigate(data.redirect || '/');
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
      const { idToken } = await loginWithGoogle();
      const response = await fetch('/auth/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken }),
        credentials: 'include'
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Error con Google');
      }
      
      const data = await response.json();
      console.log('Login con Google exitoso:', data);
      navigate(data.redirect || '/');
    } catch (err) {
      setError(err.message || 'Error con Google');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-container">
      <h1>Iniciar Sesión</h1>
      
      {error && <div className="error" role="alert">{error}</div>}
      
      <form onSubmit={handleEmailLogin} aria-label="Formulario de inicio de sesión">
        <label htmlFor="login-email" className="sr-only">Correo electrónico</label>
        <input
          id="login-email"
          type="email"
          placeholder="Correo electrónico"
          aria-label="Correo electrónico"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <label htmlFor="login-password" className="sr-only">Contraseña</label>
        <input
          id="login-password"
          type="password"
          placeholder="Contraseña"
          aria-label="Contraseña"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit" disabled={loading} aria-busy={loading}>
          {loading ? 'Cargando...' : 'Iniciar Sesión'}
        </button>
      </form>

      <div className="divider" aria-hidden="true">o</div>

      <button onClick={handleGoogleLogin} disabled={loading} className="google-btn" aria-label="Continuar con Google">
        Continuar con Google
      </button>

      <p>
        ¿No tienes cuenta? <Link to="/registro">Regístrate aquí</Link>
      </p>
    </div>
  );
}
