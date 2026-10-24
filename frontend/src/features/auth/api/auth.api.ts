import http from '../../../shared/api/http-client';
import type {
  IAuthCredentials,
  IIdentifyResponse,
  ITokenResponse,
} from '../types';

export async function identifyUser(email: string): Promise<IIdentifyResponse> {
  const { data } = await http.post<IIdentifyResponse>('/api/v1/auth/identify', {
    identifier: email,
  });

  return data;
}

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

export async function requestPasswordResetCode(email: string): Promise<void> {
  await http.post('/api/v1/auth/password-reset/request-code', { email });
}

export async function verifyPasswordResetCode(email: string, code: string): Promise<void> {
  await http.post('/api/v1/auth/password-reset/verify', { email, code });
}

export async function confirmPasswordReset(
  email: string,
  code: string,
  newPassword: string,
): Promise<void> {
  await http.post('/api/v1/auth/password-reset/confirm', {
    email,
    code,
    new_password: newPassword,
  });
}

export async function logout(): Promise<void> {
  await http.post('/api/v1/auth/logout');
}
