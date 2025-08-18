import React from 'react'
import { useLanguage } from '@/contexts/LanguageContext'
import { Button } from '@/components/ui/button'
import { Globe } from 'lucide-react'

export const LanguageSelector: React.FC = () => {
  const { language, setLanguage, languages } = useLanguage()

  const currentLanguage = languages.find(lang => lang.code === language)

  const handleLanguageChange = () => {
    // Toggle between English and Chinese
    const newLanguage = language === 'en' ? 'zh' : 'en'
    setLanguage(newLanguage)
  }

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleLanguageChange}
      className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
      title={`Switch to ${language === 'en' ? '中文' : 'English'}`}
    >
      <Globe className="w-4 h-4" />
      <span className="text-sm font-medium">
        {currentLanguage?.nativeName || 'EN'}
      </span>
    </Button>
  )
}