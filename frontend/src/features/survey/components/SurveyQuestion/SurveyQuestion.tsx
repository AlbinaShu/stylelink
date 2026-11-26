import { Radio, Typography } from 'antd';
import type { ISurveyOption } from '../../configurations/survey-questions';
import styles from './SurveyQuestion.module.css';
import { useLanguage } from '../../../../shared/i18n/LanguageContext';

const { Text } = Typography;

interface ISurveyQuestionProps<T extends string> {
    title: string;
    value?: T | null;
    options: readonly ISurveyOption<T>[];
    onChange: (value: T) => void;
}

function SurveyQuestion<T extends string>({
    title,
    value,
    options,
    onChange,
}: ISurveyQuestionProps<T>) {
    const { t } = useLanguage();
    return (
        <div className={styles.question}>
            <Text strong>{t(title)}</Text>

            <Radio.Group
                className={styles.radioGroup}
                value={value ?? undefined}
                onChange={(event) => onChange(event.target.value as T)}
            >
                {options.map((option) => (
                    <Radio
                        key={option.value}
                        value={option.value}
                    >
                        {t(option.label)}
                    </Radio>
                ))}
            </Radio.Group>
        </div>
    );
}

export default SurveyQuestion;
