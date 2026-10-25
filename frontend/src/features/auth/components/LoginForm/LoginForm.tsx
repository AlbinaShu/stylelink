import { useState } from 'react';
import { Form, Input, message } from 'antd';
import { EyeInvisibleOutlined, EyeOutlined } from '@ant-design/icons';
import Button from '../../../../shared/ui/Button/Button';
import { useAuth } from '../../hooks/useAuth';
import styles from './LoginForm.module.css';
import type { IAuthCredentials } from '../../types';

interface ILoginFormProps {
  onLoggedIn: () => void;
  onRegister: () => void;
  onForgotPassword: () => void;
  onNeedVerification: (values: IAuthCredentials) => void;
}

function LoginForm({
  onLoggedIn,
  onRegister,
  onForgotPassword,
  onNeedVerification,
}: ILoginFormProps) {
  const [form] = Form.useForm<IAuthCredentials>();
  const [loading, setLoading] = useState(false);

  const {
    identify,
    login,
    requestCode,
  } = useAuth();

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
          ? error.message
          : 'Не удалось выполнить вход',
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
          { required: true, message: 'Введите email' },
          { type: 'email', message: 'Введите корректный email' },
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
        rules={[{ required: true, message: 'Введите пароль' }]}
      >
        <Input.Password
          className={styles.input}
          placeholder="Пароль"
          size="large"
          iconRender={(visible) =>
            visible ? <EyeOutlined /> : <EyeInvisibleOutlined />
          }
        />
      </Form.Item>

      <div className={styles.forgot}>
        <button type="button" onClick={onForgotPassword}>
          Забыли пароль?
        </button>
      </div>

      <Button
        title="Войти"
        htmlType="submit"
        isLoading={loading}
        block
      />

      <div className={styles.switch}>
        <span>Нет аккаунта?</span>{' '}
        <button type="button" onClick={onRegister}>
          Зарегистрироваться
        </button>
      </div>
    </Form>
  );
}

export default LoginForm;
