import { Alert, Result, Spin, message } from 'antd';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getEmailSurveyItems, submitEmailSurveyAnswers, validateEmailSurvey } from '../../features/survey/api/survey.api';
import type { ISurveyAnswerItem, ISurveyItem, ISurveyValidateResponse } from '../../features/survey/types';
import SurveyForm from '../../features/survey/components/SurveyForm/SurveyForm';
import styles from './SurveyEmailPage.module.css';

const PAGE_SIZE = 10;

function validationMessage(reason: ISurveyValidateResponse['reason']): string {
  if (reason === 'already_answered') return 'Спасибо! Вы уже ответили на этот опрос.';
  if (reason === 'expired') return 'Срок действия опроса истёк.';

  return 'Опрос не найден.';
}

function SurveyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get('token');
  const [items, setItems] = useState<ISurveyItem[]>([]);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [invalidReason, setInvalidReason] = useState<ISurveyValidateResponse['reason']>(null);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    if (!token) {
      setInvalidReason('not_found');
      setLoading(false);
      return;
    }

    let cancelled = false;
    const load = async () => {
      try {
        const validation = await validateEmailSurvey(token);
        if (cancelled) return;

        if (!validation.valid) {
          setInvalidReason(validation.reason ?? 'not_found');
          return;
        }

        const data = await getEmailSurveyItems(token, 0, PAGE_SIZE);

        if (cancelled) return;

        setItems(data.items);
        setTotal(data.total);
        setHasMore(data.has_more);
      } catch {
        if (!cancelled) setError('Не удалось загрузить опрос.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => { cancelled = true; };
  }, [token]);

  const loadMore = async () => {
    if (!token) return;

    setLoadingMore(true);

    try {
      const data = await getEmailSurveyItems(token, items.length, PAGE_SIZE);
      setItems((current) => [...current, ...data.items]);
      setTotal(data.total);
      setHasMore(data.has_more);
    } finally {
      setLoadingMore(false);
    }
  };

  const submit = async (answers: ISurveyAnswerItem[]) => {
    if (!token) return;

    setSubmitting(true);

    try {
      await submitEmailSurveyAnswers(token, answers);
      setDone(true);
      void message.success('Ответы сохранены.');
    } catch {
      void message.error('Не удалось отправить ответы. Проверьте заполнение формы.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <div className={styles.center}><Spin size="large" /></div>;
  if (error) return <div className={styles.page}><Alert type="error" showIcon message={error} /></div>;
  if (invalidReason) return <div className={styles.center}><Result status="info" title={validationMessage(invalidReason)} /></div>;
  if (done) return <div className={styles.center}><Result status="success" title="Спасибо!" subTitle="Ваш ответ поможет нам улучшить сервис." /></div>;

  return (
    <main className={styles.page}>
      <div className={styles.card}>
        <SurveyForm
          items={items}
          total={total}
          hasMore={hasMore}
          loadingMore={loadingMore}
          submitting={submitting}
          onLoadMore={loadMore}
          onSubmit={submit}
        />
      </div>
    </main>
  );
}

export default SurveyEmailPage;
