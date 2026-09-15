import { useState, type ReactNode } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { ArrowLeftOutlined } from '@ant-design/icons';
import Brand from '../../shared/ui/Brand/Brand';
import LoginForm from '../../features/auth/components/LoginForm/LoginForm';
import RegisterForm from '../../features/auth/components/RegisterForm/RegisterForm';
import OtpStep from '../../features/auth/components/OtpStep/OtpStep';
import NameStep from '../../features/auth/components/NameStep/NameStep';
import ForgotPassword from '../../features/auth/components/ForgotPassword/ForgotPassword';
import { useAuth } from '../../features/auth/hooks/useAuth';
import type {
  AuthMode,
  AuthStep,
  IAuthCredentials,
} from '../../features/auth/types';
import { useProfile } from '../../features/profile/hooks/useProfile';
import styles from './AuthPage.module.css';

interface IAuthShellProps {
  children: ReactNode;
  onBack: () => void;
  progress?: number;
}

function AuthShell({
  children,
  onBack,
  progress,
}: IAuthShellProps) {
  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <button
            type="button"
            className={styles.back}
            onClick={onBack}
            aria-label="Назад"
          >
            <ArrowLeftOutlined />
          </button>

          <Brand />

          {progress && (
            <div className={styles.progress}>
              {[1, 2, 3].map((item) => (
                <span
                  key={item}
                  className={
                    item <= progress ? styles.active : ''
                  }
                />
              ))}
            </div>
          )}
        </div>
      </header>

      <main className={styles.content}>
        <div className={styles.container}>{children}</div>
      </main>
    </div>
  );
}

function AuthPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const {
    register,
    setRegistrationInProgress,
  } = useAuth();
  const { updateCurrentUser } = useProfile();

  const initialMode: AuthMode =
    searchParams.get('mode') === 'register'
      ? 'register'
      : 'login';

  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [step, setStep] = useState<AuthStep>('credentials');
  const [credentials, setCredentials] =
    useState<IAuthCredentials | null>(null);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [forgotPassword, setForgotPassword] = useState(false);
  const [nameLoading, setNameLoading] = useState(false);

  const goLogin = () => {
    setMode('login');
    setStep('credentials');
    setForgotPassword(false);
  };

  const goRegister = () => {
    setMode('register');
    setStep('credentials');
    setForgotPassword(false);
  };

  const startRegistrationVerification = (
    values: IAuthCredentials,
  ) => {
    setCredentials(values);
    setEmail(values.email);
    setStep('verification');
  };

  const back = () => {
    if (forgotPassword) {
      setForgotPassword(false);
      return;
    }

    if (step === 'verification') {
      setStep('credentials');
      return;
    }

    if (step === 'name') {
      setStep('verification');
      return;
    }

    navigate('/');
  };

  const handleVerificationComplete = async () => {
    if (!credentials) {
      return;
    }

    try {
      setRegistrationInProgress(true);
      await register(credentials);
      setStep('name');
    } catch (error) {
      setRegistrationInProgress(false);
      throw error;
    }
  };

  const finishRegistration = async () => {
    const trimmedName = name.trim();

    if (!trimmedName) {
      return;
    }

    try {
      setNameLoading(true);

      await updateCurrentUser(trimmedName);

      setRegistrationInProgress(false);
      navigate('/main', { replace: true });
    } finally {
      setNameLoading(false);
    }
  };

  const skipRegistrationName = () => {
    setRegistrationInProgress(false);
    navigate('/main', { replace: true });
  };

  if (forgotPassword) {
    return (
      <AuthShell onBack={back}>
        <ForgotPassword
          onBack={() => setForgotPassword(false)}
        />
      </AuthShell>
    );
  }

  if (step === 'verification') {
    return (
      <AuthShell onBack={back}>
        <OtpStep
          email={email}
          onBack={back}
          onVerified={handleVerificationComplete}
        />
      </AuthShell>
    );
  }

  if (step === 'name') {
    return (
      <AuthShell onBack={back} progress={3}>
        <NameStep
          name={name}
          loading={nameLoading}
          onNameChange={setName}
          onComplete={finishRegistration}
          onSkip={skipRegistrationName}
        />
      </AuthShell>
    );
  }

  if (mode === 'login') {
    return (
      <AuthShell onBack={() => navigate('/')}>
        <div className={styles.heading}>
          <h1>Добро пожаловать</h1>
          <p>Войдите, чтобы продолжить подбор</p>
        </div>

        <LoginForm
          onLoggedIn={() =>
            navigate('/main', { replace: true })
          }
          onRegister={goRegister}
          onForgotPassword={() => setForgotPassword(true)}
        />
      </AuthShell>
    );
  }

  return (
    <AuthShell
      onBack={() => navigate('/')}
      progress={1}
    >
      <div className={styles.heading}>
        <h1>Создать аккаунт</h1>
        <p>Зарегистрируйтесь, чтобы сохранять образы</p>
      </div>

      <RegisterForm
        onNeedVerification={startRegistrationVerification}
        onLogin={goLogin}
      />
    </AuthShell>
  );
}

export default AuthPage;
