import { ArrowLeftOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import Brand from '../Brand/Brand';
import styles from './AppHeader.module.css';

interface IAppHeaderProps {
  title?: string;
  showBack?: boolean;
  showProfile?: boolean;
}

function AppHeader({
  title,
  showBack = false,
  showProfile = false,
}: IAppHeaderProps) {
  const navigate = useNavigate();

  if (showBack) {
    return (
      <header className={styles.header}>
        <div className={styles.inner}>
          <button
            type="button"
            className={styles.back}
            onClick={() => navigate('/main')}
            aria-label="Назад"
          >
            <ArrowLeftOutlined />
          </button>

          <span className={styles.title}>{title}</span>
        </div>
      </header>
    );
  }

  return (
    <header className={styles.header}>
      <div className={styles.inner}>
        <Link to="/main" className={styles.brand}>
          <Brand />
        </Link>

        {showProfile && (
          <Link
            to="/profile"
            className={styles.profileButton}
            aria-label="Профиль"
          >
            П
          </Link>
        )}
      </div>
    </header>
  );
}

export default AppHeader;
