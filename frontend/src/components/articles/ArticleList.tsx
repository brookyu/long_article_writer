import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { articlesApi } from '@/lib/api'
import { Article } from '@/types/articles'

interface ArticleListProps {
  collectionId: number
  refreshTrigger?: number
}

export function ArticleList({ collectionId, refreshTrigger }: ArticleListProps) {
  const [articles, setArticles] = useState<Article[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedArticle, setSelectedArticle] = useState<Article | null>(null)
  const [loadingArticle, setLoadingArticle] = useState(false)

  useEffect(() => {
    loadArticles()
  }, [collectionId, refreshTrigger])

  const loadArticles = async () => {
    try {
      setLoading(true)
      const response = await articlesApi.list(collectionId)
      // Handle both array response and object with articles property
      const articlesArray = Array.isArray(response) ? response : (response.articles || [])
      console.log('Loaded articles:', articlesArray)
      setArticles(articlesArray)
    } catch (error) {
      console.error('Failed to load articles:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleViewArticle = async (article: Article) => {
    try {
      setLoadingArticle(true)
      // Fetch the full article with content
      const fullArticle = await articlesApi.get(collectionId, article.id)
      console.log('Loaded full article:', fullArticle)
      setSelectedArticle(fullArticle)
    } catch (error) {
      console.error('Failed to load article details:', error)
      // Fall back to showing what we have
      setSelectedArticle(article)
    } finally {
      setLoadingArticle(false)
    }
  }

  const getStatusBadge = (status: Article['status']) => {
    switch (status) {
      case 'completed':
        return <Badge variant="default" className="bg-green-500">✅ Completed</Badge>
      case 'generating':
        return <Badge variant="secondary" className="bg-blue-500 text-white">⏳ Generating</Badge>
      case 'failed':
        return <Badge variant="destructive">❌ Failed</Badge>
      default:
        return <Badge variant="outline">⏸️ Pending</Badge>
    }
  }

  const formatGenerationTime = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`
  }

  const deleteArticle = async (articleId: number) => {
    if (!confirm('Are you sure you want to delete this article?')) return
    
    try {
      await articlesApi.delete(collectionId, articleId)
      await loadArticles()
    } catch (error) {
      console.error('Failed to delete article:', error)
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mr-2" />
            Loading articles...
          </div>
        </CardContent>
      </Card>
    )
  }

  if (articles.length === 0) {
    return (
      <Card>
        <CardContent className="p-6 text-center">
          <div className="text-gray-500">
            <h3 className="text-lg font-medium mb-2">No Articles Yet</h3>
            <p>Generate your first AI article with enhanced citations!</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4">
        {articles.map((article) => (
          <Card key={article.id} className="cursor-pointer hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <CardTitle className="text-lg">
                    {article.title || article.topic}
                  </CardTitle>
                  <CardDescription className="mt-1">
                    Topic: {article.topic}
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge(article.status)}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-between text-sm text-gray-600 mb-4">
                <div className="flex items-center gap-4">
                  {article.word_count && (
                    <span>📄 {article.word_count} words</span>
                  )}
                  {article.references && article.references.length > 0 ? (
                    <span className="bg-green-100 text-green-800 px-2 py-1 rounded-md">
                      📚 {article.references.length} citations
                    </span>
                  ) : article.status === 'completed' ? (
                    <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded-md">
                      ⚠️ No citations
                    </span>
                  ) : null}
                  <span>⏱️ {formatGenerationTime(article.generation_time_seconds)}</span>
                </div>
                <div className="text-xs text-gray-500">
                  {new Date(article.created_at).toLocaleDateString()}
                </div>
              </div>

              <div className="flex items-center justify-between">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => handleViewArticle(article)}
                  disabled={article.status !== 'completed' || loadingArticle}
                >
                  {loadingArticle ? '⏳ Loading...' : 
                   article.status === 'completed' ? '👁️ View Article' : '⏳ Generating...'}
                </Button>
                <Button 
                  variant="destructive" 
                  size="sm"
                  onClick={() => deleteArticle(article.id)}
                >
                  🗑️ Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Article Viewer Modal */}
      {selectedArticle && (
        <ArticleViewer 
          article={selectedArticle} 
          onClose={() => setSelectedArticle(null)} 
        />
      )}
    </div>
  )
}

// Article Viewer Component
function ArticleViewer({ article, onClose }: { article: Article; onClose: () => void }) {
  // Calculate word count from content if not provided
  const wordCount = article.word_count || (article.content ? article.content.split(/\s+/).length : 0)
  
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <div className="p-6 border-b">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold">{article.title}</h2>
              <p className="text-gray-600 mt-1">Topic: {article.topic}</p>
            </div>
            <Button variant="outline" onClick={onClose}>
              ✕ Close
            </Button>
          </div>
          
          <div className="flex items-center gap-4 mt-4 text-sm text-gray-600">
            <span>📄 {wordCount} words</span>
            {article.references && article.references.length > 0 ? (
              <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full font-medium">
                📚 {article.references.length} verified citations
              </span>
            ) : (
              <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full">
                ⚠️ No supporting sources
              </span>
            )}
            <span>⏱️ Generated in {formatGenerationTime(article.generation_time_seconds)}</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          {article.content ? (
            <div className="prose max-w-none">
              <div 
                className="whitespace-pre-wrap"
                dangerouslySetInnerHTML={{ 
                  __html: article.content
                    .replace(/^# (.+)$/gm, '<h1 class="text-3xl font-bold mb-4 text-gray-800">$1</h1>')
                    .replace(/^## (.+)$/gm, '<h2 class="text-2xl font-semibold mb-3 mt-6 text-gray-800 border-b-2 border-gray-200 pb-2">$1</h2>')
                    .replace(/^### (.+)$/gm, '<h3 class="text-xl font-medium mb-2 mt-4 text-gray-700">$1</h3>')
                    .replace(/\[(\d+)\]/g, '<sup class="bg-blue-100 text-blue-800 px-1 py-0.5 rounded text-xs font-bold mx-0.5 hover:bg-blue-200 cursor-pointer transition-colors">[$1]</sup>')
                    .replace(/\n\n/g, '</p><p class="mb-4 text-gray-700 leading-relaxed">')
                    .replace(/^(.+)$/gm, '<p class="mb-4 text-gray-700 leading-relaxed">$1</p>')
                }}
              />
            </div>
          ) : (
            <div className="text-center text-gray-500">
              Article content not available
            </div>
          )}
        </div>

        {/* References Section */}
        {article.references && article.references.length > 0 && (
          <div className="border-t p-6 bg-gradient-to-r from-blue-50 to-green-50">
            <h3 className="text-lg font-semibold mb-4 text-gray-800">
              📚 Verified Sources & Citations ({article.references.length})
            </h3>
            <div className="grid gap-3">
              {article.references.map((ref) => (
                <div key={ref.number} className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
                  <div className="flex items-start gap-3">
                    <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs font-bold min-w-[2rem] text-center">
                      [{ref.number}]
                    </span>
                    <div className="flex-1">
                      <a 
                        href={ref.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="text-blue-700 hover:text-blue-900 font-medium hover:underline text-sm block mb-1"
                      >
                        {ref.title}
                      </a>
                      <div className="flex items-center gap-2 text-xs text-gray-500">
                        <span className="bg-gray-100 px-2 py-1 rounded">
                          {ref.engine.charAt(0).toUpperCase() + ref.engine.slice(1)}
                        </span>
                        <span>•</span>
                        <span>Retrieved {ref.accessed}</span>
                        <span>•</span>
                        <a 
                          href={ref.url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-blue-600 hover:underline"
                        >
                          View Source ↗
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>✅ Quality Assurance:</strong> All citations are from verified web sources and have been automatically collected during article generation to ensure factual accuracy and credibility.
              </p>
            </div>
          </div>
        )}

        {/* No References Warning */}
        {(!article.references || article.references.length === 0) && article.status === 'completed' && (
          <div className="border-t p-6 bg-red-50">
            <div className="flex items-center gap-3 p-4 bg-red-100 border border-red-300 rounded-lg">
              <span className="text-red-600 text-2xl">⚠️</span>
              <div>
                <h4 className="font-semibold text-red-800">No Supporting Sources Found</h4>
                <p className="text-red-700 text-sm mt-1">
                  This article was generated without external citations. Content may not be fully verified. 
                  Consider regenerating with a different topic or checking system settings.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

const formatGenerationTime = (seconds?: number) => {
  if (!seconds) return 'N/A'
  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = Math.floor(seconds % 60)
  return minutes > 0 ? `${minutes}m ${remainingSeconds}s` : `${remainingSeconds}s`
}