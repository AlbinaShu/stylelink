import {
  ArrowRightOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import {
  Button,
  Card,
  Flex,
  Image,
  Typography,
} from 'antd';
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { useProfile } from '../../features/profile/hooks/useProfile';
import AppBottomNav from '../../shared/ui/AppBottomNav/AppBottomNav';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';

import styles from './MainPage.module.css';

const { Title, Text } = Typography;

function MainPage() {
  const navigate = useNavigate();
  const { user, loadProfile, isLoading } = useProfile();

  useEffect(() => {
    if (!user) {
      void loadProfile();
    }
  }, [user]);

  const userName = user?.name?.trim() || 'Пользователь';

  const handleCreate = () => {
    navigate('/outfit-generation');
  };

  return (
    <div className={styles.page}>
      <AppHeader showProfile />

      <main className={styles.content}>
        <section className={styles.welcome}>
          <Text className={styles.greeting}>
            Добрый вечер,
          </Text>

          <Title level={2} className={styles.title}>
            {isLoading ? 'Пользователь' : userName} 👋
          </Title>
        </section>

        <Card
          bordered={false}
          className={styles.hero}
          styles={{
            body: {
              padding: 0,
              height: '100%',
            },
          }}
        >
          <button
            type="button"
            className={styles.heroAction}
            onClick={handleCreate}
          >
            <div className={styles.heroOverlay} />

            <div className={styles.heroContent}>
              <div className={styles.brand}>
                <span className={styles.brandIcon}>✧</span>
                AI-StyleLink
              </div>

              <div className={styles.heroBottom}>
                <div>
                  <Title level={4} className={styles.heroTitle}>
                    Новый подбор образов
                  </Title>

                  <Text className={styles.heroDescription}>
                    5 образов из Wildberries за 10 минут
                  </Text>
                </div>

                <span className={styles.plusButton}>
                  <PlusOutlined />
                </span>
              </div>
            </div>
          </button>
        </Card>

        <Card
          bordered
          className={styles.startCard}
          styles={{
            body: {
              padding: 0,
            },
          }}
        >
          <div className={styles.preview}>
            <Image
              preview={false}
              src="/images/yellow-woman.webp"
              alt=""
              className={styles.previewImage}
            />

            <Image
              preview={false}
              src="/images/yellow-woman2.webp"
              alt=""
              className={styles.previewImage}
            />

            <Image
              preview={false}
              src="/images/green-woman.webp"
              alt=""
              className={styles.previewImage}
            />
          </div>

          <Flex
            vertical
            align="center"
            className={styles.startContent}
          >
            <Title level={5} className={styles.startTitle}>
              Начните первый подбор
            </Title>

            <Text className={styles.startDescription}>
              После подбора здесь появится история запросов и избранные образы
            </Text>

            <Button
              type="primary"
              icon={<ArrowRightOutlined />}
              iconPosition="end"
              onClick={handleCreate}
              className={styles.startButton}
            >
              Начать подбор
            </Button>
          </Flex>
        </Card>
      </main>

      <AppBottomNav />
    </div>
  );
}

export default MainPage;