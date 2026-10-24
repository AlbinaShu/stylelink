import {
  confirmPasswordReset,
  identifyUser,
  login,
  logout,
  register,
  requestEmailCode,
  requestPasswordResetCode,
  verifyEmailCode,
  verifyPasswordResetCode,
} from '../api/auth.api';
import { useAuthStore } from '../model/auth.store';
import type { IAuthCredentials } from '../types';

export function useAuth() {
  const {
    accessToken,
    setAuth,
    clearAuth,
    isRegistrationInProgress,
    setRegistrationInProgress,
  } = useAuthStore();

  const loginUser = async (credentials: IAuthCredentials) => {
    const response = await login(credentials);
    const token = response.access_token;

    if (token) {
      setAuth(token);
    }

    return response;
  };

  const registerUser = async (credentials: IAuthCredentials) => {
    const response = await register(credentials);
    const token = response.access_token;

    if (token) {
      setAuth(token);
    }

    return response;
  };

  const logoutUser = async () => {
    try {
      await logout();
    } finally {
      clearAuth();
    }
  };

  return {
    accessToken,
    isRegistrationInProgress,
    setRegistrationInProgress,
    isLoggedIn: Boolean(accessToken),
    identify: identifyUser,
    login: loginUser,
    register: registerUser,
    requestCode: requestEmailCode,
    verifyCode: verifyEmailCode,
    requestPasswordResetCode,
    verifyPasswordResetCode,
    confirmPasswordReset,
    logout: logoutUser,
  };
}
