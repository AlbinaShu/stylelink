import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import LandingPage from './pages/LandingPage/LandingPage';
import AuthPage from './pages/AuthPage/AuthPage';
import MainPage from './pages/MainPage/MainPage';
import ProfilePage from './pages/ProfilePage/ProfilePage';
import { useAuth } from './features/auth/hooks/useAuth';

interface IRouteProps {
  children: ReactNode;
}

function GuestRoute({ children }: IRouteProps) {
  const { isLoggedIn, isRegistrationInProgress } = useAuth();

  return isLoggedIn && !isRegistrationInProgress
    ? <Navigate to="/main" replace />
    : children;
}

function ProtectedRoute({ children }: IRouteProps) {
  const { isLoggedIn } = useAuth();

  return isLoggedIn
    ? children
    : <Navigate to="/" replace />;
}

export function AppRouter() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <GuestRoute>
            <LandingPage />
          </GuestRoute>
        }
      />

      <Route
        path="/auth"
        element={
          <GuestRoute>
            <AuthPage />
          </GuestRoute>
        }
      />

      <Route
        path="/main"
        element={
          <ProtectedRoute>
            <MainPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <ProfilePage />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
