import { useEffect, useRef, useState } from 'react';
import { useVisibleOnce } from '../../../shared/hooks/useVisibleOnce';
import { claimInvitation, getFeedback, recordFeedbackEvent, saveRating } from '../api/feedback.api';
import { SERVICE_INVITATION_DELAY_MS } from '../configurations/feedback';
import type { FeedbackScope, IFeedbackContext } from '../types';

export function useGenerationFeedback(generationId: string) {
  const [data, setData] = useState<IFeedbackContext | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [open, setOpen] = useState(false);
  const [seenResults, setSeenResults] = useState(false);
  const mounted = useRef(false);
  const claiming = useRef(false);
  const resultsRef = useVisibleOnce<HTMLDivElement>(generationId, () => setSeenResults(true));

  useEffect(() => {
    let active = true;
    mounted.current = true;
    void getFeedback(generationId).then(value => {
      if (active) { setData(value); setLoadError(false); }
    }).catch(() => { if (active) setLoadError(true); });
    return () => { active = false; mounted.current = false; };
  }, [generationId, attempt]);

  useEffect(() => {
    if (!seenResults || !data?.invitation_eligible || open) return;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const schedule = () => {
      clearTimeout(timer);
      if (document.visibilityState !== 'visible') return;
      timer = setTimeout(() => {
        if (claiming.current) return;
        const activeElement = document.activeElement;
        if (document.querySelector('[role="dialog"]') || (
          activeElement instanceof HTMLElement && (
            ['INPUT', 'TEXTAREA', 'SELECT'].includes(activeElement.tagName) || activeElement.isContentEditable
          )
        )) { schedule(); return; }
        claiming.current = true;
        void claimInvitation(generationId).then(show => {
          if (!mounted.current) return;
          setData(previous => previous ? { ...previous, invitation_eligible: false } : previous);
          setOpen(show);
        }).catch(() => {
          // Inline questions remain available; a later visit can retry the invitation.
        }).finally(() => { claiming.current = false; });
      }, SERVICE_INVITATION_DELAY_MS);
    };
    schedule();
    document.addEventListener('visibilitychange', schedule);
    return () => {
      clearTimeout(timer);
      document.removeEventListener('visibilitychange', schedule);
    };
  }, [seenResults, data?.invitation_eligible, generationId, open]);

  const recordView = (scope: FeedbackScope) => {
    void recordFeedbackEvent(generationId, scope, 'inline_view').catch(() => undefined);
  };
  const save = async (scope: FeedbackScope, score: number, comment: string, source: 'inline' | 'invitation') => {
    const rating = await saveRating(generationId, scope, score, comment, source);
    setData(previous => previous ? { ...previous, [scope]: rating,
      invitation_eligible: scope === 'service' ? false : previous.invitation_eligible } : previous);
    if (scope === 'service') setOpen(false);
  };
  const dismiss = () => {
    setOpen(false);
    void recordFeedbackEvent(generationId, 'service', 'invitation_dismissed').catch(() => undefined);
  };

  const retry = () => {
    setLoadError(false);
    setAttempt(value => value + 1);
  };

  return { data, loadError, open, resultsRef, recordView, save, dismiss, retry };
}
