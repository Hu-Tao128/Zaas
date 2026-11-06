import { useState } from 'react';
import { registerWithEmail, loginWithGoogle } from '../services/authService';
import { useNavigate, Link } from 'react-router-dom';

export default function RegisterPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleRegister(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const { idToken } = await registerWithEmail(email, password);
      await fetch('/auth/registro/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken, tipo_usuario: 'cliente' })
      });
      navigate('/');
    } catch (err) {
      setError(err.message || 'Error al registrarse');
    } finally {
      setLoading(false);
    }
  }

  async function handleGoogleRegister() {
    setError('');
    setLoading(true);
    try {
      const { idToken } = await loginWithGoogle();
      await fetch('/auth/registro/callback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id_token: idToken, tipo_usuario: 'cliente' })
      });
      navigate('/');
    } catch (err) {
      setError(err.message || 'Error con Google');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-container">
      <h1>Crear Cuenta</h1>
      
      {error && <div className="error">{error}</div>}
      
      <form onSubmit={handleRegister}>
        <input
          type="email"
          placeholder="Correo electrónico"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Contraseña"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Cargando...' : 'Registrarse'}
        </button>
      </form>

      <div className="divider">o</div>

      <button onClick={handleGoogleRegister} disabled={loading} className="google-btn">
        Registrarse con Google
      </button>

      <p>
        ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
      </p>
    </div>
  );
}
