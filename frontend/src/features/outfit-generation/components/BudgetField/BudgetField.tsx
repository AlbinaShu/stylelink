import {
    Card,
    InputNumber,
    Slider,
    Typography,
} from 'antd';

import styles from './BudgetField.module.css';
import { useLanguage } from '../../../../shared/i18n/LanguageContext';

const { Text } = Typography;

interface IBudgetFieldProps {
    value: number;
    onChange: (value: number) => void;
}

const MIN_BUDGET = 500;
const MAX_BUDGET = 100000;

function BudgetField({
    value,
    onChange,
}: IBudgetFieldProps) {
    const { t } = useLanguage();
    return (
        <div className={styles.root}>
            <Text className={styles.label}>
                {t('Бюджет')} <span>*</span>
            </Text>

            <Card className={styles.card}>
                <div className={styles.inputWrapper}>
                    <InputNumber
                        min={MIN_BUDGET}
                        max={MAX_BUDGET}
                        controls={false}
                        value={value}
                        onChange={(nextValue) => {
                            if (nextValue !== null) {
                                onChange(nextValue);
                            }
                        }}
                        className={styles.input}
                    />

                    <Text className={styles.currency}>
                        ₽
                    </Text>
                </div>

                <Slider
                    min={MIN_BUDGET}
                    max={MAX_BUDGET}
                    step={500}
                    value={value}
                    tooltip={{ formatter: null }}
                    onChange={onChange}
                    className={styles.slider}
                />

                <div className={styles.range}>
                    <Text>500 ₽</Text>
                    <Text>100 000 ₽</Text>
                </div>
            </Card>
        </div>
    );
}

export default BudgetField;
