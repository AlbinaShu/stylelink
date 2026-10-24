import {
  HeartOutlined,
  HomeOutlined,
  PlusOutlined,
  SkinOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Button, message } from 'antd';
import type { ReactNode } from 'react';
import {
  useLocation,
  useNavigate,
} from 'react-router-dom';

import styles from './AppBottomNav.module.css';

interface IAppBottomNavItem {
  key: string;
  label: string;
  path: string;
  icon: ReactNode;
  isCreate?: boolean;
}

const items: IAppBottomNavItem[] = [
  {
    key: 'home',
    label: 'Главная',
    path: '/main',
    icon: <HomeOutlined />,
  },
  {
    key: 'outfits',
    label: 'Образы',
    path: '/outfits',
    icon: <SkinOutlined />,
  },
  {
    key: 'create',
    label: 'Подбор',
    path: '/outfit-generation',
    icon: <PlusOutlined />,
    isCreate: true,
  },
  {
    key: 'favorites',
    label: 'Избранное',
    path: '/favorites',
    icon: <HeartOutlined />,
  },
  {
    key: 'profile',
    label: 'Профиль',
    path: '/profile',
    icon: <UserOutlined />,
  },
];


function AppBottomNav() {
  const navigate = useNavigate();
  const location = useLocation();

  const handleItemClick = (item: IAppBottomNavItem) => {
    if (item.key === 'favorites') {
      void message.open({
        type: 'info',
        content: 'Избранное скоро появится. Мы уже работаем над этой функцией.',
        duration: 3,
        icon: <HeartOutlined style={{ color: 'var(--primary)' }} />,
      });
      return;
    }

    navigate(item.path);
  };

  const isActive = (path: string) => {
    return (
      location.pathname === path ||
      location.pathname.startsWith(`${path}/`)
    );
  };

  return (
    <nav className={styles.nav}>
      <div className={styles.content}>
        {items.map((item) => {
          const active = isActive(item.path);

          return (
            <Button
              key={item.key}
              type="text"
              className={[
                styles.item,
                active ? styles.active : '',
                item.isCreate ? styles.createItem : '',
              ]
                .filter(Boolean)
                .join(' ')}
              onClick={() => handleItemClick(item)}
            >
              <span
                className={
                  item.isCreate
                    ? styles.createIcon
                    : styles.icon
                }
              >
                {item.icon}
              </span>

              <span className={styles.label}>
                {item.label}
              </span>
            </Button>
          );
        })}
      </div>
    </nav>
  );
}

export default AppBottomNav;