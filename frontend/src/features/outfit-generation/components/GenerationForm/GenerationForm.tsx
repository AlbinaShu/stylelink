import {
    ArrowRightOutlined,
    StarOutlined,
} from '@ant-design/icons';
import {
    Alert,
    Button,
    Typography,
} from 'antd';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
    createGeneration,
} from '../../api/generation.api';

import type {
    IGenerationForm,
    IGenerationOption,
} from '../../types';

import BodyParameters from '../BodyParameters/BodyParameters';
import BudgetField from '../BudgetField/BudgetField';
import CustomPrompt from '../CustomPrompt/CustomPrompt';
import OptionSelector from '../OptionSelector/OptionSelector';

import styles from './GenerationForm.module.css';

const { Text } = Typography;

const occasionOptions: IGenerationOption[] = [
    {
        value: 'office',
        label: '💼 Офис',
    },
    {
        value: 'date',
        label: '💗 Свидание',
    },
    {
        value: 'walk',
        label: '🚶 Прогулка',
    },
    {
        value: 'event',
        label: '🎉 Мероприятие',
    },
    {
        value: 'travel',
        label: '✈️ Путешествие',
    },
];

const styleOptions: IGenerationOption[] = [
    {
        value: 'business',
        label: '👔 Деловой',
    },
    {
        value: 'casual',
        label: '👕 Кэжуал',
    },
    {
        value: 'sport',
        label: '🏃 Спортивный',
    },
    {
        value: 'romantic',
        label: '🌸 Романтический',
    },
];

const seasonOptions: IGenerationOption[] = [
    {
        value: 'spring-autumn',
        label: 'Весна/Осень',
    },
    {
        value: 'summer',
        label: 'Лето',
    },
    {
        value: 'winter',
        label: 'Зима',
    },
];

const initialValues: IGenerationForm = {
    occasion: null,
    style: null,
    season: null,
    budget: 15000,
    gender: 'female',
    height: null,
    weight: null,
    chest: null,
    waist: null,
    hips: null,
    prompt: '',
};

function GenerationForm() {
    const navigate = useNavigate();

    const [values, setValues] = useState<IGenerationForm>(initialValues);
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const setField = <K extends keyof IGenerationForm>(
        field: K,
        value: IGenerationForm[K],
    ) => {
        setValues((current) => ({
            ...current,
            [field]: value,
        }));

        if (error) {
            setError(null);
        }
    };

    const promptIsValid = values.prompt.trim().length >= 5;
    const optionsAreValid = Boolean(values.occasion && values.style);
    const canGenerate = promptIsValid || optionsAreValid;

    const handleGenerate = async () => {
        if (!canGenerate || isSubmitting) {
            return;
        }

        setIsSubmitting(true);
        setError(null);

        try {
            const generation = await createGeneration(values);

            navigate(`/outfit-generation/${generation.id}/loading`);
        } catch {
            setError('Не удалось запустить подбор. Проверьте соединение с сервером.');
            setIsSubmitting(false);
        }
    };

    return (
        <div className={styles.form}>
            <OptionSelector
                label="Повод"
                required
                value={values.occasion}
                columns={2}
                options={occasionOptions}
                onChange={(value) => {
                    setField('occasion', value);
                }}
            />

            <OptionSelector
                label="Стиль"
                required
                value={values.style}
                options={styleOptions}
                columns={2}
                onChange={(value) => {
                    setField('style', value);
                }}
            />

            <OptionSelector
                label="Сезон"
                value={values.season}
                options={seasonOptions}
                columns={3}
                onChange={(value) => {
                    setField('season', value);
                }}
            />

            <BudgetField
                value={values.budget}
                onChange={(value) => {
                    setField('budget', value);
                }}
            />

            <BodyParameters
                value={{
                    gender: values.gender,
                    height: values.height,
                    weight: values.weight,
                    chest: values.chest,
                    waist: values.waist,
                    hips: values.hips,
                }}
                onChange={(field, value) => {
                    setField(field, value as never);
                }}
            />

            <CustomPrompt
                value={values.prompt}
                onChange={(value) => {
                    setField('prompt', value);
                }}
            />

            {error && (
                <Alert
                    type="error"
                    showIcon
                    message={error}
                    className={styles.error}
                />
            )}

            <div className={styles.submit}>
                <Text className={styles.hint}>
                    Выберите повод и стиль или введите свой запрос (≥5 символов)
                </Text>

                <Button
                    type="primary"
                    size="large"
                    disabled={!canGenerate || isSubmitting}
                    loading={isSubmitting}
                    icon={<StarOutlined />}
                    onClick={handleGenerate}
                    className={styles.generateButton}
                >
                    <span>
                        Подобрать образы
                    </span>

                    {!isSubmitting && (
                        <ArrowRightOutlined />
                    )}
                </Button>
            </div>
        </div>
    );
}

export default GenerationForm;