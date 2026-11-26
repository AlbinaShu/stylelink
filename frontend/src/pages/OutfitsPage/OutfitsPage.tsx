import GenerationHistory from '../../features/outfit-generation/components/GenerationHistory/GenerationHistory';
import AppBottomNav from '../../shared/ui/AppBottomNav/AppBottomNav';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';
import { useLanguage } from '../../shared/i18n/LanguageContext';

import styles from './OutfitsPage.module.css';

function OutfitsPage() {
  const { t } = useLanguage();
  return (
    <div className={styles.page}>
      <AppHeader title={t('Образы')} />

      <main className={styles.content}>
        <GenerationHistory showTitle={false} />
      </main>

      <AppBottomNav />
    </div>
  );
}

export default OutfitsPage;
