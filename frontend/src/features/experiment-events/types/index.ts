export interface IRecommendationViewEvent {
  session_id: string;
  timestamp: string;
  device_type: string;
  outfitItems: Array<{
    product_id: string;
    outfit_id: string;
    outfit_item_id: string;
    initial_selected_size: string | null;
    explanation_visible: boolean;
    explanation_summary?: string | null;
  }>;
}

export interface ITooltipOpenEvent {
  session_id: string;
  product_id: string;
  outfit_id?: string;
  outfit_item_id?: string;
  tooltip_type: string;
  explanation_summary?: string | null;
  explanation_text?: string | null;
  explanation_meta?: string | null;
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
  product_id: string;
  outfit_id: string;
  outfit_item_id: string;
  recommended_size?: string | null;
  previous_size: string;
  selected_size: string;
}

export interface ISurveyOpenedEvent {
  session_id: string;
  timestamp: string;
  survey_id: string;
  survey_type: 'popup' | 'email';
  product_ids: string[];
  items_count: number;
  device_type?: string | null;
}

export interface ISurveySkippedEvent extends ISurveyOpenedEvent {
  questions_answered: number;
  last_product_id?: string | null;
  last_question_key?: string | null;
  last_question_value?: string | null;
  time_spent_ms?: number | null;
  skip_reason?: 'button' | 'close' | null;
}

export interface ISessionEndEvent {
  session_id: string;
  timestamp: string;
  duration_ms: number;
  device_type: string;
}
