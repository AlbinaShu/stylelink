import GenerationForm from '../../features/outfit-generation/components/GenerationForm/GenerationForm';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';

import styles from './OutfitGenerationPage.module.css';

function OutfitGenerationPage() {
  return (
    <div className={styles.page}>
      <AppHeader
        title="Подобрать образы"
        showBack
      />

      <main className={styles.content}>
        <GenerationForm />
      </main>
    </div>
  );
}

export default OutfitGenerationPage;