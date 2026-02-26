import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import './Login.css';
import useAuthStore from '../../store/useAuthStore';

function Login() {
  const navigate = useNavigate();
  const location = useLocation();

  const login = useAuthStore((state) => state.login);
  const isLoading = useAuthStore((state) => state.isLoading);
  const error = useAuthStore((state) => state.error);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();

    try {
      await login(email, password);
      const nextPath = location.state?.from?.pathname || '/dashboard';
      navigate(nextPath, { replace: true });
    } catch (_error) {
      // error message is handled by store state
    }
  };

  return (
    <div className="login-container">
      <div className="container">
        <div className="heading">Login</div>
        <form className="form" onSubmit={handleSubmit}>
          <input
            required
            className="input"
            type="email"
            name="email"
            id="email"
            placeholder="E-mail"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <input
            required
            className="input"
            type="password"
            name="password"
            id="password"
            placeholder="Password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {error && (
            <div style={{ color: '#b00020', fontSize: '0.9rem', marginTop: '4px' }}>
              {error}
            </div>
          )}
          <input
            className="login-button"
            type="submit"
            value={isLoading ? 'Signing In...' : 'Sign In'}
            disabled={isLoading}
          />
        </form>
        <Link to="/signup" className="signup-link">
          Create a new account
        </Link>
      </div>
    </div>
  );
}

export default Login;
