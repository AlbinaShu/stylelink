import { useState } from 'react';
import { Checkbox, Form, Input, message } from 'antd';
import { EyeInvisibleOutlined, EyeOutlined } from '@ant-design/icons';
import Button from '../../../../shared/ui/Button/Button';
import { useAuth } from '../../hooks/useAuth';
import styles from './RegisterForm.module.css';
import type { IAuthCredentials } from '../../types';
import { useLanguage } from '../../../../shared/i18n/LanguageContext';

interface IRegisterFormProps {
  onNeedVerification: (credentials: IAuthCredentials) => void;
  onLoggedIn: () => void;
  onLogin: () => void;
}

function RegisterForm({
  onNeedVerification,
  onLoggedIn,
  onLogin,
}: IRegisterFormProps) {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm<IAuthCredentials>();
  const { identify, login, requestCode } = useAuth();
  const { t } = useLanguage();

  const submit = async (values: IAuthCredentials) => {
    try {
      setLoading(true);

      const identification = await identify(values.email);

      if (identification.exists) {
        await login(values);
        onLoggedIn();
        return;
      }

      await requestCode(values.email);
      onNeedVerification(values);
    } catch (error) {
      message.error(
        error instanceof Error
          ? t(error.message)
          : t('Не удалось продолжить авторизацию'),
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Form
      form={form}
      layout="vertical"
      requiredMark={false}
      onFinish={submit}
      className={styles.form}
    >
      <Form.Item
        name="email"
        rules={[
          { required: true, message: t('Введите email') },
          { type: 'email', message: t('Введите корректный email') },
        ]}
      >
        <Input
          className={styles.input}
          placeholder="email@example.com"
          size="large"
        />
      </Form.Item>

      <Form.Item
        name="password"
        rules={[
          { required: true, message: t('Введите пароль') },
          { min: 6, message: t('Минимум 6 символов') },
        ]}
      >
        <Input.Password
          className={styles.input}
          placeholder={t('Пароль')}
          size="large"
          iconRender={(visible) =>
            visible ? <EyeOutlined /> : <EyeInvisibleOutlined />
          }
        />
      </Form.Item>

      <Form.Item
        name="consent"
        valuePropName="checked"
        rules={[
          {
            validator: (_, value) =>
              value
                ? Promise.resolve()
                : Promise.reject(new Error(t('Необходимо согласие'))),
          },
        ]}
      >
        <Checkbox className={styles.consent}>
          {t('Я согласен(а) с')}{' '}
          <a href="#" onClick={(event) => event.preventDefault()}>
            {t('обработкой персональных данных')}
          </a>{' '}
          {t('и')}{' '}
          <a href="#" onClick={(event) => event.preventDefault()}>
            {t('политикой конфиденциальности')}
          </a>
        </Checkbox>
      </Form.Item>

      <Button
        title={t('Продолжить')}
        htmlType="submit"
        isLoading={loading}
        block
      />

      <div className={styles.switch}>
        <span>{t('Уже есть аккаунт?')}</span>{' '}
        <button type="button" onClick={onLogin}>
          {t('Войти')}
        </button>
      </div>
    </Form>
  );
}

export default RegisterForm;
