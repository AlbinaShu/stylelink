import { useState } from 'react';
import { Checkbox, Form, Input, message } from 'antd';
import { EyeInvisibleOutlined, EyeOutlined } from '@ant-design/icons';
import Button from '../../../../shared/ui/Button/Button';
import { useAuth } from '../../hooks/useAuth';
import styles from './RegisterForm.module.css';
import type { IAuthCredentials } from '../../types';

interface IRegisterFormProps {
  onNeedVerification: (credentials: IAuthCredentials) => void;
  onLogin: () => void;
}

function RegisterForm({
  onNeedVerification,
  onLogin,
}: IRegisterFormProps) {
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm<IAuthCredentials>();
  const { requestCode } = useAuth();

  const submit = async (values: IAuthCredentials) => {
    try {
      setLoading(true);
      await requestCode(values.email);
      onNeedVerification(values);
    } catch (error) {
      message.error(
        error instanceof Error
          ? error.message
          : 'Не удалось отправить код',
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
        rules={[
          { required: true, message: 'Введите пароль' },
          { min: 6, message: 'Минимум 6 символов' },
        ]}
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

      <Form.Item
        name="consent"
        valuePropName="checked"
        rules={[
          {
            validator: (_, value) =>
              value
                ? Promise.resolve()
                : Promise.reject(new Error('Необходимо согласие')),
          },
        ]}
      >
        <Checkbox className={styles.consent}>
          Я согласен(а) с{' '}
          <a href="#" onClick={(event) => event.preventDefault()}>
            обработкой персональных данных
          </a>{' '}
          и{' '}
          <a href="#" onClick={(event) => event.preventDefault()}>
            политикой конфиденциальности
          </a>
        </Checkbox>
      </Form.Item>

      <Button
        title="Продолжить"
        htmlType="submit"
        isLoading={loading}
        block
      />

      <div className={styles.switch}>
        <span>Уже есть аккаунт?</span>{' '}
        <button type="button" onClick={onLogin}>
          Войти
        </button>
      </div>
    </Form>
  );
}

export default RegisterForm;
