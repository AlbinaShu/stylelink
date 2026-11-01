import { Modal, Spin, message } from 'antd';
import { useEffect, useState } from 'react';
import { getSessionId } from '../../../../shared/utils/session';
import { getSurveyItems, getSurveyPopup, skipSurvey, submitSurveyAnswers } from '../../api/survey.api';
import type { ISurveyAnswerItem, ISurveyItem, ISurveyItemsResponse, ISurveyProgress } from '../../types';
import { useSurveyTracking } from '../../hooks/useSurveyTracking';
import SurveyForm from '../SurveyForm/SurveyForm';
import styles from './SurveyPopup.module.css';

const PAGE_SIZE = 10;
// Reuse the in-flight request across React StrictMode effect remounts.
const popupRequests = new Map<string, Promise<ISurveyItemsResponse | null>>();
function loadPopup(sessionId: string) {
  let request = popupRequests.get(sessionId);
  if (!request) {
    request = getSurveyPopup(sessionId).then((popup) =>
      popup.show && popup.survey_id ? getSurveyItems(0, PAGE_SIZE, popup.survey_id) : null);
    popupRequests.set(sessionId, request);
    void request.catch(() => popupRequests.delete(sessionId));
  }
  return request;
}

function SurveyPopup() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<ISurveyItem[]>([]);
  const [surveyId, setSurveyId] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const tracking = useSurveyTracking(surveyId, 'popup');

  useEffect(() => {
    const sessionId = getSessionId();
    const checkKey = 'ai-stylelink-survey-popup-check:' + sessionId;
    if (sessionStorage.getItem(checkKey)) return;
    let cancelled = false;
    const check = async () => {
      try {
        const data = await loadPopup(sessionId);
        if (cancelled) return;
        sessionStorage.setItem(checkKey, '1');
        if (!data) return;
        setSurveyId(data.survey_id);
        setItems(data.items);
        setTotal(data.total);
        setHasMore(data.has_more);
        setOpen(true);
      } catch {
        sessionStorage.removeItem(checkKey);
      }
    };
    void check();
    return () => { cancelled = true; };
  }, []);

  const loadMore = async () => {
    if (!surveyId) return;
    setLoadingMore(true);
    try {
      const data = await getSurveyItems(items.length, PAGE_SIZE, surveyId);
      setItems((current) => [...current, ...data.items]);
      setHasMore(data.has_more);
      setTotal(data.total);
    } finally { setLoadingMore(false); }
  };

  const submit = async (answers: ISurveyAnswerItem[]) => {
    if (!surveyId) return;
    setSubmitting(true);
    try {
      const result = await submitSurveyAnswers({ survey_id: surveyId, session_id: getSessionId(), answers });
      tracking.finish();
      setOpen(false);
      Modal.success({
        title: 'Спасибо! Ответ сохранен.',
        content: result.continuation_path
          ? <a href={result.continuation_path} target="_blank" rel="noopener noreferrer">Открыть ссылку, чтобы позже дополнить или обновить ответ</a>
          : 'Ваш ответ поможет нам улучшить сервис.',
      });
    } catch {
      void message.error('Не удалось отправить ответы. Проверьте заполнение формы.');
    } finally { setSubmitting(false); }
  };

  const skip = async (reason: 'button' | 'close', progress?: ISurveyProgress) => {
    tracking.skip(reason, progress);
    if (surveyId) {
      try {
        await skipSurvey({
          survey_id: surveyId, session_id: getSessionId(), skip_reason: reason,
          questions_answered: progress?.questionsAnswered ?? 0,
          last_question_key: progress?.lastQuestionKey,
          last_question_value: progress?.lastQuestionValue,
        });
      } finally { setOpen(false); }
    } else { setOpen(false); }
  };

  return (
    <Modal open={open} footer={null} width={620} centered destroyOnHidden
      maskClosable={false} className={styles.modal}
      afterOpenChange={(visible) => { if (visible) tracking.open(); }}
      onCancel={() => void skip('close')}>
      {items.length === 0 ? <Spin /> : (
        <SurveyForm items={items} total={total} hasMore={hasMore}
          loadingMore={loadingMore} submitting={submitting}
          onLoadMore={loadMore} onSubmit={submit}
          onProgress={tracking.progress} onItemVisible={tracking.itemVisible}
          onSkip={(progress) => skip('button', progress)} />
      )}
    </Modal>
  );
}
export default SurveyPopup;
