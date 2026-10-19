const SESSION_ID_KEY = 'ai-stylelink-session-id';
const SESSION_STARTED_AT_KEY = 'ai-stylelink-session-started-at';

export function getSessionId(): string {
  let sessionId = sessionStorage.getItem(SESSION_ID_KEY);

  if (!sessionId) {
    sessionId = crypto.randomUUID();
    sessionStorage.setItem(SESSION_ID_KEY, sessionId);
  }

  return sessionId;
}

export function getSessionStartedAt(): number {
  const stored = sessionStorage.getItem(SESSION_STARTED_AT_KEY);
  const parsed = stored ? Number(stored) : Number.NaN;

  if (Number.isFinite(parsed)) {
    return parsed;
  }

  const startedAt = Date.now();
  sessionStorage.setItem(SESSION_STARTED_AT_KEY, String(startedAt));
  return startedAt;
}

export function getDeviceType(): string {
  if (window.innerWidth < 768) return 'mobile';
  if (window.innerWidth < 1024) return 'tablet';
  
  return 'desktop';
}

export function getSessionDurationMs(): number {
  return Math.max(0, Date.now() - getSessionStartedAt());
}