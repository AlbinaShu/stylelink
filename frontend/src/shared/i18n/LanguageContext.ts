import { createContext, useContext } from 'react';

export type Language = 'ru' | 'en';
export type Params = Record<string, string | number>;

export interface LanguageContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  t: (russian: string, params?: Params) => string;
}

export const LanguageContext = createContext<LanguageContextValue | null>(null);

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('LanguageProvider is missing');
  return context;
}
