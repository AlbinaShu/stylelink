import { ArrowLeftOutlined } from '@ant-design/icons';
import { Link, useNavigate } from 'react-router-dom';
import Brand from '../Brand/Brand';
import LanguageSwitcher from '../LanguageSwitcher/LanguageSwitcher';
import { useLanguage } from '../../i18n/LanguageContext';
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
  const { t } = useLanguage();

  if (showBack) {
    return (
      <header className={styles.header}>
        <div className={styles.inner}>
          <button
            type="button"
            className={styles.back}
            onClick={() => navigate('/main')}
            aria-label={t('Назад')}
          >
            <ArrowLeftOutlined />
          </button>

          <span className={styles.title}>{title}</span>
          <div className={styles.actions}><LanguageSwitcher /></div>
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

        <div className={styles.actions}>
          <LanguageSwitcher />
          {showProfile && (
            <Link
              to="/profile"
              className={styles.profileButton}
              aria-label={t('Профиль')}
            >
              {t('П')}
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}

export default AppHeader;
