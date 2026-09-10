import { create } from 'zustand';

interface IAuthState {
  accessToken: string | null;
  isRegistrationInProgress: boolean;

  setRegistrationInProgress: (value: boolean) => void;
  setAuth: (accessToken: string) => void;
  clearAuth: () => void;
}

export const ACCESS_TOKEN_KEY = 'ai-stylelink-access-token';

export const useAuthStore = create<IAuthState>((set) => ({
  accessToken: localStorage.getItem(ACCESS_TOKEN_KEY),
  isRegistrationInProgress: false,

  setAuth: accessToken => {
    localStorage.setItem(
      ACCESS_TOKEN_KEY,
      accessToken,
    );

    set({ accessToken });
  },

  setRegistrationInProgress: (value: boolean) => {
    set({ isRegistrationInProgress: value });
  },

  clearAuth: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);

    set({ accessToken: null });
  },
}));
