import type { ReactNode } from 'react';

import { Button, Card, List } from 'antd';
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