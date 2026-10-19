import { Modal, Spin, message } from 'antd';
import { useEffect, useRef, useState } from 'react';

import {
  sendSurveyOpened,
  sendSurveySkipped,
} from '../../../experiment-events/api/experiment-events.api';
import {
  getDeviceType,
  getSessionId,
} from '../../../../shared/utils/session';
import {
  getSurveyItems,
  getSurveyPopup,
  skipSurvey,
  submitSurveyAnswers,
} from '../../api/survey.api';
import type {
  ISurveyAnswerItem,
  ISurveyItem,
} from '../../types';
import SurveyForm from '../SurveyForm/SurveyForm';

import styles from './SurveyPopup.module.css';

const PAGE_SIZE = 10;

type Progress = {
  questionsAnswered: number;
  lastQuestionKey: string | null;
  lastQuestionValue: string | null;
};

function SurveyPopup() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<ISurveyItem[]>([]);
  const [surveyId, setSurveyId] = useState<string | null>(null);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const openedAtRef = useRef(0);

  const progressRef = useRef<Progress>({
    questionsAnswered: 0,
    lastQuestionKey: null,
    lastQuestionValue: null,
  });

  useEffect(() => {
    const sessionId = getSessionId();
    const checkKey = `ai-stylelink-survey-popup-check:${sessionId}`;

    if (sessionStorage.getItem(checkKey)) {
      return;
    }

    sessionStorage.setItem(checkKey, '1');

    const check = async () => {
      try {
        const popup = await getSurveyPopup(sessionId);

        if (!popup.show || !popup.survey_id) {
          return;
        }

        setLoading(true);

        const data = await getSurveyItems(0, PAGE_SIZE);

        setSurveyId(data.survey_id);
        setItems(data.items);
        setTotal(data.total);
        setHasMore(data.has_more);

        openedAtRef.current = Date.now();
        setOpen(true);

        void sendSurveyOpened({
          session_id: sessionId,
          timestamp: new Date().toISOString(),
          survey_type: 'popup',
          items_count: data.total,
          device_type: getDeviceType(),
        }).catch(() => undefined);
      } catch (error) {
        sessionStorage.removeItem(checkKey);

        console.error(
          '[Survey] Failed to load survey:',
          error,
        );
      } finally {
        setLoading(false);
      }
    };

    void check();
  }, []);

  const loadMore = async () => {
    setLoadingMore(true);

    try {
      const data = await getSurveyItems(
        items.length,
        PAGE_SIZE,
      );

      setItems((current) => [
        ...current,
        ...data.items,
      ]);

      setHasMore(data.has_more);
      setTotal(data.total);
    } finally {
      setLoadingMore(false);
    }
  };

  const submit = async (
    answers: ISurveyAnswerItem[],
  ) => {
    if (!surveyId) {
      return;
    }

    setSubmitting(true);

    try {
      await submitSurveyAnswers({
        survey_id: surveyId,
        session_id: getSessionId(),
        answers,
      });

      setOpen(false);

      void message.success(
        'Спасибо! Ваш ответ поможет нам улучшить сервис.',
      );
    } catch {
      void message.error(
        'Не удалось отправить ответы. Проверьте заполнение формы.',
      );
    } finally {
      setSubmitting(false);
    }
  };

  const skip = async (
    reason: 'button' | 'close',
    progress = progressRef.current,
  ) => {
    if (!surveyId) {
      setOpen(false);
      return;
    }

    const timeSpentMs = Math.max(
      0,
      Date.now() - openedAtRef.current,
    );

    const payload = {
      survey_id: surveyId,
      session_id: getSessionId(),
      questions_answered:
        progress.questionsAnswered,
      last_question_key:
        progress.lastQuestionKey,
      last_question_value:
        progress.lastQuestionValue,
      time_spent_ms: timeSpentMs,
      skip_reason: reason,
    } as const;

    try {
      await skipSurvey(payload);

      void sendSurveySkipped({
        session_id: getSessionId(),
        timestamp: new Date().toISOString(),
        survey_type: 'popup',
        questions_answered:
          progress.questionsAnswered,
        last_question_key:
          progress.lastQuestionKey,
        last_question_value:
          progress.lastQuestionValue,
        time_spent_ms: timeSpentMs,
        skip_reason: reason,
        device_type: getDeviceType(),
      }).catch(() => undefined);
    } finally {
      setOpen(false);
    }
  };

  return (
    <Modal
      open={open}
      footer={null}
      width={620}
      centered
      destroyOnHidden
      maskClosable={false}
      className={styles.modal}
      onCancel={() => void skip('close')}
    >
      {loading ? (
        <div className={styles.loader}>
          <Spin />
        </div>
      ) : (
        <SurveyForm
          items={items}
          total={total}
          hasMore={hasMore}
          loadingMore={loadingMore}
          submitting={submitting}
          onLoadMore={loadMore}
          onSubmit={submit}
          onProgress={(progress) => {
            progressRef.current = progress;
          }}
          onSkip={(progress) =>
            skip('button', progress)
          }
        />
      )}
    </Modal>
  );
}

export default SurveyPopup;