import { Avatar, Card, Typography } from 'antd';
import { UserOutlined } from '@ant-design/icons';

import type { IUser } from '../../types';
import styles from './UserCard.module.css';
import { useLanguage } from '../../../../shared/i18n/LanguageContext';

const { Text } = Typography;

interface IUserCardProps {
  user: IUser;
}

function UserCard({
  user,
}: IUserCardProps) {
  const { t } = useLanguage();
  return (
    <Card
      bordered
      className={styles.card}
    >
      <div className={styles.content}>
        <Avatar
          size={50}
          icon={<UserOutlined />}
          className={styles.avatar}
        />

        <div className={styles.info}>
          <Text strong>
            {user?.name || t('Пользователь')}
          </Text>

          <Text type="secondary">
            {user?.email || '—'}
          </Text>
        </div>
      </div>
    </Card>
  );
}

export default UserCard;
