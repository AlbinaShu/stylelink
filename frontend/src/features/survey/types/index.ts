export type SurveyStatus = 'not_answered' | 'answered';
export type OrderPlaced = 'yes' | 'no' | 'pending';
export type CountChoice = '1' | '2' | '3+';
export type SizeChoice = 'recommended' | 'other';
export type FitResult = 'perfect' | 'small' | 'large' | 'unknown' | 'in_transit' | 'not_tried' | 'not_ordered';
export type SurveyAction = 'kept' | 'returned' | 'undecided';
export type ReturnReason = 'size' | 'quality' | 'color' | 'other';

export interface ISurveyItem {
  product_id: string;
  name: string | null;
  image_url: string | null;
  recommended_size: string | null;
  selected_size: string | null;
  status: SurveyStatus;
  clicked_at: string;
  buy_click_id: string | null;
  answer?: ISurveyAnswerItem | null;
}

export interface ISurveyItemsResponse {
  survey_id: string;
  items: ISurveyItem[];
  total: number;
  has_more: boolean;
}

export interface ISurveyPopupResponse {
  show: boolean;
  survey_id: string | null;
  reason: 'available' | 'same_session' | 'already_shown' | 'skip_cooldown' | 'no_survey';
}

export interface ISurveyAnswerItem {
  product_id: string;
  fit_scope?: 'recommended_only';
  order_placed: OrderPlaced;
  sizes_ordered?: CountChoice | null;
  purchased_size?: SizeChoice | null;
  added_to_cart?: 'yes' | 'no' | null;
  sizes_in_cart?: CountChoice | null;
  cart_size?: SizeChoice | null;
  fit_result?: FitResult | null;
  tried_size?: SizeChoice | null;
  action?: SurveyAction | null;
  return_reason?: ReturnReason | null;
  return_reason_text?: string | null;
}

export interface ISurveyAnswersRequest {
  survey_id: string;
  session_id?: string | null;
  answers: ISurveyAnswerItem[];
}

export interface ISurveyAnswersResponse {
  status: 'ok';
  answered_count: number;
  continuation_path?: string | null;
}

export interface ISurveySkipRequest {
  survey_id: string;
  session_id?: string | null;
  questions_answered?: number;
  last_question_key?: string | null;
  last_question_value?: string | null;
  time_spent_ms?: number | null;
  skip_reason?: 'button' | 'close' | null;
}

export interface ISurveyValidateResponse {
  valid: boolean;
  survey_id: string | null;
  expires_at: string | null;
  reason: 'already_answered' | 'expired' | 'not_found' | null;
}

export interface IEmailSurveyAnswersResponse {
  status: 'saved';
  survey_id: string;
  answers_created: number;
}

export interface ISurveyProgress {
  questionsAnswered: number;
  lastProductId: string | null;
  lastQuestionKey: string | null;
  lastQuestionValue: string | null;
}
