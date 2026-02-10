import { useEffect, useState } from 'react';

import { refreshSession } from '../lib/auth';
import { useAuthStore } from '../stores/authStore';

export function useAuth() {
  const user = useAuthStore((s) => s.user);
  const accessToken = useAuthStore((s) => s.accessToken);
  const clear = useAuthStore((s) => s.clear);
  const [isHydrating, setIsHydrating] = useState(true);

  useEffect(() => {
    let mounted = true;

    refreshSession().finally(() => {
      if (mounted) {
        setIsHydrating(false);
      }
    });

    return () => {
      mounted = false;
    };
  }, []);

  return {
    user,
    accessToken,
    isAuthenticated: Boolean(accessToken && user),
    isHydrating,
    clear
  };
}
