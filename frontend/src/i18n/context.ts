import { createContext } from 'react'
import type { LanguagePreferenceCode } from './languages'

export type I18nValue = {
  language: LanguagePreferenceCode
  setLanguage: (language: LanguagePreferenceCode) => void
  t: (text: string, values?: Record<string, string | number>) => string
}

export const I18nContext = createContext<I18nValue | null>(null)
