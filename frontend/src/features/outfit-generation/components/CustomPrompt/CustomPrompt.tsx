import {
    Input,
    Typography,
} from 'antd';

import styles from './CustomPrompt.module.css';
import { useLanguage } from '../../../../shared/i18n/LanguageContext';

const { Text } = Typography;
const { TextArea } = Input;

interface ICustomPromptProps {
    value: string;
    onChange: (value: string) => void;
}

function CustomPrompt({
    value,
    onChange,
}: ICustomPromptProps) {
    const { t } = useLanguage();
    return (
        <div className={styles.root}>
            <Text className={styles.title}>
                {t('Свой запрос')}
            </Text>

            <Text className={styles.description}>
                {t('Заполните (≥5 символов), чтобы заменить выбор повода и стиля')}
            </Text>

            <TextArea
                value={value}
                maxLength={500}
                rows={5}
                showCount
                placeholder={t('Например: хочу образ в стиле 90-х для похода в клуб...')}
                onChange={(event) => onChange(event.target.value)}
                className={styles.input}
            />
        </div>
    );
}

export default CustomPrompt;
