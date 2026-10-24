import { Button, Spin } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';
import { useEffect } from 'react';

import { useAuth } from '../../features/auth/hooks/useAuth';
import BodyParameters from '../../features/profile/components/BodyParameters/BodyParameters';
import ProfileMenu from '../../features/profile/components/ProfileMenu/ProfileMenu';
import UserCard from '../../features/profile/components/UserCard/UserCard';
import { useProfile } from '../../features/profile/hooks/useProfile';
import SubscriptionPlans from '../../features/profile/components/SubscriptionPlans/SubscriptionPlans';
import UsageLimit from '../../features/profile/components/UsageLimit/UsageLimit';

import AppBottomNav from '../../shared/ui/AppBottomNav/AppBottomNav';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';

import styles from './ProfilePage.module.css';

function ProfilePage() {
  const { logout } = useAuth();

  const {
    user,
    profile,
    isLoading,
    loadProfile,
    clearProfile,
  } = useProfile();

  useEffect(() => {
    if (!user) {
      void loadProfile();
    }
  }, [user]);

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      clearProfile();
    }
  };

  return (
    <div className={styles.page}>
      <AppHeader
        title="Профиль"
        showBack
      />

      <main className={styles.content}>
        {isLoading && !user ? (
          <div className={styles.loading}>
            <Spin />
          </div>
        ) : (
          <>
            <UserCard user={user!} />

            <SubscriptionPlans />

            <UsageLimit />

            <BodyParameters profile={profile!} />

            <ProfileMenu />

            <Button
              type="text"
              icon={<LogoutOutlined />}
              className={styles.logoutButton}
              onClick={handleLogout}
            >
              Выйти из аккаунта
            </Button>
          </>
        )}
      </main>

      <AppBottomNav />
    </div>
  );
}

export default ProfilePage;