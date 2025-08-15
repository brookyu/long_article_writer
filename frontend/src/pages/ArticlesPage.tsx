import React, { useState } from 'react'
import { ArticleGenerator } from '@/components/articles/ArticleGenerator'
import { ArticleList } from '@/components/articles/ArticleList'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface ArticlesPageProps {
  collectionId: number
  collectionName?: string
}

export function ArticlesPage({ collectionId, collectionName }: ArticlesPageProps) {
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleArticleGenerated = (articleId: number) => {
    console.log('Article generated:', articleId)
    // Trigger refresh of article list
    setRefreshTrigger(prev => prev + 1)
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">
          🤖 AI Article Generator
        </h1>
        <p className="text-gray-600">
          Generate professional articles with enhanced citations for collection: {' '}
          <span className="font-medium">{collectionName || `Collection ${collectionId}`}</span>
        </p>
        <div className="flex gap-2 mt-3">
          <Badge variant="secondary">⚡ 2-minute generation</Badge>
          <Badge variant="secondary">📚 Automatic citations</Badge>
          <Badge variant="secondary">🌐 Multi-language search</Badge>
          <Badge variant="secondary">🔗 Reference links</Badge>
        </div>
      </div>

      <div className="grid gap-8 lg:grid-cols-2">
        {/* Article Generator */}
        <div>
          <ArticleGenerator 
            collectionId={collectionId}
            onArticleGenerated={handleArticleGenerated}
          />
        </div>

        {/* Generated Articles List */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                📄 Generated Articles
                <Badge variant="outline">Collection {collectionId}</Badge>
              </CardTitle>
              <CardDescription>
                View and manage your AI-generated articles with citations
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ArticleList 
                collectionId={collectionId}
                refreshTrigger={refreshTrigger}
              />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Features Info */}
      <div className="mt-12">
        <Card>
          <CardHeader>
            <CardTitle>🚀 Enhanced Article Generation Features</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="text-center">
                <div className="text-2xl mb-2">⚡</div>
                <h3 className="font-semibold mb-1">Fast Generation</h3>
                <p className="text-sm text-gray-600">
                  Professional articles in under 2 minutes
                </p>
              </div>
              <div className="text-center">
                <div className="text-2xl mb-2">📚</div>
                <h3 className="font-semibold mb-1">Auto Citations</h3>
                <p className="text-sm text-gray-600">
                  Automatic reference collection and formatting
                </p>
              </div>
              <div className="text-center">
                <div className="text-2xl mb-2">🌐</div>
                <h3 className="font-semibold mb-1">Global Search</h3>
                <p className="text-sm text-gray-600">
                  Multi-language web search integration
                </p>
              </div>
              <div className="text-center">
                <div className="text-2xl mb-2">🎯</div>
                <h3 className="font-semibold mb-1">Professional Quality</h3>
                <p className="text-sm text-gray-600">
                  Academic-style articles with bibliography
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}