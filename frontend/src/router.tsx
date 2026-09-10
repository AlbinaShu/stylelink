import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import LandingPage from './pages/LandingPage/LandingPage';
import AuthPage from './pages/AuthPage/AuthPage';
import { useAuth } from './features/auth/hooks/useAuth';

interface IRouteProps {
  children: ReactNode;
}

function GuestRoute({ children }: IRouteProps) {
  const { isLoggedIn, isRegistrationInProgress } = useAuth();

  return isLoggedIn && !isRegistrationInProgress ? <Navigate to="/main" replace /> : children;
}

function ProtectedRoute({ children }: IRouteProps) {
  const { isLoggedIn } = useAuth();

  return isLoggedIn ? children : <Navigate to="/" replace />;
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
            <div>основная страница приложения</div>
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
