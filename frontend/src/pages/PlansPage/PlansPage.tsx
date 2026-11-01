import { Alert, Button, Space } from 'antd';
import { Link } from 'react-router-dom';
import SubscriptionPlans from '../../features/profile/components/SubscriptionPlans/SubscriptionPlans';
import { useGenerationUsage } from '../../features/outfit-generation/hooks/useGenerationUsage';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';
import AppBottomNav from '../../shared/ui/AppBottomNav/AppBottomNav';
import styles from './PlansPage.module.css';

function PlansPage() {
  const { usage, error, loading, reload } = useGenerationUsage();
  return (
    <div className={styles.page}>
      <AppHeader title="Тарифы" showBack />
      <main className={styles.content}>
        <Space orientation="vertical" size={24} style={{ width: '100%' }}>
          {usage?.exhausted && (
            <Alert type="warning" showIcon title="Бесплатные подборы закончились"
              description={'Вы использовали ' + usage.used + ' из ' + usage.limit
                + ' бесплатных подборов. Для нового подбора нужен платный тариф. '
                + 'Если текущий подбор завершится ошибкой, он не будет учтён в лимите.'} />
          )}
          {error && <Alert type="error" title="Не удалось проверить лимит"
            action={<Button onClick={() => void reload()}>Повторить</Button>} />}
          <SubscriptionPlans />
          <Alert type="info" showIcon title="Подключение Pro пока недоступно"
            description="Оплата ещё не подключена. Вы можете просматривать ранее созданные образы." />
          {!loading && !error && usage && !usage.exhausted && (
            <Link to="/outfit-generation">Начать подбор</Link>
          )}
          <Link to="/outfits">Мои образы</Link>
        </Space>
      </main>
      <AppBottomNav />
    </div>
  );
}
export default PlansPage;
