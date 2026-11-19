import { useState } from 'react';
import { Form, Input, message } from 'antd';
import Button from '../../../../shared/ui/Button/Button';
import { useAuth } from '../../hooks/useAuth';
import styles from './ForgotPassword.module.css';
import { useLanguage } from '../../../../shared/i18n/LanguageContext';

type Step = 'email' | 'code' | 'password';

function ForgotPassword({ onBack }: { onBack: () => void }) {
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const { requestPasswordResetCode, verifyPasswordResetCode, confirmPasswordReset } = useAuth();
  const { t } = useLanguage();

  const requestCode = async (values: { email: string }) => {
    try {
      setLoading(true);
      await requestPasswordResetCode(values.email);
      setEmail(values.email);
      setStep('code');
      message.success(t('Если такой аккаунт существует, код отправлен на почту'));
    } catch (error) {
      message.error(error instanceof Error ? t(error.message) : t('Не удалось отправить код'));
    } finally {
      setLoading(false);
    }
  };

  const verifyCode = async (values: { code: string }) => {
    try {
      setLoading(true);
      await verifyPasswordResetCode(email, values.code);
      setCode(values.code);
      setStep('password');
    } catch (error) {
      message.error(error instanceof Error ? t(error.message) : t('Неверный код'));
    } finally {
      setLoading(false);
    }
  };

  const resetPassword = async (values: { password: string; confirmPassword: string }) => {
    try {
      setLoading(true);
      await confirmPasswordReset(email, code, values.password);
      message.success(t('Пароль успешно изменён'));
      onBack();
    } catch (error) {
      message.error(error instanceof Error ? t(error.message) : t('Не удалось изменить пароль'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.root}>
      <h1>{t('Восстановление пароля')}</h1>

      {step === 'email' && (
        <>
          <p>{t('Введите email аккаунта. Мы отправим код для сброса пароля.')}</p>
          <Form layout="vertical" requiredMark={false} onFinish={requestCode} className={styles.form}>
            <Form.Item name="email" rules={[{ required: true, message: t('Введите email') }, { type: 'email', message: t('Введите корректный email') }]}>
              <Input placeholder="email@example.com" size="large" />
            </Form.Item>
            <Button title={t('Получить код')} htmlType="submit" isLoading={loading} block />
          </Form>
        </>
      )}

      {step === 'code' && (
        <>
          <p>{t('Введите шестизначный код, отправленный на {email}.', { email })}</p>
          <Form layout="vertical" requiredMark={false} onFinish={verifyCode} className={styles.form}>
            <Form.Item name="code" rules={[{ required: true, message: t('Введите код') }, { len: 6, message: t('Код должен содержать 6 символов') }]}>
              <Input inputMode="numeric" maxLength={6} placeholder="000000" size="large" />
            </Form.Item>
            <Button title={t('Проверить код')} htmlType="submit" isLoading={loading} block />
          </Form>
        </>
      )}

      {step === 'password' && (
        <>
          <p>{t('Задайте новый пароль.')}</p>
          <Form layout="vertical" requiredMark={false} onFinish={resetPassword} className={styles.form}>
            <Form.Item name="password" rules={[{ required: true, message: t('Введите новый пароль') }, { min: 6, message: t('Минимум 6 символов') }]}>
              <Input.Password placeholder={t('Новый пароль')} size="large" />
            </Form.Item>
            <Form.Item
              name="confirmPassword"
              dependencies={['password']}
              rules={[
                { required: true, message: t('Повторите пароль') },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    return !value || getFieldValue('password') === value
                      ? Promise.resolve()
                      : Promise.reject(new Error(t('Пароли не совпадают')));
                  },
                }),
              ]}
            >
              <Input.Password placeholder={t('Повторите пароль')} size="large" />
            </Form.Item>
            <Button title={t('Сохранить новый пароль')} htmlType="submit" isLoading={loading} block />
          </Form>
        </>
      )}

      <button type="button" className={styles.back} onClick={onBack}>{t('Вернуться ко входу')}</button>
    </div>
  );
}

export default ForgotPassword;
