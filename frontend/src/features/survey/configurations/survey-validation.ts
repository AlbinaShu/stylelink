import type { ISurveyAnswerItem } from '../types';

export function isSurveyAnswerValid(
  answer: Partial<ISurveyAnswerItem> | undefined,
  recommendedSize: string | null,
): answer is ISurveyAnswerItem {
  if (!recommendedSize || !answer?.product_id || !answer.order_placed) return false;
  if (answer.order_placed !== 'yes') {
    return Boolean(answer.added_to_cart && (
      answer.added_to_cart === 'no' ||
      (answer.sizes_in_cart && answer.cart_size)
    ));
  }
  if (!answer.sizes_ordered) return false;
  if (!answer.fit_result) return false;
  if (['in_transit', 'not_ordered'].includes(answer.fit_result)) return true;
  if (!answer.action) return false;
  return answer.action !== 'returned' || Boolean(answer.return_reasons?.length || answer.return_reason);
}
