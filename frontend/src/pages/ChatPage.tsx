import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ArrowLeft, MessageSquare, Settings, BarChart3 } from 'lucide-react'
import { StreamingChat } from '@/components/chat/StreamingChat'

interface Collection {
  id: number
  name: string
  description?: string
  document_count: number
  created_at: string
}

export function ChatPage() {
  const { collectionId } = useParams<{ collectionId: string }>()
  const [collection, setCollection] = useState<Collection | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchCollection = async () => {
      if (!collectionId) return

      try {
        const response = await fetch(`/api/kb/collections/${collectionId}`)
        if (!response.ok) {
          throw new Error('Failed to fetch collection')
        }
        const data = await response.json()
        setCollection(data)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error')
      } finally {
        setLoading(false)
      }
    }

    fetchCollection()
  }, [collectionId])

  const handleArticleGenerated = (article: any) => {
    console.log('Article generated:', article)
    // Could navigate to article view or show success message
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p>Loading collection...</p>
        </div>
      </div>
    )
  }

  if (error || !collection) {
    return (
      <div className="container mx-auto p-6">
        <Card>
          <CardContent className="p-6">
            <div className="text-center">
              <h3 className="text-lg font-semibold mb-2">Collection Not Found</h3>
              <p className="text-muted-foreground mb-4">
                {error || 'The requested collection could not be found.'}
              </p>
              <Button onClick={() => window.history.back()}>
                <ArrowLeft className="w-4 h-4 mr-2" />
                Go Back
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-background">
      {/* Header */}
      <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => window.history.back()}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              <div className="flex items-center gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <MessageSquare className="w-5 h-5 text-primary" />
                </div>
                <div>
                  <h1 className="text-xl font-semibold">AI Article Writer</h1>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>{collection.name}</span>
                    <Badge variant="secondary">
                      {collection.document_count} documents
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm">
                <BarChart3 className="w-4 h-4 mr-2" />
                Analytics
              </Button>
              <Button variant="ghost" size="sm">
                <Settings className="w-4 h-4 mr-2" />
                Settings
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Interface */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full">
          <StreamingChat
            collectionId={parseInt(collectionId!)}
            collectionName={collection.name}
          />
        </div>
      </div>
    </div>
  )
}