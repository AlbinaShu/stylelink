import {
  HeartOutlined,
  PlusOutlined,
  SkinOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Button } from 'antd';
import type { ReactNode } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

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
    key: 'outfits',
    label: 'Образы',
    path: '/main',
    icon: <SkinOutlined />,
  },
  {
    key: 'favorites',
    label: 'Избранное',
    path: '/favorites',
    icon: <HeartOutlined />,
  },
  {
    key: 'create',
    label: 'Подбор',
    path: '/create',
    icon: <PlusOutlined />,
    isCreate: true,
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

  const isActive = (path: string) => {
    return location.pathname === path;
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
              className={`${styles.item} ${
                active ? styles.active : ''
              } ${item.isCreate ? styles.createItem : ''}`}
              onClick={() => navigate(item.path)}
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