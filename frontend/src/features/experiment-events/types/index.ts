import type { IOutfit } from '../../outfit-generation/types';

export interface IRecommendationViewEvent {
  session_id: string;
  timestamp: string;
  device_type: string;
  outfitItems: Array<{
    product_id: string;
    name: string;
    price: number;
    category: string;
    recommended_size?: string | null;
    fit_signal?: string | null;
    confidence?: number | null;
    num_reviews?: number | null;
  }>;
}

export interface ITooltipOpenEvent {
  session_id: string;
  product_id: string;
  tooltip_type: string;
  timestamp: string;
}

export interface IBuyClickEvent {
  session_id: string;
  timestamp: string;
  product_id: string;
  recommended_size?: string | null;
  price: number;
  outfit_id?: string | null;
  selected_size: string;
  match: boolean;
}

export interface ISizeChangedEvent {
  session_id: string;
  timestamp: string;
  item_id: string;
  recommended_size?: string | null;
  previous_size: string;
  selected_size: string;
}

export interface ISurveyOpenedEvent {
  session_id: string;
  timestamp: string;
  survey_type: 'popup' | 'email';
  items_count?: number | null;
  device_type?: string | null;
}

export interface ISurveySkippedEvent {
  session_id: string;
  timestamp: string;
  survey_type: 'popup' | 'email';
  questions_answered: number;
  last_question_key?: string | null;
  last_question_value?: string | null;
  time_spent_ms?: number | null;
  skip_reason?: 'button' | 'close' | null;
  device_type?: string | null;
}

export interface ISessionEndEvent {
  session_id: string;
  timestamp: string;
  duration_ms: number;
  device_type: string;
}

export type RecommendationOutfits = IOutfit[];
