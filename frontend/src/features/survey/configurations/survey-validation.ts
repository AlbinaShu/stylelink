import type { ISurveyAnswerItem } from '../types';

export function isSurveyAnswerValid(
  answer: Partial<ISurveyAnswerItem> | undefined,
): answer is ISurveyAnswerItem {
  if (!answer?.product_id || !answer.order_placed) return false;
  if (answer.order_placed !== 'yes') {
    return Boolean(answer.added_to_cart && (
      answer.added_to_cart === 'no' ||
      (answer.sizes_in_cart && (answer.sizes_in_cart !== '1' || answer.cart_size))
    ));
  }
  if (!answer.sizes_ordered || !answer.fit_result) return false;
  if (answer.sizes_ordered === '1' && !answer.purchased_size) return false;
  if (answer.fit_result === 'in_transit') return true;
  if (answer.fit_result !== 'not_tried' && !answer.tried_size) return false;
  if (!answer.action) return false;
  return answer.action !== 'returned' || Boolean(answer.return_reason);
}
