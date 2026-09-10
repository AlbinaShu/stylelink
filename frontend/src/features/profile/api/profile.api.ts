import http from '../../../shared/api/http-client';
import type {
  IUser,
  IProfile,
  IUpdateProfileRequest,
} from '../types';

export async function getCurrentUser(): Promise<IUser> {
  const { data } = await http.get<IUser>('/api/v1/users/current_user');

  return data;
}

export async function updateCurrentUser(name: string): Promise<IUser> {
  const { data } = await http.patch<IUser>('/api/v1/users/current', { name });

  return data;
}

export async function getProfile(): Promise<IProfile> {
  const { data } = await http.get<IProfile>('/api/v1/profile');

  return data;
}

export async function updateProfile(payload: IUpdateProfileRequest): Promise<IProfile> {
  const { data } = await http.put<IProfile>('/api/v1/profile', payload);

  return data;
}
