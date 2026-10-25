import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';

import { Button, Card, List, message } from 'antd';
import {
  HeartOutlined,
  QuestionCircleOutlined,
  RightOutlined,
} from '@ant-design/icons';

import styles from './ProfileMenu.module.css';

interface IProfileMenuItem {
  key: string;
  title: string;
  icon: ReactNode;
}

const items: IProfileMenuItem[] = [
  {
    key: 'favorites',
    title: 'Избранные образы',
    icon: <HeartOutlined />,
  },
  {
    key: 'support',
    title: 'Поддержка',
    icon: <QuestionCircleOutlined />,
  },
];

function ProfileMenu() {
  const navigate = useNavigate();

  const handleClick = (key: string) => {
    if (key === 'favorites') {
      void message.open({
        type: 'info',
        content: 'Избранное скоро появится. Мы уже работаем над этой функцией.',
        duration: 3,
        icon: <HeartOutlined style={{ color: 'var(--primary)' }} />,
      });
      return;
    }

    if (key === 'support') {
      navigate('/support');
    }
  };

  return (
    <Card
      bordered
      className={styles.card}
      styles={{
        body: {
          padding: 0,
        },
      }}
    >
      <List
        dataSource={items}
        split
        renderItem={(item) => (
          <List.Item className={styles.item}>
            <Button
              type="text"
              block
              className={styles.button}
              onClick={() => handleClick(item.key)}
            >
              <span className={styles.label}>
                {item.icon}
                <span>{item.title}</span>
              </span>

              <RightOutlined className={styles.arrow} />
            </Button>
          </List.Item>
        )}
      />
    </Card>
  );
}

export default ProfileMenu;