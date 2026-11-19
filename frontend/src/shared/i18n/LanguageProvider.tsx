import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import enUS from 'antd/locale/en_US';
import ruRU from 'antd/locale/ru_RU';
import { ConfigProvider } from 'antd';
import { translate } from './translations';
import { LanguageContext, type Language, type Params } from './LanguageContext';

const STORAGE_KEY = 'stylelink-language';

function storedLanguage(): Language {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'ru';
  } catch {
    return 'ru';
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<Language>(storedLanguage);

  useEffect(() => {
    document.documentElement.lang = language;
    try {
      localStorage.setItem(STORAGE_KEY, language);
    } catch {
      // The interface still works when storage is unavailable.
    }
  }, [language]);

  const t = useCallback((russian: string, params: Params = {}) =>
    translate(language, russian, params), [language]);

  const value = useMemo(() => ({ language, setLanguage, t }), [language, t]);

  return (
    <LanguageContext.Provider value={value}>
      <ConfigProvider
        locale={language === 'en' ? enUS : ruRU}
        theme={{ token: { colorPrimary: '#8B3045', borderRadius: 13, fontFamily: 'Inter, Arial, sans-serif' } }}
      >
        {children}
      </ConfigProvider>
    </LanguageContext.Provider>
  );
}
