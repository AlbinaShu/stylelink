import { UserOutlined } from '@ant-design/icons';
import Button from '../../../../shared/ui/Button/Button';
import styles from './NameStep.module.css';

interface INameStepProps {
  name: string;
  loading: boolean;
  onNameChange: (value: string) => void;
  onComplete: () => void;
  onSkip: () => void;
}

function NameStep({
  name,
  loading,
  onNameChange,
  onComplete,
  onSkip,
}: INameStepProps) {
  return (
    <div className={styles.root}>
      <div className={styles.icon} aria-hidden="true">
        <UserOutlined />
      </div>

      <h1>Как вас зовут?</h1>
      <p>Будем обращаться к вам по имени при подборе образов</p>

      <input
        className={styles.input}
        value={name}
        onChange={(event) => onNameChange(event.target.value)}
        placeholder="Введите ваше имя"
      />

      <Button
        title="Начать подбор образов"
        onClick={onComplete}
        isDisabled={!name.trim()}
        isLoading={loading}
        block
      />

      <button
        type="button"
        className={styles.skip}
        disabled={loading}
        onClick={onSkip}
      >
        Пропустить
      </button>
    </div>
  );
}

export default NameStep;
