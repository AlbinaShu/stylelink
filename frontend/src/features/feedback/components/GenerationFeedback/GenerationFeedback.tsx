import { Alert, Button, Modal, Spin } from 'antd';
import type { ReactNode } from 'react';
import { useGenerationFeedback } from '../../hooks/useGenerationFeedback';
import RatingForm from '../RatingForm/RatingForm';
import styles from './GenerationFeedback.module.css';

interface IGenerationFeedbackProps {
  generationId: string;
  children: ReactNode;
}

export default function GenerationFeedback({ generationId, children }: IGenerationFeedbackProps) {
  const { data, loadError, open, resultsRef, recordView, save, dismiss, retry } = useGenerationFeedback(generationId);

  return (
    <>
      <div ref={resultsRef} aria-hidden="true" style={{ height: 1 }} />
      {children}
      <aside className={styles.panel} aria-label="Оценка результатов и сервиса">
        {loadError ? (
          <Alert type="warning" title="Не удалось загрузить оценки"
            action={<Button onClick={() => { retry(); }}>Повторить</Button>} />
        ) : !data ? <Spin aria-label="Загрузка оценок" /> : (
          <>
            <RatingForm key={generationId + '-selection'} scope="selection" rating={data.selection}
              onVisible={() => recordView('selection')}
              onSave={(score, comment) => save('selection', score, comment, 'inline')} />
            <RatingForm key={generationId + '-service-' + (data.service ? JSON.stringify(data.service) : 'new')}
              scope="service" rating={data.service}
              onVisible={() => recordView('service')}
              onSave={(score, comment) => save('service', score, comment, 'inline')} />
          </>
        )}
      </aside>
      <Modal open={open} title="Поделитесь впечатлением об AI StyleLink" footer={null}
        onCancel={dismiss} destroyOnHidden>
        <p className={styles.description}>Вы уже попробовали несколько подборок. Поделитесь общим впечатлением.</p>
        <RatingForm scope="service" rating={data?.service ?? null}
          onSave={(score, comment) => save('service', score, comment, 'invitation')} />
        <Button type="link" onClick={dismiss}>Позже</Button>
      </Modal>
    </>
  );
}
