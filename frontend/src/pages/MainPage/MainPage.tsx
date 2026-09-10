import { ArrowRightOutlined, SkinOutlined } from '@ant-design/icons';
import { useEffect } from 'react';
import { useProfile } from '../../features/profile/hooks/useProfile';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';
import styles from './MainPage.module.css';

function MainPage() {
  const { user, loadProfile, isLoading } = useProfile();

  useEffect(() => {
    if (!user) {
      void loadProfile();
    }
  }, [user, loadProfile]);

  const userName = user?.name?.trim() || 'Пользователь';

  return (
    <div className={styles.page}>
      <AppHeader showProfile />

      <main className={styles.content}>
        <section className={styles.welcome}>
          <p className={styles.greeting}>
            Добро пожаловать,
          </p>

          <h1 className={styles.title}>
            {isLoading ? 'Пользователь' : userName} 👋
          </h1>
        </section>

        <button
          type="button"
          className={styles.newOutfit}
        >
          <div className={styles.newOutfitText}>
            <strong>Новый подбор</strong>
            <span>5 образов за 10 минут</span>
          </div>

          <span className={styles.arrow}>
            <ArrowRightOutlined />
          </span>
        </button>

        <section className={styles.emptyState}>
          <SkinOutlined className={styles.emptyIcon} />

          <p className={styles.emptyTitle}>
            Начните первый подбор
          </p>

          <p className={styles.emptyDescription}>
            После подбора здесь появится история запросов и
            избранные образы
          </p>
        </section>
      </main>
    </div>
  );
}

export default MainPage;