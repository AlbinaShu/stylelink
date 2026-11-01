import { useCallback, useEffect, useRef } from 'react';
import {
  sendSurveyItemView, sendSurveyOpened, sendSurveySkipped,
} from '../../experiment-events/api/experiment-events.api';
import { getDeviceType, getSessionId } from '../../../shared/utils/session';
import type { ISurveyProgress } from '../types';

export function useSurveyTracking(surveyId: string | null, type: 'popup' | 'email', token?: string) {
  const state = useRef({
    surveyId: '', opened: false, finished: false, skipped: false, openedAt: 0,
    seen: new Set<string>(), progress: {} as ISurveyProgress,
  });
  const base = useCallback(() => ({
    session_id: getSessionId(), timestamp: new Date().toISOString(),
    survey_id: surveyId!, survey_type: type, device_type: getDeviceType(),
  }), [surveyId, type]);

  const open = useCallback(() => {
    if (!surveyId) return;
    if (state.current.surveyId !== surveyId) {
      state.current = {
        surveyId, opened: false, finished: false, skipped: false, openedAt: 0,
        seen: new Set(), progress: {} as ISurveyProgress,
      };
    }
    if (state.current.opened) return;
    state.current.opened = true;
    state.current.openedAt = Date.now();
    void sendSurveyOpened({ ...base(), product_ids: [], items_count: 0 }, token).catch(() => undefined);
  }, [surveyId, base, token]);

  const itemVisible = useCallback((productId: string) => {
    if (!surveyId) return;
    open();
    if (state.current.seen.has(productId)) return;
    state.current.seen.add(productId);
    void sendSurveyItemView({
      ...base(), product_ids: [productId], items_count: 1,
    }, token).catch(() => undefined);
  }, [surveyId, open, base, token]);

  const progress = useCallback((value: ISurveyProgress) => {
    state.current.progress = value;
  }, []);

  const finish = useCallback(() => { state.current.finished = true; }, []);

  const skip = useCallback((reason: 'button' | 'close', value?: ISurveyProgress) => {
    const current = state.current;
    if (!surveyId || !current.opened || current.finished || current.skipped) return;
    current.skipped = true;
    const p = value ?? current.progress;
    void sendSurveySkipped({
      ...base(), product_ids: [...current.seen], items_count: current.seen.size,
      questions_answered: p.questionsAnswered ?? 0,
      last_product_id: p.lastProductId ?? null,
      last_question_key: p.lastQuestionKey ?? null,
      last_question_value: p.lastQuestionValue ?? null,
      time_spent_ms: Math.max(0, Date.now() - current.openedAt), skip_reason: reason,
    }, token).catch(() => undefined);
  }, [surveyId, base, token]);

  useEffect(() => {
    const onHide = () => skip('close');
    window.addEventListener('pagehide', onHide);
    return () => window.removeEventListener('pagehide', onHide);
  }, [skip]);
  return { open, itemVisible, progress, finish, skip };
}
