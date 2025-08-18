import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { StreamingChat } from '@/components/chat/StreamingChat'
import { EnhancedAgentChat } from '@/components/chat/EnhancedAgentChat'
import { StepByStepAgentChat } from '@/components/chat/StepByStepAgentChat'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { ArrowLeft, BookOpen, FileText, Bot, MessageSquare } from 'lucide-react'
import { collectionsApi } from '@/lib/api'
import { Collection } from '@/types/collections'

export function WritingPage() {
  const { collectionId } = useParams<{ collectionId: string }>()
  const [collection, setCollection] = useState<Collection | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (collectionId) {
      loadCollection()
    }
  }, [collectionId])

  const loadCollection = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const collectionData = await collectionsApi.get(parseInt(collectionId!))
      setCollection(collectionData)
    } catch (err) {
      console.error('Failed to load collection:', err)
      setError('Failed to load collection. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <div className="text-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
            <p className="text-muted-foreground">Loading collection...</p>
          </div>
        </div>
      </div>
    )
  }

  if (error || !collection) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex items-center justify-center min-h-[400px]">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-center text-destructive">Error</CardTitle>
            </CardHeader>
            <CardContent className="text-center space-y-4">
              <p className="text-muted-foreground">
                {error || 'Collection not found'}
              </p>
              <div className="flex gap-2 justify-center">
                <Button asChild variant="outline">
                  <Link to="/collections">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Collections
                  </Link>
                </Button>
                <Button onClick={loadCollection}>
                  Try Again
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button asChild variant="ghost" size="sm">
                <Link to={`/collections/${collectionId}`}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Collection
                </Link>
              </Button>
              
              <div className="flex items-center space-x-2">
                <BookOpen className="w-5 h-5 text-primary" />
                <div>
                  <h1 className="text-lg font-semibold">AI Article Writer</h1>
                  <p className="text-sm text-muted-foreground">
                    Collection: {collection.name}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-1 text-sm text-muted-foreground">
                <FileText className="w-4 h-4" />
                <span>{collection.total_documents || 0} documents</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full max-w-7xl mx-auto p-4">
          <Tabs defaultValue="step-by-step" className="h-full flex flex-col">
            <TabsList className="grid w-full grid-cols-3 mb-4">
              <TabsTrigger value="step-by-step" className="flex items-center gap-2">
                <Bot className="w-4 h-4" />
                Step-by-Step Agents
              </TabsTrigger>
              <TabsTrigger value="enhanced" className="flex items-center gap-2">
                <Bot className="w-4 h-4" />
                Enhanced AI Agents
              </TabsTrigger>
              <TabsTrigger value="simple" className="flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Simple Chat
              </TabsTrigger>
            </TabsList>
            
            <TabsContent value="step-by-step" className="flex-1 mt-0">
              <StepByStepAgentChat collectionId={parseInt(collectionId!)} />
            </TabsContent>
            
            <TabsContent value="enhanced" className="flex-1 mt-0">
              <EnhancedAgentChat collectionId={parseInt(collectionId!)} />
            </TabsContent>
            
            <TabsContent value="simple" className="flex-1 mt-0">
              <StreamingChat 
                collectionId={parseInt(collectionId!)} 
                collectionName={collection.name}
              />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}