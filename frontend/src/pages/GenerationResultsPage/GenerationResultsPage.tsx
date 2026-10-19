import {
    Alert,
    Empty,
    Spin,
} from 'antd';
import {
    useEffect,
    useRef,
    useState,
} from 'react';
import {
    Navigate,
    useParams,
} from 'react-router-dom';

import {
    getGenerationOutfits,
} from '../../features/outfit-generation/api/generation.api';
import type { IOutfit } from '../../features/outfit-generation/types';
import GenerationResults from '../../features/outfit-generation/components/GenerationResults/GenerationResults';
import { sendRecommendationView } from '../../features/experiment-events/api/experiment-events.api';
import { getDeviceType, getSessionId } from '../../shared/utils/session';
import AppBottomNav from '../../shared/ui/AppBottomNav/AppBottomNav';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';

import styles from './GenerationResultsPage.module.css';

function GenerationResultsPage() {
    const { generationId } = useParams<{
        generationId: string;
    }>();

    const [outfits, setOutfits] = useState<IOutfit[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const viewSentRef = useRef(false);

    useEffect(() => {
        if (!generationId) {
            return;
        }

        let cancelled = false;

        const loadOutfits = async () => {
            try {
                setIsLoading(true);
                setError(null);

                const data = await getGenerationOutfits(
                    generationId,
                );

                if (cancelled) {
                    return;
                }

                setOutfits(data);

                if (!viewSentRef.current && data.length > 0) {
                    viewSentRef.current = true;
                    void sendRecommendationView({
                        session_id: getSessionId(),
                        timestamp: new Date().toISOString(),
                        device_type: getDeviceType(),
                        outfitItems: data.flatMap((outfit) =>
                            outfit.items.map((item) => ({
                                product_id: item.product_id,
                                name: item.name,
                                price: item.price,
                                category: item.category ?? 'unknown',
                                recommended_size: item.recommended_size,
                                fit_signal: item.fit?.fit_signal ?? null,
                                confidence: item.fit?.confidence ?? null,
                                num_reviews: null,
                            })),
                        ),
                    }).catch(() => undefined);
                }
            } catch {
                if (cancelled) {
                    return;
                }

                setError(
                    'Не удалось загрузить результаты подбора.',
                );
            } finally {
                if (!cancelled) {
                    setIsLoading(false);
                }
            }
        };

        void loadOutfits();

        return () => {
            cancelled = true;
        };
    }, [generationId]);

    if (!generationId) {
        return (
            <Navigate
                to="/outfit-generation"
                replace
            />
        );
    }

    return (
        <div className={styles.page}>
            <AppHeader
                title={
                    isLoading
                        ? 'Результаты подбора'
                        : `${outfits.length} образов готово`
                }
                showBack
            />

            <main className={styles.content}>
                {isLoading && (
                    <div className={styles.state}>
                        <Spin size="large" />
                    </div>
                )}

                {!isLoading && error && (
                    <Alert
                        type="error"
                        showIcon
                        message={error}
                    />
                )}

                {!isLoading &&
                    !error &&
                    outfits.length === 0 && (
                        <Empty
                            description="Подходящих образов не найдено"
                        />
                    )}

                {!isLoading &&
                    !error &&
                    outfits.length > 0 && (
                        <GenerationResults
                            outfits={outfits}
                        />
                    )}
            </main>

            <AppBottomNav />
        </div>
    );
}

export default GenerationResultsPage;