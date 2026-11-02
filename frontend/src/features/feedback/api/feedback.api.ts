import http from '../../../shared/api/http-client';
import type { FeedbackScope, IFeedbackContext, IFeedbackRating } from '../types';

const url = (generationId: string) => `/api/v1/feedback/${generationId}`;

export async function getFeedback(generationId: string): Promise<IFeedbackContext> {
  return (await http.get<IFeedbackContext>(url(generationId))).data;
}
export async function saveRating(generationId: string, scope: FeedbackScope, score: number,
  comment: string, source: 'inline' | 'invitation'): Promise<IFeedbackRating> {
  return (await http.put<IFeedbackRating>(`${url(generationId)}/ratings/${scope}`, { score, comment, source })).data;
}
export async function claimInvitation(generationId: string): Promise<boolean> {
  return (await http.post<{ show: boolean }>(`${url(generationId)}/invitation`)).data.show;
}
export async function recordFeedbackEvent(generationId: string, scope: FeedbackScope,
  event_type: 'inline_view' | 'invitation_dismissed') {
  await http.post(`${url(generationId)}/events`, { scope, event_type });
}
