import test from 'node:test';
import assert from 'node:assert/strict';
import { isSurveyAnswerValid as validateSurveyAnswer } from '../src/features/survey/configurations/survey-validation.ts';
import { isHalfVisible } from '../src/shared/hooks/useVisibleOnce.ts';

const isSurveyAnswerValid = (answer) => validateSurveyAnswer(answer, 'M');
const base = { product_id: 'product', order_placed: 'yes', sizes_ordered: '1', purchased_size: 'recommended' };
test('in-transit is a complete status without a fitting or return answer', () => {
  assert.equal(isSurveyAnswerValid({ ...base, fit_result: 'in_transit' }), true);
});
test('no-order branch ends with cart questions', () => {
  assert.equal(isSurveyAnswerValid({ product_id: 'product', order_placed: 'no', added_to_cart: 'no' }), true);
  assert.equal(isSurveyAnswerValid({ product_id: 'product', order_placed: 'pending' }), false);
});
test('a multi-size order assesses the recommendation without asking tried size', () => {
  assert.equal(isSurveyAnswerValid({ ...base, sizes_ordered: '2', fit_result: 'perfect', action: 'kept' }), true);
  assert.equal(isSurveyAnswerValid({ ...base, sizes_ordered: '3+', fit_result: 'not_ordered' }), true);
});
test('an item without a recommendation collects the number of ordered sizes', () => {
  assert.equal(validateSurveyAnswer({ ...base, sizes_ordered: '2' }, null), true);
});
test('unknown fit can independently report a quality return', () => {
  assert.equal(isSurveyAnswerValid({ ...base, fit_result: 'unknown', tried_size: 'recommended', action: 'returned', return_reason: 'quality' }), true);
});
test('not-tried excludes the tried-size question but keeps the return question', () => {
  assert.equal(isSurveyAnswerValid({ ...base, fit_result: 'not_tried', action: 'kept' }), true);
});
test('visibility counts only half-visible blocks in the active tab', () => {
  globalThis.window = { innerWidth: 100, innerHeight: 100 };
  globalThis.document = { visibilityState: 'visible' };
  const element = (top, bottom) => ({ getBoundingClientRect: () => ({ left: 0, right: 100, top, bottom, width: 100, height: bottom - top }) });
  assert.equal(isHalfVisible(element(100, 200)), false);
  assert.equal(isHalfVisible(element(51, 151)), false);
  assert.equal(isHalfVisible(element(50, 150)), true);
  globalThis.document.visibilityState = 'hidden';
  assert.equal(isHalfVisible(element(0, 100)), false);
});
