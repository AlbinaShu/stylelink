import { Button, Input } from 'antd';
import type { ISurveyAnswerItem } from '../../types';
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
    onChange: (
        key: keyof ISurveyAnswerItem,
        value: string | null,
    ) => void;
    onSave: () => void;
}

function SurveyProduct({
    answer,
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

                    {answer.sizes_ordered === '1' && (
                        <SurveyQuestion
                            title="Какой размер заказали?"
                            value={answer.purchased_size}
                            options={SIZE_CHOICE_OPTIONS}
                            onChange={(value) => onChange('purchased_size', value)}
                        />
                    )}
                </>
            )}

            {answer.order_placed === 'no' && (
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

                            {answer.sizes_in_cart === '1' && (
                                <SurveyQuestion
                                    title="Какой размер был в корзине?"
                                    value={answer.cart_size}
                                    options={SIZE_CHOICE_OPTIONS}
                                    onChange={(value) => onChange('cart_size', value)}
                                />
                            )}
                        </>
                    )}
                </>
            )}

            {(answer.order_placed === 'yes' ||
                answer.order_placed === 'no') && (
                    <SurveyQuestion
                        title="Как подошёл размер?"
                        value={answer.fit_result}
                        options={FIT_OPTIONS}
                        onChange={(value) => onChange('fit_result', value)}
                    />
                )}

            {answer.fit_result &&
                answer.fit_result !== 'unknown' && (
                    <SurveyQuestion
                        title="Что сделали с товаром?"
                        value={answer.action}
                        options={ACTION_OPTIONS}
                        onChange={(value) => onChange('action', value)}
                    />
                )}

            {answer.action === 'returned' && (
                <>
                    <SurveyQuestion
                        title="Почему вернули?"
                        value={answer.return_reason}
                        options={RETURN_REASON_OPTIONS}
                        onChange={(value) =>
                            onChange('return_reason', value)
                        }
                    />

                    {answer.return_reason === 'other' && (
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