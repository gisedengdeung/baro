import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuthStore from '../../store/useAuthStore';
import './Signup.css';

function Signup() {
  const navigate = useNavigate();

  const signup = useAuthStore((state) => state.signup);
  const isLoading = useAuthStore((state) => state.isLoading);
  const authError = useAuthStore((state) => state.error);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState('operator');
  const [localError, setLocalError] = useState(null);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setLocalError(null);

    if (password.length < 8) {
      setLocalError('비밀번호는 최소 8자 이상이어야 합니다.');
      return;
    }

    if (password !== confirmPassword) {
      setLocalError('비밀번호 확인이 일치하지 않습니다.');
      return;
    }

    try {
      await signup(email, password, role);
      navigate('/dashboard', { replace: true });
    } catch (_error) {
      // error message is handled by store state
    }
  };

  return (
    <div className="login-container">
      <div className="container">
        <div className="heading">Sign Up</div>
        <form className="form" onSubmit={handleSubmit}>
          <input
            required
            className="input"
            type="email"
            name="email"
            id="signup-email"
            placeholder="E-mail"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <input
            required
            className="input"
            type="password"
            name="password"
            id="signup-password"
            placeholder="Password (min 8)"
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <input
            required
            className="input"
            type="password"
            name="confirm-password"
            id="signup-confirm-password"
            placeholder="Confirm Password"
            minLength={8}
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
          />
          <select
            className="input"
            name="role"
            id="signup-role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            <option value="operator">Operator</option>
            <option value="admin">Admin</option>
          </select>
          {(localError || authError) && (
            <div style={{ color: '#b00020', fontSize: '0.9rem', marginTop: '10px' }}>{localError || authError}</div>
          )}
          <input
            className="login-button"
            type="submit"
            value={isLoading ? 'Signing Up...' : 'Sign Up'}
            disabled={isLoading}
          />
        </form>
        <Link to="/login" className="signup-link">
          Already have an account? Sign in
        </Link>
      </div>
    </div>
  );
}

export default Signup;
