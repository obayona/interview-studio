import { useState } from 'react';
import type { SyntheticEvent } from 'react';

import { Button } from '../../components/ui/Button';
import { ApiError } from '../../services/api-client';
import { authApi } from '../../services/auth-api';

function safeDestination(): string {
  const value = new URLSearchParams(window.location.search).get('next');
  return value?.startsWith('/') && !value.startsWith('//') ? value : '/';
}

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const submit = async (
    event: SyntheticEvent<HTMLFormElement, SubmitEvent>,
  ) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await authApi.login(username, password);
      window.location.replace(safeDestination());
    } catch (reason) {
      setError(
        reason instanceof ApiError
          ? reason.message
          : 'Interview Studio could not sign you in.',
      );
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page" id="main-content">
      <section className="login-card" aria-labelledby="login-title">
        <p className="login-card__eyebrow">Interview Studio</p>
        <h1 id="login-title">Welcome back</h1>
        <p className="login-card__intro">
          Sign in to access your private interview workspace.
        </p>
        <form className="login-card__form" onSubmit={submit}>
          <label className="ui-field">
            <span className="ui-field__label">Username</span>
            <input
              className="ui-input"
              name="username"
              autoComplete="username"
              required
              value={username}
              onChange={(event) => setUsername(event.target.value)}
            />
          </label>
          <label className="ui-field">
            <span className="ui-field__label">Password</span>
            <input
              className="ui-input"
              type="password"
              name="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>
          {error && (
            <p className="login-card__error" role="alert">
              {error}
            </p>
          )}
          <Button type="submit" variant="primary" disabled={submitting}>
            {submitting ? 'Signing in…' : 'Sign in'}
          </Button>
        </form>
      </section>
    </main>
  );
}
