import http from '../../../shared/api/http-client';
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

export const sendTooltipOpen = (payload: ITooltipOpenEvent) =>
  http.post(`${BASE}/tooltip-open`, payload);

export const sendBuyClick = (payload: IBuyClickEvent) =>
  http.post(`${BASE}/buy-click`, payload);

export const sendSizeChanged = (payload: ISizeChangedEvent) =>
  http.post(`${BASE}/size-changed`, payload);

export const sendSurveyOpened = (payload: ISurveyOpenedEvent) =>
  http.post(`${BASE}/survey-opened`, payload);

export const sendSurveySkipped = (payload: ISurveySkippedEvent) =>
  http.post(`${BASE}/survey-skipped`, payload);

export const sendSessionEnd = (payload: ISessionEndEvent) =>
  http.post(`${BASE}/session-end`, payload);
