import type { ISurveyAnswerItem } from '../types';

export function isSurveyAnswerValid(
    answer: Partial<ISurveyAnswerItem>,
): answer is ISurveyAnswerItem {
    if (!answer.product_id || !answer.order_placed) {
        return false;
    }

    if (answer.order_placed === 'pending') {
        return true;
    }

    if (answer.order_placed === 'yes') {
        if (!answer.sizes_ordered || !answer.fit_result) {
            return false;
        }

        if (
            answer.sizes_ordered === '1' &&
            !answer.purchased_size
        ) {
            return false;
        }
    }

    if (answer.order_placed === 'no') {
        if (!answer.added_to_cart || !answer.fit_result) {
            return false;
        }

        if (answer.added_to_cart === 'yes') {
            if (!answer.sizes_in_cart) {
                return false;
            }

            if (
                answer.sizes_in_cart === '1' &&
                !answer.cart_size
            ) {
                return false;
            }
        }
    }

    if (
        answer.fit_result &&
        answer.fit_result !== 'unknown' &&
        !answer.action
    ) {
        return false;
    }

    if (
        answer.action === 'returned' &&
        !answer.return_reason
    ) {
        return false;
    }

    return true;
}