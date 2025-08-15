import { BrowserRouter as Router, Routes, Route, Link, useParams } from 'react-router-dom'
import { CollectionsPage } from '@/pages/CollectionsPage'
import { CollectionDetailPage } from '@/pages/CollectionDetailPage'
import { ArticlesPage } from '@/pages/ArticlesPage'
import { WritingPage } from '@/pages/WritingPage'
import { SettingsPage } from '@/pages/SettingsPage'
import './App.css'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-background">
        {/* Navigation */}
        <nav className="border-b bg-card">
          <div className="container mx-auto px-4 py-3">
            <div className="flex items-center justify-between">
              <Link to="/" className="text-xl font-bold">
                Long Article Writer
              </Link>
              <div className="flex items-center space-x-4">
                <Link 
                  to="/collections" 
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Collections
                </Link>
                <Link 
                  to="/articles/1" 
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  🤖 AI Articles
                </Link>
                <Link 
                  to="/settings" 
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Settings
                </Link>
                <Link 
                  to="/" 
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Home
                </Link>
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
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  )
}

function ArticlesPageWrapper() {
  const { collectionId } = useParams<{ collectionId: string }>()
  return <ArticlesPage collectionId={parseInt(collectionId || '1')} />
}

function HomePage() {
  return (
    <div className="container mx-auto py-8">
      <div className="text-center max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-foreground mb-4">
          🤖 Long Article Writer
        </h1>
        <p className="text-lg text-muted-foreground mb-8">
          AI-powered article generation with enhanced citations and multi-language web search
        </p>
        <div className="flex flex-wrap justify-center gap-2 mb-8">
          <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">
            ⚡ 2-minute generation
          </span>
          <span className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm font-medium">
            📚 Automatic citations
          </span>
          <span className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm font-medium">
            🌐 Multi-language search
          </span>
          <span className="px-3 py-1 bg-orange-100 text-orange-800 rounded-full text-sm font-medium">
            🔗 Reference links
          </span>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-card p-6 rounded-lg border">
            <h2 className="text-xl font-semibold mb-4">Knowledge Base</h2>
            <p className="text-muted-foreground mb-4">
              Organize your documents into collections for AI-powered research and writing.
            </p>
            <Link 
              to="/collections" 
              className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors h-9 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              Manage Collections
            </Link>
          </div>
          
          <div className="bg-card p-6 rounded-lg border">
            <h2 className="text-xl font-semibold mb-4">🤖 AI Article Generation</h2>
            <p className="text-muted-foreground mb-4">
              Generate professional articles with enhanced citations in under 2 minutes.
            </p>
            <Link 
              to="/articles/1"
              className="inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors h-9 px-4 py-2 bg-primary text-primary-foreground hover:bg-primary/90"
            >
              🚀 Generate Articles
            </Link>
          </div>
        </div>

        <div className="bg-card p-6 rounded-lg border">
          <h2 className="text-xl font-semibold mb-4">Getting Started</h2>
          <div className="text-left space-y-3">
            <div className="flex items-start gap-3">
              <span className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium flex-shrink-0">1</span>
              <p className="text-muted-foreground">Create your first collection to organize documents by topic or project</p>
            </div>
            <div className="flex items-start gap-3">
              <span className="bg-muted text-muted-foreground rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium flex-shrink-0">2</span>
              <p className="text-muted-foreground">Upload documents (PDFs, text files) to build your knowledge base</p>
            </div>
            <div className="flex items-start gap-3">
              <span className="bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center text-sm font-medium flex-shrink-0">3</span>
              <p className="text-muted-foreground">Generate AI-powered articles with enhanced citations in under 2 minutes</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App