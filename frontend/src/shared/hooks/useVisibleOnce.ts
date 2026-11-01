import { useEffect, useRef } from 'react';

export function isHalfVisible(element: HTMLElement | null): boolean {
  if (!element || document.visibilityState !== 'visible') return false;
  const rect = element.getBoundingClientRect();
  const width = Math.max(0, Math.min(rect.right, window.innerWidth) - Math.max(rect.left, 0));
  const height = Math.max(0, Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0));
  return rect.width > 0 && rect.height > 0 && width * height / (rect.width * rect.height) >= 0.5;
}

/** Count the block only while at least half is visible in the active tab. */
export function useVisibleOnce<T extends HTMLElement>(key: string, onVisible: () => void) {
  const elementRef = useRef<T>(null);
  const seen = useRef(new Set<string>());
  useEffect(() => {
    const element = elementRef.current;
    if (!element || seen.current.has(key)) return;
    const check = () => {
      if (document.visibilityState !== 'visible' || seen.current.has(key)) return;
      const rect = element.getBoundingClientRect();
      const width = Math.max(0, Math.min(rect.right, window.innerWidth) - Math.max(rect.left, 0));
      const height = Math.max(0, Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0));
      if (rect.width > 0 && rect.height > 0 && width * height / (rect.width * rect.height) >= 0.5) {
        seen.current.add(key);
        onVisible();
      }
    };
    const observer = new IntersectionObserver(check, { threshold: [0, 0.5, 1] });
    observer.observe(element);
    document.addEventListener('visibilitychange', check);
    window.addEventListener('resize', check);
    check();
    return () => {
      observer.disconnect();
      document.removeEventListener('visibilitychange', check);
      window.removeEventListener('resize', check);
    };
  }, [key, onVisible]);
  return elementRef;
}
