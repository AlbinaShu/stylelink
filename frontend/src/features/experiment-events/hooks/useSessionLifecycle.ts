import { useEffect } from 'react';

import { sendSessionEnd } from '../api/experiment-events.api';
import { getDeviceType, getSessionId, getSessionStartedAt } from '../../../shared/utils/session';

export function useSessionLifecycle() {
    useEffect(() => {
        const sessionId = getSessionId();
        const startedAt = getSessionStartedAt();

        const handlePageHide = () => {
            void sendSessionEnd({
                session_id: sessionId,
                timestamp: new Date().toISOString(),
                duration_ms: Math.max(0, Date.now() - startedAt),
                device_type: getDeviceType(),
            });
        };

        window.addEventListener('pagehide', handlePageHide);

        return () => {
            window.removeEventListener('pagehide', handlePageHide);
        };
    }, []);
}