import { useEffect, useState } from 'react';

import { authApi } from '../../services/auth-api';

export function LogoutButton() {
  const [busy, setBusy] = useState(false);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    void authApi
      .session()
      .then((session) => setVisible(session.username !== 'development'))
      .catch(() => setVisible(false));
  }, []);

  const logout = async () => {
    setBusy(true);
    try {
      await authApi.logout();
    } finally {
      window.location.assign('/login');
    }
  };

  if (!visible) return null;

  return (
    <button
      className="ui-button ui-button--secondary app-shell__logout"
      type="button"
      onClick={logout}
      disabled={busy}
    >
      {busy ? 'Signing out…' : 'Sign out'}
    </button>
  );
}
