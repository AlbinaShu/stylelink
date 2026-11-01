import http from '../../../shared/api/http-client';
import axios from 'axios';
import type {
  IBuyClickEvent,
  IRecommendationViewEvent,
  ISessionEndEvent,
  ISizeChangedEvent,
  ISurveyOpenedEvent,
  ISurveySkippedEvent,
  ITooltipOpenEvent,
} from '../types';

const BASE = '/api/v1/experiment-events';

export const sendRecommendationView = (payload: IRecommendationViewEvent) =>
  http.post(`${BASE}/recommendation-view`, payload);

export const sendExplanationView = (payload: IRecommendationViewEvent) =>
  http.post(BASE + '/explanation-view', payload);

export const sendTooltipOpen = (payload: ITooltipOpenEvent) =>
  http.post(`${BASE}/tooltip-open`, payload);

export const sendBuyClick = (payload: IBuyClickEvent) =>
  http.post(`${BASE}/buy-click`, payload);

export const sendSizeChanged = (payload: ISizeChangedEvent) =>
  http.post(`${BASE}/size-changed`, payload);

const publicHttp = axios.create({ baseURL: window.__ENV__?.API_URL || import.meta.env.VITE_API_URL });
const surveyEvent = (name: string, payload: ISurveyOpenedEvent | ISurveySkippedEvent, token?: string) => token
  ? publicHttp.post('/api/v1/survey/email/events/' + name, payload, { params: { token } })
  : http.post(BASE + '/survey-' + name, payload);
export const sendSurveyOpened = (payload: ISurveyOpenedEvent, token?: string) => surveyEvent('opened', payload, token);
export const sendSurveyItemView = (payload: ISurveyOpenedEvent, token?: string) => surveyEvent('item-view', payload, token);
export const sendSurveySkipped = (payload: ISurveySkippedEvent, token?: string) => surveyEvent('skipped', payload, token);

export const sendSessionEnd = (payload: ISessionEndEvent) =>
  http.post(`${BASE}/session-end`, payload);
