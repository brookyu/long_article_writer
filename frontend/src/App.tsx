import { BrowserRouter as Router, Routes, Route, Link, useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CollectionsPage } from '@/pages/CollectionsPage'
import { CollectionDetailPage } from '@/pages/CollectionDetailPage'
import { ArticlesPage } from '@/pages/ArticlesPage'
import { WritingPage } from '@/pages/WritingPage'
import { SettingsPage } from '@/pages/SettingsPage'
import { ChatPage } from '@/pages/ChatPage'
import TestUploadPage from '@/pages/TestUploadPage'
import { LanguageProvider } from '@/contexts/LanguageContext'
import { LanguageSelector } from '@/components/ui/LanguageSelector'
import './i18n'
import './App.css'

function App() {
  return (
    <LanguageProvider>
      <Router>
        <div className="min-h-screen bg-background">
          <AppContent />
        </div>
      </Router>
    </LanguageProvider>
  )
}

function AppContent() {
  const { t } = useTranslation()

  return (
    <>
      {/* Navigation */}
      <nav className="border-b bg-card">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <Link to="/" className="text-xl font-bold">
              {t('navigation.appTitle')}
            </Link>
            <div className="flex items-center space-x-4">
              <Link 
                to="/collections" 
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {t('navigation.collections')}
              </Link>
              <Link 
                to="/articles/1" 
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {t('navigation.articles')}
              </Link>
              <Link 
                to="/settings" 
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {t('navigation.settings')}
              </Link>
              <Link 
                to="/test-upload" 
                className="text-blue-600 hover:text-blue-800 font-medium transition-colors"
              >
                🚀 Test Upload
              </Link>
              <Link 
                to="/" 
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                {t('navigation.home')}
              </Link>
              <LanguageSelector />
            </div>
          </div>
        </div>
      </nav>

      <main>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/collections" element={<CollectionsPage />} />
          <Route path="/collections/:id" element={<CollectionDetailPage />} />
          <Route path="/articles/:collectionId" element={<ArticlesPageWrapper />} />
          <Route path="/write/:collectionId" element={<WritingPage />} />
          <Route path="/chat/:collectionId" element={<ChatPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/test-upload" element={<TestUploadPage />} />
        </Routes>
      </main>
    </>
  )
}

function ArticlesPageWrapper() {
  const { collectionId } = useParams<{ collectionId: string }>()
  return <ArticlesPage collectionId={parseInt(collectionId || '1')} />
}

function HomePage() {
  const { t } = useTranslation()
  
  return (
    <div className="container mx-auto py-8">
      <div className="text-center max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-foreground mb-4">
          {t('home.title')}
        </h1>
        <p className="text-lg text-muted-foreground mb-8">
          {t('home.subtitle')}
        </p>
        <div className="flex flex-wrap justify-center gap-2 mb-8">
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
            {t('home.features.generation')}
          </span>
          <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
            {t('home.features.citations')}
          </span>
          <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
            {t('home.features.multilang')}
          </span>
          <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm font-medium">
            {t('home.features.references')}
          </span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-card p-6 rounded-lg border">
            <h2 className="text-xl font-semibold mb-4">{t('home.knowledgeBase.title')}</h2>
            <p className="text-muted-foreground mb-4">
              {t('home.knowledgeBase.description')}
            </p>
            <Link 
              to="/collections" 
              className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors h-9 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {t('home.knowledgeBase.button')}
            </Link>
          </div>
          
          <div className="bg-card p-6 rounded-lg border">
            <h2 className="text-xl font-semibold mb-4">{t('home.aiGeneration.title')}</h2>
            <p className="text-muted-foreground mb-4">
              {t('home.aiGeneration.description')}
            </p>
            <Link 
              to="/articles/1"
              className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors h-9 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              {t('home.aiGeneration.button')}
            </Link>
          </div>
        </div>

        <div className="bg-card p-6 rounded-lg border">
          <h2 className="text-xl font-semibold mb-4">{t('home.gettingStarted.title')}</h2>
          <div className="text-left space-y-3">
            <div className="flex items-start gap-3">
              <span className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium flex-shrink-0">1</span>
              <p className="text-muted-foreground">{t('home.gettingStarted.step1')}</p>
            </div>
            <div className="flex items-start gap-3">
              <span className="bg-muted text-muted-foreground rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium flex-shrink-0">2</span>
              <p className="text-muted-foreground">{t('home.gettingStarted.step2')}</p>
            </div>
            <div className="flex items-start gap-3">
              <span className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium flex-shrink-0">3</span>
              <p className="text-muted-foreground">{t('home.gettingStarted.step3')}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App