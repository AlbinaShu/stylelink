export type FeedbackScope = 'selection' | 'service';
export interface IFeedbackRating {
  score: number;
  comment: string | null;
  generation_id: string;
  generation_number: number;
}
export interface IFeedbackContext {
  generation_number: number;
  completed_count: number;
  selection: IFeedbackRating | null;
  service: IFeedbackRating | null;
  invitation_eligible: boolean;
}
