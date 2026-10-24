import {
  ArrowRightOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import {
  Button,
  Card,
  Flex,
  Typography,
} from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import GenerationHistory from '../../features/outfit-generation/components/GenerationHistory/GenerationHistory';
import { useProfile } from '../../features/profile/hooks/useProfile';
import AppBottomNav from '../../shared/ui/AppBottomNav/AppBottomNav';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';

import firstGenerationFlatlay from '../../assets/images/first-generation-flatlay.png';
import styles from './MainPage.module.css';

const { Title, Text } = Typography;

function MainHistory({
  onCreate,
}: {
  onCreate: () => void;
}) {
  const [isEmpty, setIsEmpty] = useState(false);

  if (isEmpty) {
    return (
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
          <img
            src={firstGenerationFlatlay}
            alt="Подбор образа AI-StyleLink"
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
            После первого подбора здесь появится история ваших образов
          </Text>

          <Button
            type="primary"
            icon={<ArrowRightOutlined />}
            iconPosition="end"
            onClick={onCreate}
            className={styles.startButton}
          >
            Начать подбор
          </Button>
        </Flex>
      </Card>
    );
  }

  return (
    <GenerationHistory
      limit={3}
      onEmpty={() => setIsEmpty(true)}
    />
  );
}

function MainPage() {
  const navigate = useNavigate();
  const { user, loadProfile, isLoading } = useProfile();

  useEffect(() => {
    if (!user) {
      void loadProfile();
    }
  }, [user]);

  const userName = user?.name?.trim() || 'Пользователь';
  const hour = new Date().getHours();

  const greeting =
    hour >= 5 && hour < 12
      ? 'Доброе утро'
      : hour >= 12 && hour < 18
        ? 'Добрый день'
        : hour >= 18 && hour < 23
          ? 'Добрый вечер'
          : 'Доброй ночи';

  const handleCreate = () => {
    navigate('/outfit-generation');
  };

  return (
    <div className={styles.page}>
      <AppHeader showProfile />

      <main className={styles.content}>
        <section className={styles.welcome}>
          <Text className={styles.greeting}>
            {greeting},
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
                    До 5 образов из Яндекс Маркета
                  </Text>
                </div>

                <span className={styles.plusButton}>
                  <PlusOutlined />
                </span>
              </div>
            </div>
          </button>
        </Card>

        <MainHistory
          onCreate={handleCreate}
        />
      </main>

      <AppBottomNav />
    </div>
  );
}

export default MainPage;
