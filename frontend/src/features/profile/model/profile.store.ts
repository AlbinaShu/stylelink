import { create } from 'zustand';
import type { IProfile, IUser } from '../types';

interface IProfileState {
  user: IUser | null;
  profile: IProfile | null;
  isLoading: boolean;

  setUser: (user: IUser | null) => void;
  setProfile: (profile: IProfile | null) => void;
  setLoading: (value: boolean) => void;
  clearProfile: () => void;
}

export const useProfileStore = create<IProfileState>((set) => ({
  user: null,
  profile: null,
  isLoading: false,

  setUser: (user) => {
    set({ user });
  },

  setProfile: (profile) => {
    set({ profile });
  },

  setLoading: (value) => {
    set({ isLoading: value });
  },

  clearProfile: () => {
    set({
      user: null,
      profile: null,
      isLoading: false,
    });
  },
}));