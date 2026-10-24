import GenerationHistory from '../../features/outfit-generation/components/GenerationHistory/GenerationHistory';
import AppBottomNav from '../../shared/ui/AppBottomNav/AppBottomNav';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';

import styles from './OutfitsPage.module.css';

function OutfitsPage() {
  return (
    <div className={styles.page}>
      <AppHeader title="Образы" />

      <main className={styles.content}>
        <GenerationHistory showTitle={false} />
      </main>

      <AppBottomNav />
    </div>
  );
}

export default OutfitsPage;
