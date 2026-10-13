import {
    ArrowRightOutlined,
    StarOutlined,
} from '@ant-design/icons';
import {
    Button,
    Typography,
} from 'antd';
import { useEffect, useState } from 'react';

import {
    createGeneration,
    getGeneration,
    getGenerationOutfits,
} from '../../api/generation.api';
import type { IOutfit } from '../../api/generation.api';

import type {
    IGenerationForm,
    IGenerationOption,
} from '../../types';
import BodyParameters from '../BodyParameters/BodyParameters';
import BudgetField from '../BudgetField/BudgetField';
import CustomPrompt from '../CustomPrompt/CustomPrompt';
import GenerationResults from '../GenerationResults/GenerationResults';
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
    const [values, setValues] = useState<IGenerationForm>(
        initialValues,
    );
    const [generationId, setGenerationId] = useState<string | null>(null);
    const [status, setStatus] = useState<string | null>(null);
    const [outfits, setOutfits] = useState<IOutfit[] | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (!generationId) {
            return;
        }

        let cancelled = false;
        let timer: ReturnType<typeof setTimeout>;

        const poll = async () => {
            try {
                const generation = await getGeneration(generationId);
                if (cancelled) return;

                setStatus(generation.status);
                if (generation.status === 'completed') {
                    const result = await getGenerationOutfits(generationId);
                    if (!cancelled) setOutfits(result);
                } else if (generation.status !== 'failed') {
                    timer = setTimeout(() => void poll(), 2500);
                }
            } catch {
                if (!cancelled) {
                    setError('Не удалось получить результат. Проверьте соединение с сервером.');
                }
            }
        };

        void poll();
        return () => {
            cancelled = true;
            clearTimeout(timer);
        };
    }, [generationId]);

    const setField = <K extends keyof IGenerationForm>(
        field: K,
        value: IGenerationForm[K],
    ) => {
        setValues((current) => ({
            ...current,
            [field]: value,
        }));
    };

    const promptIsValid = values.prompt.trim().length >= 5;

    const optionsAreValid = Boolean(
        values.occasion && values.style,
    );

    const canGenerate = promptIsValid || optionsAreValid;

    const isGenerating = Boolean(status && status !== 'completed' && status !== 'failed');

    const handleGenerate = async () => {
        if (!canGenerate || isSubmitting || isGenerating) {
            return;
        }

        setIsSubmitting(true);
        setGenerationId(null);
        setStatus(null);
        setOutfits(null);
        setError(null);

        try {
            const generation = await createGeneration(values);
            setStatus(generation.status);
            setGenerationId(generation.id);
        } catch {
            setError('Не удалось отправить запрос. Проверьте соединение с сервером.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
      <>
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

            <div className={styles.submit}>
                <Text className={styles.hint}>
                    Выберите повод и стиль или введите свой запрос (≥5 символов)
                </Text>

                <Button
                    type="primary"
                    size="large"
                    disabled={!canGenerate || isGenerating}
                    loading={isSubmitting || isGenerating}
                    icon={<StarOutlined />}
                    onClick={handleGenerate}
                    className={styles.generateButton}
                >
                    <span>Подобрать образы</span>
                    <ArrowRightOutlined />
                </Button>
            </div>
        </div>
        <GenerationResults status={status} outfits={outfits} error={error} />
      </>
    );
}

export default GenerationForm;
