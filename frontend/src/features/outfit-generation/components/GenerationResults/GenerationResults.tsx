import { ExportOutlined } from '@ant-design/icons';
import { Alert, Empty, Image, Typography } from 'antd';

import type { IOutfit } from '../../api/generation.api';
import styles from './GenerationResults.module.css';

const { Text, Title } = Typography;

const fitLabels: Record<string, string> = {
  runs_small: 'Маломерит',
  true_to_size: 'Размер в размер',
  runs_large: 'Большемерит',
};

interface IGenerationResultsProps {
  status: string | null;
  outfits: IOutfit[] | null;
  error: string | null;
}

function GenerationResults({ status, outfits, error }: IGenerationResultsProps) {
  if (error) {
    return <Alert type="error" showIcon message={error} className={styles.notice} />;
  }

  if (!status) {
    return null;
  }

  if (status !== 'completed') {
    return (
      <Alert
        type={status === 'failed' ? 'error' : 'info'}
        showIcon
        message={status === 'failed' ? 'Не удалось собрать образы' : 'Подбираем образы…'}
        className={styles.notice}
      />
    );
  }

  if (!outfits?.length) {
    return <Empty description="Подходящих товаров пока не найдено" className={styles.empty} />;
  }

  return (
    <section className={styles.results} aria-live="polite">
      <Title level={3} className={styles.heading}>Подобранные образы</Title>
      {outfits.map((outfit) => (
        <article key={outfit.id} className={styles.outfit}>
          <div className={styles.outfitHeader}>
            <Title level={4} className={styles.outfitTitle}>{outfit.title}</Title>
            <Text strong>{Math.round(outfit.total_price).toLocaleString('ru-RU')} ₽</Text>
          </div>
          <div className={styles.items}>
            {outfit.items.map((item) => (
              <a
                key={item.id}
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                className={styles.item}
              >
                <Image src={item.image || undefined} alt={item.name} preview={false} className={styles.image} />
                <span className={styles.details}>
                  <Text strong className={styles.name}>{item.name}</Text>
                  <Text className={styles.meta}>{item.marketplace} · {Math.round(item.price).toLocaleString('ru-RU')} ₽</Text>
                  {item.fit?.fit_signal && (
                    <Text className={styles.fit}>{fitLabels[item.fit.fit_signal]}</Text>
                  )}
                </span>
                <ExportOutlined aria-hidden="true" />
              </a>
            ))}
          </div>
        </article>
      ))}
    </section>
  );
}

export default GenerationResults;
