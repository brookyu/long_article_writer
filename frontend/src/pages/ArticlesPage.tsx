import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArticleGenerationChat } from '@/components/chat/ArticleGenerationChat'
import { ArticleList } from '@/components/articles/ArticleList'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface ArticlesPageProps {
  collectionId: number
  collectionName?: string
}

export function ArticlesPage({ collectionId, collectionName }: ArticlesPageProps) {
  const { t } = useTranslation()
  const [refreshTrigger, setRefreshTrigger] = useState(0)

  const handleArticleGenerated = (articleId: number) => {
    console.log('Article generated:', articleId)
    // Trigger refresh of article list
    setRefreshTrigger(prev => prev + 1)
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold mb-1">
                {t('chat.title')}
              </h1>
              <p className="text-muted-foreground">
                {t('chat.subtitle', { collectionId: collectionName || `Collection ${collectionId}` })}
              </p>
            </div>
            <div className="flex gap-2">
              <Badge variant="secondary">⚡ {t('chat.features.realtime')}</Badge>
              <Badge variant="secondary">💬 {t('chat.features.interactive')}</Badge>
              <Badge variant="secondary">📚 {t('chat.features.citations')}</Badge>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content - Split Layout */}
      <div className="flex-1 min-h-0">
        <div className="h-full grid lg:grid-cols-3 gap-0">
          {/* Chat Interface - Takes up 2/3 of space */}
          <div className="lg:col-span-2 border-r overflow-auto">
            <ArticleGenerationChat 
              collectionId={collectionId}
            />
          </div>

          {/* Generated Articles Sidebar - Takes up 1/3 of space */}
          <div className="lg:col-span-1 bg-muted/30">
            <div className="h-full overflow-auto">
              <div className="p-4">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="flex items-center gap-2 text-lg">
                      📄 {t('articles.generatedTitle')}
                      <Badge variant="outline" className="text-xs">{t('articles.collectionLabel', { collectionId })}</Badge>
                    </CardTitle>
                    <CardDescription className="text-sm">
                      {t('articles.subtitle')}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <ArticleList 
                      collectionId={collectionId}
                      refreshTrigger={refreshTrigger}
                    />
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div>
  )
}