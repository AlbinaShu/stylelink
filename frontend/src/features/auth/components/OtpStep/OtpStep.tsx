import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { message } from 'antd';
import { SafetyOutlined } from '@ant-design/icons';
import Button from '../../../../shared/ui/Button/Button';
import { maskEmail } from '../../../../shared/utils/mask-email';
import { useAuth } from '../../hooks/useAuth';
import styles from './OtpStep.module.css';
import { useLanguage } from '../../../../shared/i18n/LanguageContext';

interface IOtpStepProps {
  email: string;
  onBack: () => void;
  onVerified: () => void | Promise<void>;
}

const LENGTH = 6;
const RESEND_SECONDS = 60;

function OtpStep({
  email,
  onBack,
  onVerified,
}: IOtpStepProps) {
  const [code, setCode] = useState<string[]>(Array(LENGTH).fill(''));
  const [loading, setLoading] = useState(false);
  const [seconds, setSeconds] = useState(RESEND_SECONDS);
  const refs = useRef<Array<HTMLInputElement | null>>([]);
  const { requestCode, verifyCode } = useAuth();
  const { t } = useLanguage();

  useEffect(() => {
    if (seconds <= 0) return;

    const timer = window.setInterval(() => {
      setSeconds((value) => value - 1);
    }, 1000);

    return () => window.clearInterval(timer);
  }, [seconds]);

  useEffect(() => {
    refs.current[0]?.focus();
  }, []);

  const change = (index: number, value: string) => {
    const digit = value.replace(/\D/g, '').slice(-1);
    const next = [...code];
    next[index] = digit;
    setCode(next);

    if (digit && index < LENGTH - 1) {
      refs.current[index + 1]?.focus();
    }
  };

  const keyDown = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Backspace' && !code[index] && index > 0) {
      refs.current[index - 1]?.focus();
    }
  };

  const verify = async () => {
    const value = code.join('');

    if (value.length !== LENGTH) return;

    try {
      setLoading(true);
      await verifyCode(email, value);
    } catch (error) {
      message.error(
        error instanceof Error
          ? t(error.message)
          : t('Неверный код'),
      );

      return;
    }

    try {
      await onVerified();
    } catch (error) {
      message.error(
        error instanceof Error
          ? t(error.message)
          : t('Не удалось завершить регистрацию'),
      );
    } finally {
      setLoading(false);
    }
  };

  const resend = async () => {
    if (seconds > 0) return;

    try {
      await requestCode(email);
      setSeconds(RESEND_SECONDS);
      message.success(t('Код отправлен повторно'));
    } catch (error) {
      message.error(
        error instanceof Error
          ? t(error.message)
          : t('Не удалось отправить код'),
      );
    }
  };

  return (
    <div className={styles.root}>
      <div className={styles.icon} aria-hidden="true">
        <SafetyOutlined />
      </div>

      <h1>{t('Подтвердите email')}</h1>

      <p className={styles.description}>
        {t('Код отправлен на')} <strong>{maskEmail(email)}</strong>
      </p>

      <div className={styles.inputs}>
        {code.map((value, index) => (
          <input
            key={index}
            ref={(element) => {
              refs.current[index] = element;
            }}
            value={value}
            inputMode="numeric"
            maxLength={1}
            aria-label={t('Цифра {number}', { number: index + 1 })}
            onChange={(event) => change(index, event.target.value)}
            onKeyDown={(event) => keyDown(index, event)}
          />
        ))}
      </div>

      <Button
        title={t('Подтвердить')}
        onClick={verify}
        isDisabled={code.join('').length !== LENGTH}
        isLoading={loading}
        block
      />

      <button
        type="button"
        className={styles.resend}
        disabled={seconds > 0}
        onClick={resend}
      >
        {t('Отправить код повторно через')} <strong>{seconds}{t('с')}</strong>
      </button>

      <br />

      <button type="button" className={styles.change} onClick={onBack}>
        {t('Изменить email')}
      </button>
    </div>
  );
}

export default OtpStep;
