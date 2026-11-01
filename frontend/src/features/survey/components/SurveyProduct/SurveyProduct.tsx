import { Button, Checkbox, Input, Typography } from 'antd';
import type { ISurveyAnswerItem, ReturnReason } from '../../types';
import {
    ACTION_OPTIONS,
    COUNT_OPTIONS,
    FIT_OPTIONS,
    ORDER_PLACED_OPTIONS,
    RETURN_REASON_OPTIONS,
    SIZE_CHOICE_OPTIONS,
    YES_NO_OPTIONS,
} from '../../configurations/survey-questions';
import SurveyQuestion from '../SurveyQuestion/SurveyQuestion';
import styles from './SurveyProduct.module.css';

interface ISurveyProductProps {
    answer: Partial<ISurveyAnswerItem>;
    recommendedSize: string | null;
    onChange: (
        key: keyof ISurveyAnswerItem,
        value: string | ReturnReason[] | null,
    ) => void;
    onSave: () => void;
}

function SurveyProduct({
    answer,
    recommendedSize,
    onChange,
    onSave,
}: ISurveyProductProps) {
    return (
        <div className={styles.questions}>
            <SurveyQuestion
                title="Заказывали этот товар?"
                value={answer.order_placed}
                options={ORDER_PLACED_OPTIONS}
                onChange={(value) => onChange('order_placed', value)}
            />

            {answer.order_placed === 'yes' && (
                <>
                    <SurveyQuestion
                        title="Сколько размеров заказали?"
                        value={answer.sizes_ordered}
                        options={COUNT_OPTIONS}
                        onChange={(value) => onChange('sizes_ordered', value)}
                    />

                </>
            )}

            {(answer.order_placed === 'no' || answer.order_placed === 'pending') && (
                <>
                    <SurveyQuestion
                        title="Добавляли товар в корзину?"
                        value={answer.added_to_cart}
                        options={YES_NO_OPTIONS}
                        onChange={(value) => onChange('added_to_cart', value)}
                    />

                    {answer.added_to_cart === 'yes' && (
                        <>
                            <SurveyQuestion
                                title="Сколько размеров добавляли?"
                                value={answer.sizes_in_cart}
                                options={COUNT_OPTIONS}
                                onChange={(value) => onChange('sizes_in_cart', value)}
                            />

                            {answer.sizes_in_cart && (
                                <SurveyQuestion
                                    title={answer.sizes_in_cart === '1' ? 'Какой размер был в корзине?' : 'Среди добавленных размеров был рекомендованный размер ' + recommendedSize + '?'}
                                    value={answer.cart_size}
                                    options={answer.sizes_in_cart === '1' ? SIZE_CHOICE_OPTIONS : [{value: 'recommended', label: 'Да'}, {value: 'other', label: 'Нет'}]}
                                    onChange={(value) => onChange('cart_size', value)}
                                />
                            )}
                        </>
                    )}
                </>
            )}

            {answer.order_placed === 'yes' && recommendedSize && (
                <SurveyQuestion
                    title={'Как подошёл рекомендованный нами размер ' + recommendedSize + '?'}
                    value={answer.fit_result}
                    options={FIT_OPTIONS}
                    onChange={(value) => onChange('fit_result', value)}
                />
            )}

            {answer.order_placed === 'yes' && answer.fit_result &&
                recommendedSize && !['in_transit', 'not_ordered'].includes(answer.fit_result) && (
                    <SurveyQuestion
                        title={'Что вы сделали с рекомендованным размером ' + recommendedSize + '?'}
                        value={answer.action}
                        options={ACTION_OPTIONS}
                        onChange={(value) => onChange('action', value)}
                    />
                )}

            {answer.action === 'returned' && (
                <>
                    <Typography.Text strong>
                        Почему вернули рекомендованный размер {recommendedSize}? Можно выбрать несколько причин.
                    </Typography.Text>
                    <Checkbox.Group
                        options={[...RETURN_REASON_OPTIONS]}
                        value={answer.return_reasons ?? (answer.return_reason ? [answer.return_reason] : [])}
                        onChange={(values) => onChange('return_reasons', values)}
                    />

                    {(answer.return_reasons?.includes('other') || answer.return_reason === 'other') && (
                        <Input.TextArea
                            maxLength={2000}
                            rows={3}
                            placeholder="Укажите причину"
                            value={answer.return_reason_text ?? ''}
                            onChange={(event) =>
                                onChange(
                                    'return_reason_text',
                                    event.target.value,
                                )
                            }
                        />
                    )}
                </>
            )}

            <Button
                type="primary"
                className={styles.surveySaveButton}
                onClick={onSave}>
                Сохранить ответ
            </Button>
        </div>
    );
}

export default SurveyProduct;