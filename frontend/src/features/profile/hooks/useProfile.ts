import { useProfileStore } from '../model/profile.store';
import {
  getCurrentUser,
  getProfile,
  updateCurrentUser as updateCurrentUserApi,
  updateProfile as updateProfileApi,
} from '../api/profile.api';
import type { IUpdateProfileRequest } from '../types';

export function useProfile() {
  const {
    user,
    profile,
    isLoading,
    setUser,
    setProfile,
    setLoading,
    clearProfile,
  } = useProfileStore();

  const loadProfile = async () => {
    try {
      setLoading(true);

      const [user, profile] = await Promise.all([
        getCurrentUser(),
        getProfile(),
      ]);

      setUser(user);
      setProfile(profile);
    } finally {
      setLoading(false);
    }
  };

  const updateCurrentUser = async (name: string) => {
    const response = await updateCurrentUserApi(name);

    setUser(response);

    return response;
  };

  const updateProfile = async (payload: IUpdateProfileRequest) => {
    const response = await updateProfileApi(payload);

    setProfile(response);

    return response;
  };

  return {
    user,
    profile,
    isLoading,

    loadProfile,
    updateCurrentUser,
    updateProfile,
    clearProfile,
  };
}