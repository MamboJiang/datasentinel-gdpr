export const defaultLanguagePreferenceCode = 'en'

export const languagePreferenceOptions = [
  { code: 'en', label: 'English', nativeLabel: 'English' },
  { code: 'bg', label: 'Bulgarian', nativeLabel: 'Български' },
  { code: 'hr', label: 'Croatian', nativeLabel: 'Hrvatski' },
  { code: 'cs', label: 'Czech', nativeLabel: 'Čeština' },
  { code: 'da', label: 'Danish', nativeLabel: 'Dansk' },
  { code: 'nl', label: 'Dutch', nativeLabel: 'Nederlands' },
  { code: 'et', label: 'Estonian', nativeLabel: 'Eesti' },
  { code: 'fi', label: 'Finnish', nativeLabel: 'Suomi' },
  { code: 'fr', label: 'French', nativeLabel: 'Français' },
  { code: 'de', label: 'German', nativeLabel: 'Deutsch' },
  { code: 'el', label: 'Greek', nativeLabel: 'Ελληνικά' },
  { code: 'hu', label: 'Hungarian', nativeLabel: 'Magyar' },
  { code: 'ga', label: 'Irish', nativeLabel: 'Gaeilge' },
  { code: 'it', label: 'Italian', nativeLabel: 'Italiano' },
  { code: 'lv', label: 'Latvian', nativeLabel: 'Latviešu' },
  { code: 'lt', label: 'Lithuanian', nativeLabel: 'Lietuvių' },
  { code: 'mt', label: 'Maltese', nativeLabel: 'Malti' },
  { code: 'pl', label: 'Polish', nativeLabel: 'Polski' },
  { code: 'pt', label: 'Portuguese', nativeLabel: 'Português' },
  { code: 'ro', label: 'Romanian', nativeLabel: 'Română' },
  { code: 'sk', label: 'Slovak', nativeLabel: 'Slovenčina' },
  { code: 'sl', label: 'Slovenian', nativeLabel: 'Slovenščina' },
  { code: 'es', label: 'Spanish', nativeLabel: 'Español' },
  { code: 'sv', label: 'Swedish', nativeLabel: 'Svenska' },
] as const

export type LanguagePreferenceCode = typeof languagePreferenceOptions[number]['code']

export function isLanguagePreferenceCode(value: string | null): value is LanguagePreferenceCode {
  return languagePreferenceOptions.some(({ code }) => code === value)
}
