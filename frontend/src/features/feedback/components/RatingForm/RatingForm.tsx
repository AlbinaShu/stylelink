import { Button, Input } from 'antd';
import { useId, useState } from 'react';
import { useVisibleOnce } from '../../../../shared/hooks/useVisibleOnce';
import type { FeedbackScope, IFeedbackRating } from '../../types';
import styles from '../GenerationFeedback/GenerationFeedback.module.css';

interface RatingFormProps {
  scope: FeedbackScope;
  rating: IFeedbackRating | null;
  onSave: (score: number, comment: string) => Promise<void>;
  onVisible?: () => void;
}

export default function RatingForm({ scope, rating, onSave, onVisible }: RatingFormProps) {
  const id = useId();
  const [score, setScore] = useState<number | null>(rating?.score ?? null);
  const [comment, setComment] = useState(rating?.comment ?? '');
  const [editing, setEditing] = useState(!rating);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(false);
  const ref = useVisibleOnce<HTMLDivElement>(id, () => onVisible?.());
  const service = scope === 'service';

  const submit = async () => {
    if (score === null || saving) return;
    setSaving(true);
    setError(false);
    try {
      await onSave(score, comment);
      setEditing(false);
    } catch {
      setError(true);
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className={styles.form} aria-labelledby={id + '-title'}>
      <div ref={ref}>
        <h2 id={id + '-title'} className={styles.title}>
          {service ? 'Как вам AI StyleLink в целом?' : 'Как вам эта подборка?'}
        </h2>
        <p id={id + '-question'} className={styles.description}>
          {service ? 'Насколько вы в целом удовлетворены использованием сервиса?'
            : 'Насколько предложенные образы соответствуют вашему запросу?'}
        </p>
      </div>
      {!editing && rating ? (
        <div className={styles.saved} role="status">
          Спасибо за отзыв! Ваша оценка: <strong>{rating.score}/10</strong>{' '}
          <Button type="link" onClick={() => {
            setScore(rating.score);
            setComment(rating.comment ?? '');
            setEditing(true);
          }}>Изменить</Button>
        </div>
      ) : (
        <>
          <div className={styles.scale} role="radiogroup" aria-labelledby={id + '-question'}>
            {Array.from({ length: 10 }, (_, index) => index + 1).map(value => (
              <label key={value} className={styles.choice}>
                <input type="radio" name={id} value={value} checked={score === value}
                  disabled={saving} onChange={() => setScore(value)} aria-label={`${value} из 10`} />
                <span>{value}</span>
              </label>
            ))}
          </div>
          <div className={styles.endpoints}>
            <span>{service ? 'Совсем не удовлетворён' : 'Совсем не соответствуют'}</span>
            <span>{service ? 'Полностью удовлетворён' : 'Полностью соответствуют'}</span>
          </div>
          {score !== null && (
            <label className={styles.comment}>
              {service ? 'Что понравилось или что стоит улучшить?'
                : 'Что понравилось или чего не хватило?'} Необязательно
              <Input.TextArea value={comment} maxLength={2000} showCount rows={3} disabled={saving}
                onChange={event => setComment(event.target.value)}
                placeholder={service ? 'Поделитесь впечатлением от сервиса'
                  : 'Например, стиль, сочетание вещей, бюджет или выбор размера'} />
            </label>
          )}
          {error && <p role="alert" className={styles.error}>Не удалось сохранить оценку. Попробуйте ещё раз.</p>}
          <Button type="primary" disabled={score === null} loading={saving} onClick={() => void submit()}>
            Отправить оценку
          </Button>
        </>
      )}
    </section>
  );
}
