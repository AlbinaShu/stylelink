import axios from 'axios';
import http from '../../../shared/api/http-client';
import type {
  IEmailSurveyAnswersResponse,
  ISurveyAnswerItem,
  ISurveyAnswersRequest,
  ISurveyAnswersResponse,
  ISurveyItemsResponse,
  ISurveyPopupResponse,
  ISurveySkipRequest,
  ISurveyValidateResponse,
} from '../types';

const publicHttp = axios.create({
  baseURL: window.__ENV__?.API_URL || import.meta.env.VITE_API_URL,
  headers: { 'Content-Type': 'application/json' },
});

export async function getSurveyPopup(sessionId: string): Promise<ISurveyPopupResponse> {
  const { data } = await http.get<ISurveyPopupResponse>('/api/v1/survey/popup', {
    params: { session_id: sessionId },
  });

  return data;
}

export async function getSurveyItems(offset = 0, limit = 10, surveyId?: string): Promise<ISurveyItemsResponse> {
  const { data } = await http.get<ISurveyItemsResponse>('/api/v1/survey/items', {
    params: { offset, limit, survey_id: surveyId },
  });

  return data;
}

export async function submitSurveyAnswers(payload: ISurveyAnswersRequest): Promise<ISurveyAnswersResponse> {
  const { data } = await http.post<ISurveyAnswersResponse>('/api/v1/survey/answers', payload);

  return data;
}

export async function skipSurvey(payload: ISurveySkipRequest): Promise<{ status: 'skipped' }> {
  const { data } = await http.post<{ status: 'skipped' }>('/api/v1/survey/skip', payload);

  return data;
}

export async function validateEmailSurvey(token: string): Promise<ISurveyValidateResponse> {
  const { data } = await publicHttp.get<ISurveyValidateResponse>('/api/v1/survey/email/validate', {
    params: { token },
  });

  return data;
}

export async function getEmailSurveyItems(token: string, offset = 0, limit = 10): Promise<ISurveyItemsResponse> {
  const { data } = await publicHttp.get<ISurveyItemsResponse>('/api/v1/survey/email/items', {
    params: { token, offset, limit },
  });

  return data;
}

export async function submitEmailSurveyAnswers(token: string, answers: ISurveyAnswerItem[]): Promise<IEmailSurveyAnswersResponse> {
  const { data } = await publicHttp.post<IEmailSurveyAnswersResponse>(
    '/api/v1/survey/email/answers',
    answers,
    { params: { token } },
  );

  return data;
}
