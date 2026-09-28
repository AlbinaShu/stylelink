import {
    Input,
    Typography,
} from 'antd';

import styles from './CustomPrompt.module.css';

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
    return (
        <div className={styles.root}>
            <Text className={styles.title}>
                Свой запрос
            </Text>

            <Text className={styles.description}>
                Заполните (≥5 символов), чтобы заменить выбор повода и стиля
            </Text>

            <TextArea
                value={value}
                maxLength={500}
                rows={5}
                showCount
                placeholder="Например: хочу образ в стиле 90-х для похода в клуб..."
                onChange={(event) => onChange(event.target.value)}
                className={styles.input}
            />
        </div>
    );
}

export default CustomPrompt;
