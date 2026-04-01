import React, { createContext, useContext, useState, useEffect } from 'react';
import { LANGUAGES, mapTelegramLang } from '@/i18n/translations';

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [langCode, setLangCode] = useState(() => {
    // 1. Check localStorage first
    const saved = localStorage.getItem('clawquiz_lang');
    if (saved) return saved;
    // 2. Try Telegram user language
    const tgLang = window.Telegram?.WebApp?.initDataUnsafe?.user?.language_code;
    if (tgLang) return mapTelegramLang(tgLang);
    // 3. Try browser language
    const browserLang = navigator.language?.split('-')[0];
    return mapTelegramLang(browserLang) || 'en';
  });

  const setLanguage = (code) => {
    setLangCode(code);
    localStorage.setItem('clawquiz_lang', code);
    // Set RTL for Arabic
    const lang = LANGUAGES.find(l => l.code === code);
    document.documentElement.dir = lang?.rtl ? 'rtl' : 'ltr';
  };

  useEffect(() => {
    const lang = LANGUAGES.find(l => l.code === langCode);
    document.documentElement.dir = lang?.rtl ? 'rtl' : 'ltr';
  }, []);

  return (
    <LanguageContext.Provider value={{ langCode, setLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  return useContext(LanguageContext);
}
