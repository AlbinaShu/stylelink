import axios from 'axios';

import {
  ACCESS_TOKEN_KEY,
  useAuthStore,
} from '../../features/auth/model/auth.store';

const API_URL = import.meta.env.VITE_API_URL ?? '';

const http = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

const PUBLIC_AUTH_ENDPOINTS = [
  '/api/v1/auth/email/request-code',
  '/api/v1/auth/email/verify',
  '/api/v1/auth/login',
  '/api/v1/auth/register',
  '/api/v1/auth/password-reset/request-code',
  '/api/v1/auth/password-reset/verify',
  '/api/v1/auth/password-reset/confirm',
];

const isPublicAuthRequest = (url?: string): boolean => {
  if (!url) {
    return false;
  }

  return PUBLIC_AUTH_ENDPOINTS.some((endpoint) =>
    url.includes(endpoint),
  );
};

http.interceptors.request.use(
  (config) => {
    if (isPublicAuthRequest(config.url)) {
      return config;
    }

    const accessToken = localStorage.getItem(
      ACCESS_TOKEN_KEY,
    );

    if (accessToken) {
      config.headers.Authorization = `Bearer ${accessToken}`;
    }

    return config;
  },
  (error) => {
    return Promise.reject(error);
  },
);

http.interceptors.response.use(
  (response) => response,

  (error) => {
    const status = error.response?.status;
    const requestUrl = error.config?.url;

    if (
      status === 401 &&
      !isPublicAuthRequest(requestUrl)
    ) {
      useAuthStore.getState().clearAuth();

      if (window.location.pathname !== '/auth') {
        window.location.replace('/auth');
      }
    }

    return Promise.reject(error);
  },
);

export default http;
