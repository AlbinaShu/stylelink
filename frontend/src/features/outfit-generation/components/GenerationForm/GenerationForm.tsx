import {
    ArrowRightOutlined,
    StarOutlined,
    UserOutlined,
} from '@ant-design/icons';
import {
    Alert,
    Button,
    Modal,
    Typography,
} from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import {
    createGeneration,
    isGenerationLimitError,
} from '../../api/generation.api';

import { useProfile } from '../../../profile/hooks/useProfile';

import type {
    IGenerationForm,
    IGenerationOption,
} from '../../types';

import BodyParameters from '../BodyParameters/BodyParameters';
import BudgetField from '../BudgetField/BudgetField';
import CustomPrompt from '../CustomPrompt/CustomPrompt';
import OptionSelector from '../OptionSelector/OptionSelector';

import styles from './GenerationForm.module.css';
import { useLanguage } from '../../../../shared/i18n/LanguageContext';

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
    shoe_size: null,
    chest: null,
    waist: null,
    hips: null,
    prompt: '',
};

function GenerationForm() {
    const navigate = useNavigate();
    const { t } = useLanguage();

    const {
        profile,
        loadProfile,
        updateProfile,
    } = useProfile();

    const [values, setValues] = useState<IGenerationForm>(initialValues);
    const [error, setError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    const profileAppliedRef = useRef(false);

    useEffect(() => {
        if (!profile) {
            void loadProfile();
        }
    }, [profile]);

    useEffect(() => {
        if (!profile || profileAppliedRef.current) {
            return;
        }

        setValues((current) => ({
            ...current,
            gender: profile.gender ?? current.gender,
            height: profile.height ?? current.height,
            weight: profile.weight ?? current.weight,
            shoe_size: profile.shoe_size ?? current.shoe_size,
            chest: profile.chest ?? current.chest,
            waist: profile.waist ?? current.waist,
            hips: profile.hips ?? current.hips,
        }));

        profileAppliedRef.current = true;
    }, [profile]);

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

    const bodyValuesAreComplete = Boolean(
        values.gender &&
        values.height != null &&
        values.weight != null &&
        values.shoe_size != null &&
        values.chest != null &&
        values.waist != null &&
        values.hips != null
    );

    const requestIsValid = promptIsValid || optionsAreValid;
    const canGenerate = requestIsValid && bodyValuesAreComplete;

    const profileBodyIsComplete = Boolean(
        profile?.gender &&
        profile?.height != null &&
        profile?.weight != null &&
        profile?.shoe_size != null &&
        profile?.chest != null &&
        profile?.waist != null &&
        profile?.hips != null
    );

    const createOutfitGeneration = async () => {
        setIsSubmitting(true);
        setError(null);

        try {
            const generation = await createGeneration(values);

            navigate(`/outfit-generation/${generation.id}/loading`);
        } catch (error) {
            if (isGenerationLimitError(error)) {
                navigate('/plans', { replace: true });
                return;
            }
            setError(t('Не удалось запустить подбор. Проверьте соединение с сервером.'));
            setIsSubmitting(false);
        }
    };

    const saveBodyParametersAndGenerate = async () => {
        setIsSubmitting(true);
        setError(null);

        try {
            await updateProfile({
                gender: values.gender!,
                height: values.height!,
                weight: values.weight!,
                shoe_size: values.shoe_size,
                chest: values.chest!,
                waist: values.waist!,
                hips: values.hips!,
            });

            const generation = await createGeneration(values);

            navigate(`/outfit-generation/${generation.id}/loading`);
        } catch (error) {
            if (isGenerationLimitError(error)) {
                navigate('/plans', { replace: true });
                return;
            }
            setError(
                t('Не удалось сохранить параметры или запустить подбор. Проверьте соединение с сервером.'),
            );
            setIsSubmitting(false);
        }
    };

    const handleGenerate = async () => {
        if (!canGenerate || isSubmitting) {
            return;
        }

        if (!profileBodyIsComplete && bodyValuesAreComplete) {
            Modal.confirm({
                title: t('Сохранить параметры тела?'),
                icon: <UserOutlined style={{ color: 'var(--primary)' }} />,
                content:
                    t('Сохранить эти данные в профиле, чтобы автоматически использовать их при следующих подборах?'),
                okText: t('Сохранить'),
                cancelText: t('Не сейчас'),
                centered: true,
                okButtonProps: {
                    style: {
                        background: 'var(--primary)',
                        borderColor: 'var(--primary)',
                        boxShadow: 'none',
                    },
                },
                onOk: async () => {
                    await saveBodyParametersAndGenerate();
                },
                onCancel: () => {
                    void createOutfitGeneration();
                },
            });

            return;
        }

        await createOutfitGeneration();
    };

    return (
        <div className={styles.form}>
            <OptionSelector
                label={t('Повод')}
                required
                value={values.occasion}
                columns={2}
                options={occasionOptions.map((option) => ({ ...option, label: t(option.label) }))}
                onChange={(value) => {
                    setField('occasion', value);
                }}
            />

            <OptionSelector
                label={t('Стиль')}
                required
                value={values.style}
                options={styleOptions.map((option) => ({ ...option, label: t(option.label) }))}
                columns={2}
                onChange={(value) => {
                    setField('style', value);
                }}
            />

            <OptionSelector
                label={t('Сезон')}
                value={values.season}
                options={seasonOptions.map((option) => ({ ...option, label: t(option.label) }))}
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
                    shoe_size: values.shoe_size,
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
                    {t('Заполните параметры тела и выберите повод и стиль или введите свой запрос (≥5 символов)')}
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
                        {t('Подобрать образы')}
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
