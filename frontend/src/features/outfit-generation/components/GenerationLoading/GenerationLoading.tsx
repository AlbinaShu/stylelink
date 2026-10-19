import { useEffect, useMemo, useRef, useState } from 'react';
import { LoadingOutlined } from '@ant-design/icons';
import {
    Button,
    Progress,
    Spin,
    Typography,
} from 'antd';

import {
    getGeneration,
} from '../../api/generation.api';
import {
    type GenerationStatus,
} from '../../types';

import styles from './GenerationLoading.module.css';

const { Text, Title } = Typography;

interface IGenerationLoadingProps {
    generationId: string;
    onCompleted: () => void;
    onFailed: () => void;
    onCancel: () => void;
}

type ActiveGenerationStatus = Exclude<
    GenerationStatus,
    'completed' | 'failed'
>;

interface IGenerationStep {
    minProgress: number;
    maxProgress: number;
    text: string;
}

const GENERATION_STATUS_ORDER: ActiveGenerationStatus[] = [
    'generating_queries',
    'searching_products',
    'forming_outfits',
    'collecting_fit_data',
    'predicting_fit',
];

const GENERATION_STEPS: Record<
    ActiveGenerationStatus,
    IGenerationStep
> = {
    generating_queries: {
        minProgress: 5,
        maxProgress: 20,
        text: 'Подбираем поисковые запросы...',
    },
    searching_products: {
        minProgress: 20,
        maxProgress: 50,
        text: 'Ищем лучшие вещи на маркетплейсах...',
    },
    forming_outfits: {
        minProgress: 50,
        maxProgress: 70,
        text: 'Собираем стильные образы...',
    },
    collecting_fit_data: {
        minProgress: 70,
        maxProgress: 82,
        text: 'Анализируем отзывы о посадке...',
    },
    predicting_fit: {
        minProgress: 82,
        maxProgress: 95,
        text: 'Определяем подходящие размеры...',
    },
};

const POLLING_INTERVAL = 2500;
const PROGRESS_INTERVAL = 1400;
const COMPLETED_DELAY = 400;

function isActiveStatus(
    status: GenerationStatus,
): status is ActiveGenerationStatus {
    return GENERATION_STATUS_ORDER.includes(
        status as ActiveGenerationStatus,
    );
}

function GenerationLoading({
    generationId,
    onCompleted,
    onFailed,
    onCancel,
}: IGenerationLoadingProps) {
    const [status, setStatus] =
        useState<ActiveGenerationStatus>(
            'generating_queries',
        );

    const [progress, setProgress] = useState(
        GENERATION_STEPS.generating_queries.minProgress,
    );

    const [isPollingError, setIsPollingError] =
        useState(false);

    const onCompletedRef = useRef(onCompleted);
    const onFailedRef = useRef(onFailed);

    useEffect(() => {
        onCompletedRef.current = onCompleted;
    }, [onCompleted]);

    useEffect(() => {
        onFailedRef.current = onFailed;
    }, [onFailed]);

    useEffect(() => {
        let pollingTimer: number | undefined;
        let completedTimer: number | undefined;
        let cancelled = false;

        const poll = async () => {
            try {
                const generation =
                    await getGeneration(generationId);

                if (cancelled) {
                    return;
                }

                setIsPollingError(false);

                const nextStatus = generation.status;

                if (nextStatus === 'completed') {
                    setProgress(100);

                    completedTimer = window.setTimeout(
                        () => {
                            if (!cancelled) {
                                onCompletedRef.current();
                            }
                        },
                        COMPLETED_DELAY,
                    );

                    return;
                }

                if (nextStatus === 'failed') {
                    onFailedRef.current();
                    return;
                }

                if (isActiveStatus(nextStatus)) {
                    setStatus(nextStatus);

                    const nextStep =
                        GENERATION_STEPS[nextStatus];

                    setProgress((current) =>
                        Math.max(
                            current,
                            nextStep.minProgress,
                        ),
                    );
                }
            } catch {
                if (!cancelled) {
                    setIsPollingError(true);
                }
            }

            if (!cancelled) {
                pollingTimer = window.setTimeout(
                    poll,
                    POLLING_INTERVAL,
                );
            }
        };

        void poll();

        return () => {
            cancelled = true;

            if (pollingTimer !== undefined) {
                window.clearTimeout(pollingTimer);
            }

            if (completedTimer !== undefined) {
                window.clearTimeout(completedTimer);
            }
        };
    }, [generationId]);

    useEffect(() => {
        const step = GENERATION_STEPS[status];

        const timer = window.setInterval(() => {
            setProgress((current) => {
                const limit =
                    step.maxProgress - 1;

                if (current >= limit) {
                    return current;
                }

                const remaining =
                    limit - current;

                const increment =
                    remaining > 10 ? 2 : 1;

                return Math.min(
                    current + increment,
                    limit,
                );
            });
        }, PROGRESS_INTERVAL);

        return () => {
            window.clearInterval(timer);
        };
    }, [status]);

    const step = GENERATION_STEPS[status];

    const currentStep = useMemo(
        () =>
            GENERATION_STATUS_ORDER.indexOf(
                status,
            ) + 1,
        [status],
    );

    return (
        <div className={styles.root}>
            <div className={styles.content}>
                <div className={styles.loader}>
                    <Spin
                        indicator={
                            <LoadingOutlined spin />
                        }
                        size="large"
                    />
                </div>

                <Title
                    level={3}
                    className={styles.title}
                >
                    Создаём ваши образы
                </Title>

                <Text className={styles.description}>
                    {step.text}
                </Text>

                <div className={styles.progressBlock}>
                    <div className={styles.progressHeader}>
                        <Text
                            className={
                                styles.progressLabel
                            }
                        >
                            Этап {currentStep} из{' '}
                            {
                                GENERATION_STATUS_ORDER.length
                            }
                        </Text>

                        <Text
                            strong
                            className={
                                styles.progressValue
                            }
                        >
                            {progress}%
                        </Text>
                    </div>

                    <Progress
                        percent={progress}
                        showInfo={false}
                        strokeLinecap="round"
                        className={styles.progress}
                    />
                </div>

                {isPollingError && (
                    <Text
                        className={
                            styles.connectionMessage
                        }
                    >
                        Восстанавливаем соединение...
                    </Text>
                )}

                <Text className={styles.hint}>
                    Подбор может занять некоторое время.
                    Страницу можно оставить открытой.
                </Text>

                <Button
                    type="text"
                    className={styles.cancelButton}
                    onClick={onCancel}
                >
                    Отменить
                </Button>
            </div>
        </div>
    );
}

export default GenerationLoading;