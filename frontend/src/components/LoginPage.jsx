import { useState } from 'react';
import { mockLogin } from '../data/mockData';

function LoginPage({ onLoginSuccess }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  function handleSubmit(e) {
    e.preventDefault();

    if (!username.trim() || !password.trim()) {
      setError('Please enter both username and password.');
      return;
    }

    const result = mockLogin(username.trim(), password);

    if (result.success) {
      setError('');
      onLoginSuccess();
    } else {
      setError(result.message);
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-card__header">
          <div className="navbar__logo-mark navbar__logo-mark--lg">
            A
          </div>

          <div className="login-brand-label">
            AUTHENOVA
          </div>

          <h1>Verification Desk</h1>

          <p className="text-muted">
            Secure access for authorized identity verification officers.
          </p>
        </div>

        <div className="login-security-note">
          <span className="login-security-note__dot" />
          Secure officer access
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <label className="form-label" htmlFor="username">
            Username
          </label>

          <input
            id="username"
            type="text"
            className="form-input"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />

          <label className="form-label" htmlFor="password">
            Password
          </label>

          <input
            id="password"
            type="password"
            className="form-input"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />

          {error && (
            <div className="alert alert--error">
              {error}
            </div>
          )}

          <button
            type="submit"
            className="btn btn--primary btn--full"
          >
            Log In
          </button>
        </form>

        <div className="login-hint">
          <span>Demo access</span>

          <div className="login-hint__credentials">
            <code>officer1</code>
            <span>·</span>
            <code>authenova123</code>
          </div>
        </div>
      </div>
    </div>
  );
}

export default LoginPage;