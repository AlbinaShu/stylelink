import styles from './ForgotPassword.module.css';

interface IForgotPasswordProps {
  onBack: () => void;
}

function ForgotPassword({ onBack }: IForgotPasswordProps) {
  return (
    <div className={styles.root}>
      <h1>Восстановление пароля</h1>
      <p>
        Функция восстановления пароля будет доступна после подключения
        соответствующего API.
      </p>
      <button type="button" onClick={onBack}>
        Вернуться ко входу
      </button>
    </div>
  );
}

export default ForgotPassword;
