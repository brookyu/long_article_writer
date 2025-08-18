import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useTranslation } from 'react-i18next'

interface LanguageContextType {
  language: string
  setLanguage: (lang: string) => void
  languages: { code: string; name: string; nativeName: string }[]
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

export const useLanguage = () => {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}

interface LanguageProviderProps {
  children: ReactNode
}

export const LanguageProvider: React.FC<LanguageProviderProps> = ({ children }) => {
  const { i18n } = useTranslation()
  const [language, setLanguageState] = useState(i18n.language || 'en')

  const languages = [
    { code: 'en', name: 'English', nativeName: 'English' },
    { code: 'zh', name: 'Chinese', nativeName: '中文' }
  ]

  // Load language preference from settings API
  useEffect(() => {
    const loadLanguageFromSettings = async () => {
      try {
        const response = await fetch('/api/settings/config')
        if (response.ok) {
          const data = await response.json()
          const savedLanguage = data.ui_settings?.language || 'en'
          setLanguage(savedLanguage)
        }
      } catch (error) {
        console.error('Failed to load language from settings:', error)
      }
    }

    loadLanguageFromSettings()
  }, [])

  const setLanguage = async (lang: string) => {
    try {
      // Update i18next
      await i18n.changeLanguage(lang)
      setLanguageState(lang)

      // Save to backend settings
      const currentSettingsResponse = await fetch('/api/settings/config')
      if (currentSettingsResponse.ok) {
        const currentSettings = await currentSettingsResponse.json()
        
        const updatedSettings = {
          ...currentSettings,
          ui_settings: {
            ...currentSettings.ui_settings,
            language: lang
          }
        }

        await fetch('/api/settings/config', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(updatedSettings)
        })
      }
    } catch (error) {
      console.error('Failed to change language:', error)
    }
  }

  return (
    <LanguageContext.Provider value={{ language, setLanguage, languages }}>
      {children}
    </LanguageContext.Provider>
  )
}