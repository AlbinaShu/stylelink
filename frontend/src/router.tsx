import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import LandingPage from './pages/LandingPage/LandingPage';
import AuthPage from './pages/AuthPage/AuthPage';
import MainPage from './pages/MainPage/MainPage';
import ProfilePage from './pages/ProfilePage/ProfilePage';
import OutfitGenerationPage from './pages/OutfitGenerationPage/OutfitGenerationPage';
import GenerationLoadingPage from './pages/GenerationLoadingPage/GenerationLoadingPage';
import GenerationResultsPage from './pages/GenerationResultsPage/GenerationResultsPage';
import { useAuth } from './features/auth/hooks/useAuth';
import SurveyPopup from './features/survey/components/SurveyPopup/SurveyPopup';
import SurveyEmailPage from './pages/SurveyEmailPage/SurveyEmailPage';
import { useSessionLifecycle } from './features/experiment-events/hooks/useSessionLifecycle';

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
  useSessionLifecycle();

  return isLoggedIn
    ? <>
        {children}
        <SurveyPopup />
      </>
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

      <Route path="/survey" element={<SurveyEmailPage />} />

      <Route
        path="/main"
        element={
          <ProtectedRoute>
            <MainPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/outfit-generation"
        element={
          <ProtectedRoute>
            <OutfitGenerationPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/outfit-generation/:generationId/loading"
        element={
          <ProtectedRoute>
            <GenerationLoadingPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/outfit-generation/:generationId/results"
        element={
          <ProtectedRoute>
            <GenerationResultsPage />
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
