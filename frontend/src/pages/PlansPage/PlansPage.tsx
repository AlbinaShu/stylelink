import { Alert, Button, Space } from 'antd';
import { Link } from 'react-router-dom';
import SubscriptionPlans from '../../features/profile/components/SubscriptionPlans/SubscriptionPlans';
import { useGenerationUsage } from '../../features/outfit-generation/hooks/useGenerationUsage';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';
import AppBottomNav from '../../shared/ui/AppBottomNav/AppBottomNav';
import { useLanguage } from '../../shared/i18n/LanguageContext';
import styles from './PlansPage.module.css';

function PlansPage() {
  const { usage, error, loading, reload } = useGenerationUsage();
  const { t } = useLanguage();
  return (
    <div className={styles.page}>
      <AppHeader title={t('Тарифы')} showBack />
      <main className={styles.content}>
        <Space orientation="vertical" size={24} style={{ width: '100%' }}>
          {usage?.exhausted && (
            <Alert type="warning" showIcon title={t('Бесплатные подборы закончились')}
              description={t('Вы использовали {used} из {limit} бесплатных подборов. Для нового подбора нужен платный тариф. Если текущий подбор завершится ошибкой, он не будет учтён в лимите.', { used: usage.used, limit: usage.limit })} />
          )}
          {error && <Alert type="error" title={t('Не удалось проверить лимит')}
            action={<Button onClick={() => void reload()}>{t('Повторить')}</Button>} />}
          <SubscriptionPlans />
          <Alert type="info" showIcon title={t('Подключение Pro пока недоступно')}
            description={t('Оплата ещё не подключена. Вы можете просматривать ранее созданные образы.')} />
          {!loading && !error && usage && !usage.exhausted && (
            <Link to="/outfit-generation">{t('Начать подбор')}</Link>
          )}
          <Link to="/outfits">{t('Мои образы')}</Link>
        </Space>
      </main>
      <AppBottomNav />
    </div>
  );
}
export default PlansPage;
