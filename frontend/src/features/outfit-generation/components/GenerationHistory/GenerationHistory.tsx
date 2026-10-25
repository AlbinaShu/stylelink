import { ArrowRightOutlined } from '@ant-design/icons';
import { Spin, Typography } from 'antd';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getGenerations } from '../../api/generation.api';
import type { IGeneration } from '../../types';

import styles from './GenerationHistory.module.css';

const { Text, Title } = Typography;

interface IGenerationHistoryProps {
  limit?: number;
  showTitle?: boolean;
  onEmpty?: () => void;
}

const LABELS: Record<string, string> = {
  // Повод
  walk: 'Прогулка',
  work: 'Работа',
  office: 'Офис',
  date: 'Свидание',
  party: 'Вечеринка',
  wedding: 'Свадьба',
  travel: 'Путешествие',
  vacation: 'Отпуск',
  dinner: 'Ужин',
  restaurant: 'Ресторан',
  everyday: 'На каждый день',
  casual_outing: 'Повседневный выход',
  event: 'Мероприятие',

  // Стиль
  business: 'Деловой',
  business_casual: 'Деловой повседневный',
  casual: 'Повседневный',
  sport: 'Спортивный',
  sports: 'Спортивный',
  sporty: 'Спортивный',
  classic: 'Классический',
  classical: 'Классический',
  romantic: 'Романтический',
  minimalism: 'Минимализм',
  minimalist: 'Минималистичный',
  streetwear: 'Уличный',
  street: 'Уличный',
  elegant: 'Элегантный',
  smart_casual: 'Элегантный повседневный',
  formal: 'Формальный',
  relaxed: 'Расслабленный',
  feminine: 'Женственный',
  masculine: 'Мужественный',

  // Сезон
  summer: 'Лето',
  autumn: 'Осень',
  fall: 'Осень',
  winter: 'Зима',
  spring: 'Весна',
  spring_autumn: 'Весна–осень',
  autumn_spring: 'Осень–весна',
  spring_fall: 'Весна–осень',
  fall_spring: 'Осень–весна',
  demi_season: 'Демисезон',
  all_season: 'Всесезонный',
};

const OCCASION_EMOJIS: Record<string, string> = {
  walk: '🚶',
  work: '💼',
  office: '💼',
  date: '❤️',
  party: '🎉',
  wedding: '💍',
  travel: '✈️',
  vacation: '🏖️',
  dinner: '🍽️',
  restaurant: '🍽️',
  everyday: '👕',
  casual_outing: '👟',
  event: '✨',
};

function getGenerationEmoji(generation: IGeneration): string {
  if (!generation.occasion) {
    return '✨';
  }

  const normalized = generation.occasion
    .trim()
    .toLowerCase()
    .replace(/[\\s-]+/g, '_');

  return OCCASION_EMOJIS[normalized] ?? '✨';
}

function humanize(value: string | null): string | null {
  if (!value) {
    return null;
  }

  const normalized = value
    .trim()
    .toLowerCase()
    .replace(/[\s-]+/g, '_');

  const translated = LABELS[normalized];

  if (translated) {
    return translated;
  }

  // Не показываем пользователю технические snake_case значения.
  const cleaned = value
    .trim()
    .replace(/[_-]+/g, ' ');

  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

function formatPrice(value: number | null): string {
  if (value == null) {
    return '';
  }

  return `${new Intl.NumberFormat('ru-RU', {
    maximumFractionDigits: 0,
  }).format(value)} ₽`;
}

function getGenerationTitle(generation: IGeneration): string {
  const parts = [
    humanize(generation.occasion),
    humanize(generation.style),
  ].filter(Boolean);

  if (parts.length > 0) {
    return parts.join(' · ');
  }

  if (generation.prompt?.trim()) {
    return generation.prompt.trim();
  }

  return 'Подбор образов';
}

function getGenerationPrompt(generation: IGeneration): string | null {
  const prompt = generation.prompt?.trim();

  if (!prompt) {
    return null;
  }

  const hasMainTitle = Boolean(
    humanize(generation.occasion) ||
    humanize(generation.style)
  );

  return hasMainTitle ? prompt : null;
}

function getGenerationSubtitle(generation: IGeneration): string {
  const season = humanize(generation.season);

  if (generation.status === 'failed') {
    return season ? `${season} · Ошибка генерации` : 'Ошибка генерации';
  }

  if (generation.status !== 'completed') {
    return season ? `${season} · Создаётся` : 'Создаётся';
  }

  return season ?? '';
}

function GenerationHistory({
  limit,
  showTitle = true,
  onEmpty,
}: IGenerationHistoryProps) {
  const navigate = useNavigate();

  const [generations, setGenerations] = useState<IGeneration[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let active = true;

    const load = async () => {
      try {
        const response = await getGenerations(1, limit ?? 20);

        if (!active) {
          return;
        }

        const items = response.items.filter(
          (generation) => generation.status !== 'failed',
        );

        setGenerations(limit ? items.slice(0, limit) : items);

        if (items.length === 0) {
          onEmpty?.();
        }
      } catch {
        if (active) {
          setGenerations([]);
          onEmpty?.();
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    };

    void load();

    return () => {
      active = false;
    };
  }, [limit]);

  const openGeneration = (generation: IGeneration) => {
    if (generation.status === 'completed') {
      navigate(`/outfit-generation/${generation.id}/results`);
      return;
    }

    navigate(`/outfit-generation/${generation.id}/loading`);
  };

  if (isLoading) {
    return (
      <div className={styles.loading}>
        <Spin size="small" />
      </div>
    );
  }

  if (generations.length === 0) {
    return null;
  }

  return (
    <section className={styles.section}>
      {showTitle && (
        <Title level={5} className={styles.heading}>
          История подборов
        </Title>
      )}

      <div className={styles.list}>
        {generations.map((generation) => (
          <button
            key={generation.id}
            type="button"
            className={styles.item}
            onClick={() => openGeneration(generation)}
          >
            <span className={styles.icon}>
              {getGenerationEmoji(generation)}
            </span>

            <span className={styles.info}>
              <Text className={styles.itemTitle}>
                {getGenerationTitle(generation)}
              </Text>

              {getGenerationPrompt(generation) && (
                <Text className={styles.subtitle} ellipsis>
                  «{getGenerationPrompt(generation)}»
                </Text>
              )}

              {getGenerationSubtitle(generation) && (
                <Text className={styles.subtitle}>
                  {getGenerationSubtitle(generation)}
                </Text>
              )}
            </span>

            <span className={styles.right}>
              {generation.budget != null && (
                <Text className={styles.price}>
                  {formatPrice(generation.budget)}
                </Text>
              )}

              <ArrowRightOutlined className={styles.arrow} />
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

export default GenerationHistory;
