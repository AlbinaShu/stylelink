import { Alert, Button, Spin } from 'antd';
import { Navigate } from 'react-router-dom';
import { useGenerationUsage } from '../../features/outfit-generation/hooks/useGenerationUsage';
import GenerationForm from '../../features/outfit-generation/components/GenerationForm/GenerationForm';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';

import styles from './OutfitGenerationPage.module.css';

function OutfitGenerationPage() {
  const { usage, error, loading, reload } = useGenerationUsage();
  if (usage?.exhausted) return <Navigate to="/plans" replace />;
  return (
    <div className={styles.page}>
      <AppHeader
        title="Подобрать образы"
        showBack
      />

      <main className={styles.content}>
        {loading ? <Spin /> : error ? (
          <Alert type="error" showIcon title="Не удалось проверить доступные подборы"
            action={<Button onClick={() => void reload()}>Повторить</Button>} />
        ) : <GenerationForm />}
      </main>
    </div>
  );
}

export default OutfitGenerationPage;