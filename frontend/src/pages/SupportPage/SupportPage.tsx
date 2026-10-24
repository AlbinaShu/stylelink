import {
  MailOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { Button, Card, Typography } from 'antd';

import AppBottomNav from '../../shared/ui/AppBottomNav/AppBottomNav';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';

import styles from './SupportPage.module.css';

const { Title, Text } = Typography;

const SUPPORT_EMAIL = 'aistylelink@gmail.com';

function SupportPage() {
  const handleContactSupport = () => {
    window.location.href =
      `mailto:${SUPPORT_EMAIL}?subject=${encodeURIComponent('Вопрос по AI·StyleLink')}`;
  };

  return (
    <div className={styles.page}>
      <AppHeader title="Поддержка" showBack />

      <main className={styles.content}>
        <Card
          bordered
          className={styles.card}
          styles={{ body: { padding: 0 } }}
        >
          <div className={styles.iconWrapper}>
            <QuestionCircleOutlined className={styles.icon} />
          </div>

          <Title level={3} className={styles.title}>
            Чем мы можем помочь?
          </Title>

          <Text className={styles.description}>
            Если у вас возник вопрос, проблема или предложение по работе
            AI·StyleLink, напишите нам. Мы постараемся ответить как можно скорее.
          </Text>

          <div className={styles.contact}>
            <Text className={styles.contactLabel}>
              Контактная почта
            </Text>

            <a
              href={`mailto:${SUPPORT_EMAIL}`}
              className={styles.email}
            >
              <MailOutlined />
              <span>{SUPPORT_EMAIL}</span>
            </a>
          </div>

          <Button
            type="primary"
            size="large"
            icon={<MailOutlined />}
            onClick={handleContactSupport}
            className={styles.button}
          >
            Написать в поддержку
          </Button>
        </Card>
      </main>

      <AppBottomNav />
    </div>
  );
}

export default SupportPage;
