import type {
    CountChoice,
    FitResult,
    OrderPlaced,
    ReturnReason,
    SizeChoice,
    SurveyAction,
} from '../types';

export interface ISurveyOption<T extends string> {
    value: T;
    label: string;
}

export const ORDER_PLACED_OPTIONS: readonly ISurveyOption<OrderPlaced>[] = [
    { value: 'yes', label: 'Да' },
    { value: 'no', label: 'Нет' },
    { value: 'pending', label: 'Пока не оформил(а)' },
];

export const COUNT_OPTIONS: readonly ISurveyOption<CountChoice>[] = [
    { value: '1', label: '1 размер' },
    { value: '2', label: '2 размера' },
    { value: '3+', label: '3 и больше' },
];

export const SIZE_CHOICE_OPTIONS: readonly ISurveyOption<SizeChoice>[] = [
    { value: 'recommended', label: 'Рекомендованный' },
    { value: 'other', label: 'Другой' },
];

export const YES_NO_OPTIONS: readonly ISurveyOption<'yes' | 'no'>[] = [
    { value: 'yes', label: 'Да' },
    { value: 'no', label: 'Нет' },
];

export const FIT_OPTIONS: readonly ISurveyOption<FitResult>[] = [
    { value: 'perfect', label: 'Идеально' },
    { value: 'small', label: 'Оказался мал' },
    { value: 'large', label: 'Оказался велик' },
    { value: 'unknown', label: 'Примерил(а), но затрудняюсь оценить' },
    { value: 'not_ordered', label: 'Этот размер не заказывал(а)' },
    { value: 'in_transit', label: 'Товар ещё в пути' },
    { value: 'not_tried', label: 'Получил(а), но ещё не примерил(а)' },
];

export const ACTION_OPTIONS: readonly ISurveyOption<SurveyAction>[] = [
    { value: 'kept', label: 'Оставил(а)' },
    { value: 'returned', label: 'Вернул(а)' },
    { value: 'undecided', label: 'Пока не решил(а)' },
];

export const RETURN_REASON_OPTIONS: readonly ISurveyOption<ReturnReason>[] = [
    { value: 'size', label: 'Размер' },
    { value: 'quality', label: 'Качество' },
    { value: 'color', label: 'Цвет / фасон' },
    { value: 'other', label: 'Другое' },
];