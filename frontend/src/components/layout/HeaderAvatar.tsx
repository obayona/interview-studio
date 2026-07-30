import { useCallback, useEffect, useState } from 'react';
import { profileApi } from '../../services/profile-api';
import type { DeveloperProfile } from '../../types/profile';
import { Icon } from '../ui/Icon';

const PROFILE_UPDATED_EVENT = 'interview-studio:profile-updated';

export function announceProfileUpdate(profile: DeveloperProfile) {
  window.dispatchEvent(
    new CustomEvent<DeveloperProfile>(PROFILE_UPDATED_EVENT, {
      detail: profile,
    }),
  );
}

export function HeaderAvatar() {
  const [profile, setProfile] = useState<DeveloperProfile>();

  const load = useCallback(async () => {
    try {
      setProfile(await profileApi.get());
    } catch {
      setProfile(undefined);
    }
  }, []);

  useEffect(() => {
    const update = (event: Event) =>
      setProfile((event as CustomEvent<DeveloperProfile>).detail);
    void load();
    window.addEventListener(PROFILE_UPDATED_EVENT, update);
    document.addEventListener('astro:page-load', load);
    return () => {
      window.removeEventListener(PROFILE_UPDATED_EVENT, update);
      document.removeEventListener('astro:page-load', load);
    };
  }, [load]);

  return (
    <a className="app-shell__avatar" href="/profile" aria-label="Open profile">
      {profile?.avatar_url ? (
        <img
          src={`${profile.avatar_url}?v=${encodeURIComponent(profile.updated_at)}`}
          alt=""
        />
      ) : (
        <Icon name="user" />
      )}
    </a>
  );
}
