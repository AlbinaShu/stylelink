import { useCallback } from 'react';
import {
    Navigate,
    useNavigate,
    useParams,
} from 'react-router-dom';

import GenerationLoading from '../../features/outfit-generation/components/GenerationLoading/GenerationLoading';

function GenerationLoadingPage() {
    const { generationId } = useParams<{
        generationId: string;
    }>();

    const navigate = useNavigate();

    const handleCompleted = useCallback(() => {
        if (!generationId) {
            return;
        }

        navigate(
            `/outfit-generation/${generationId}/results`,
            {
                replace: true,
            },
        );
    }, [generationId, navigate]);

    const handleFailed = useCallback(() => {
        navigate('/outfit-generation', {
            replace: true,
            state: {
                generationError: true,
            },
        });
    }, [navigate]);

    const handleCancel = useCallback(() => {
        navigate('/outfit-generation');
    }, [navigate]);

    if (!generationId) {
        return (
            <Navigate
                to="/outfit-generation"
                replace
            />
        );
    }

    return (
        <GenerationLoading
            generationId={generationId}
            onCompleted={handleCompleted}
            onFailed={handleFailed}
            onCancel={handleCancel}
        />
    );
}

export default GenerationLoadingPage;