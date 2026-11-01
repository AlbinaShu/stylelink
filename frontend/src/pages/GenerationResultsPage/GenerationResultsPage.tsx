import {
    Alert,
    Empty,
    Spin,
} from 'antd';
import {
    useEffect,
    useState,
} from 'react';
import {
    Navigate,
    useParams,
} from 'react-router-dom';

import {
    getGeneration,
    getGenerationOutfits,
} from '../../features/outfit-generation/api/generation.api';
import type {
    IGeneration,
    IOutfit,
} from '../../features/outfit-generation/types';
import GenerationResults from '../../features/outfit-generation/components/GenerationResults/GenerationResults';
import AppBottomNav from '../../shared/ui/AppBottomNav/AppBottomNav';
import AppHeader from '../../shared/ui/AppHeader/AppHeader';

import styles from './GenerationResultsPage.module.css';

function GenerationResultsPage() {
    const { generationId } = useParams<{
        generationId: string;
    }>();

    const [outfits, setOutfits] = useState<IOutfit[]>([]);
    const [generation, setGeneration] = useState<IGeneration | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (!generationId) {
            return;
        }

        let cancelled = false;

        const loadOutfits = async () => {
            try {
                setIsLoading(true);
                setError(null);

                const [data, generationData] = await Promise.all([
                    getGenerationOutfits(generationId),
                    getGeneration(generationId),
                ]);

                if (cancelled) {
                    return;
                }

                setOutfits(data);
                setGeneration(generationData);

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
                            shoeSize={generation?.shoe_size ?? null}
                        />
                    )}
            </main>

            <AppBottomNav />
        </div>
    );
}

export default GenerationResultsPage;