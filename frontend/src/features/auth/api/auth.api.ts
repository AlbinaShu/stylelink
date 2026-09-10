import http from '../../../shared/api/http-client';
import type {
  IAuthCredentials,
  ITokenResponse,
} from '../types';

export async function requestEmailCode(email: string): Promise<void> {
  await http.post('/api/v1/auth/email/request-code', { email });
}

export async function verifyEmailCode(email: string, code: string): Promise<void> {
  await http.post('/api/v1/auth/email/verify', { email, code });
}

export async function login(credentials: IAuthCredentials): Promise<ITokenResponse> {
  const { data } = await http.post<ITokenResponse>('/api/v1/auth/login', credentials);

  return data;
}

export async function register(credentials: IAuthCredentials): Promise<ITokenResponse> {
  const { data } = await http.post<ITokenResponse>('/api/v1/auth/register', credentials);

  return data;
}

export async function logout(): Promise<void> {
  await http.post('/api/v1/auth/logout');
}