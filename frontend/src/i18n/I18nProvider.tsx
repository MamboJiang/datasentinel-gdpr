import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { I18nContext, type I18nValue } from './context'
import { defaultLanguagePreferenceCode, isLanguagePreferenceCode, type LanguagePreferenceCode } from './languages'
import { selectedTemplates, supplementalTranslations, translations } from './translations'

const storageKey = 'datasentinel-language-preference'

function getStoredLanguagePreference(): LanguagePreferenceCode {
  if (typeof window === 'undefined') {
    return defaultLanguagePreferenceCode
  }

  const storedLanguage = window.localStorage.getItem(storageKey)
  return isLanguagePreferenceCode(storedLanguage) ? storedLanguage : defaultLanguagePreferenceCode
}

function interpolate(text: string, values: Record<string, string | number> | undefined) {
  if (!values) {
    return text
  }

  return Object.entries(values).reduce((next, [key, value]) => next.replaceAll(`{{${key}}}`, String(value)), text)
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguage] = useState<LanguagePreferenceCode>(getStoredLanguagePreference)

  useEffect(() => {
    document.documentElement.lang = language
    document.documentElement.dataset.languagePreference = language
    window.localStorage.setItem(storageKey, language)
  }, [language])

  const value = useMemo<I18nValue>(() => ({
    language,
    setLanguage,
    t: (text, values) => interpolate(
      text === '{{language}} selected'
        ? selectedTemplates[language]
        : translations[language][text] ?? supplementalTranslations[language]?.[text] ?? text,
      values,
    ),
  }), [language])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}
