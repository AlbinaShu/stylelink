export type AuthMode = 'login' | 'register';
export type AuthStep = 'credentials' | 'verification' | 'name';

export interface IAuthCredentials {
  email: string;
  password: string;
}

export interface ITokenResponse {
  access_token: string;
}