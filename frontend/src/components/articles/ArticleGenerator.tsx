import React, { useState, useEffect, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { articlesApi } from '@/lib/api'
import { ArticleRequest } from '@/types/articles'

interface ArticleGeneratorProps {
  collectionId: number
  onArticleGenerated?: (articleId: number) => void
}

export function ArticleGenerator({ collectionId, onArticleGenerated }: ArticleGeneratorProps) {
  const [isGenerating, setIsGenerating] = useState(false)

  const [progress, setProgress] = useState<string>('')
  const [generationStatus, setGenerationStatus] = useState<'idle' | 'generating' | 'completed' | 'failed'>('idle')
  const [formData, setFormData] = useState<ArticleRequest>({
    topic: '',
    subtopics: [],
    article_type: 'comprehensive',
    target_length: 'medium',
    writing_style: 'professional'
  })
  const [subtopicInput, setSubtopicInput] = useState('')
  const pollingInterval = useRef<number | null>(null)

  // Polling function to check article status
  const pollArticleStatus = async (articleId: number) => {
    try {
      const article = await articlesApi.get(collectionId, articleId)
      setProgress(article.progress || '')
      setGenerationStatus(article.status)
      
      if (article.status === 'completed') {
        setIsGenerating(false)
        if (pollingInterval.current) {
          clearInterval(pollingInterval.current)
          pollingInterval.current = null
        }
        if (onArticleGenerated) {
          onArticleGenerated(articleId)
        }
      } else if (article.status === 'failed') {
        setIsGenerating(false)
        if (pollingInterval.current) {
          clearInterval(pollingInterval.current)
          pollingInterval.current = null
        }
      }
    } catch (error) {
      console.error('Failed to poll article status:', error)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.topic.trim()) return

    setIsGenerating(true)
    setGenerationStatus('generating')
    setProgress('Starting article generation...')
    
    try {
      const response = await articlesApi.generate(collectionId, {
        ...formData,
        subtopics: formData.subtopics?.length ? formData.subtopics : undefined
      })
      

      
      // Start polling for progress updates
      pollingInterval.current = setInterval(() => {
        pollArticleStatus(response.id)
      }, 2000) // Poll every 2 seconds
      
    } catch (error) {
      console.error('Failed to generate article:', error)
      setIsGenerating(false)
      setGenerationStatus('failed')
      setProgress('Failed to start article generation')
    }
  }

  // Reset generation state
  const resetGenerationState = () => {
    setIsGenerating(false)
    setProgress('')
    setGenerationStatus('idle')
    if (pollingInterval.current) {
      clearInterval(pollingInterval.current)
      pollingInterval.current = null
    }
  }

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval.current) {
        clearInterval(pollingInterval.current)
      }
    }
  }, [])

  const addSubtopic = () => {
    if (subtopicInput.trim() && !formData.subtopics?.includes(subtopicInput.trim())) {
      setFormData(prev => ({
        ...prev,
        subtopics: [...(prev.subtopics || []), subtopicInput.trim()]
      }))
      setSubtopicInput('')
    }
  }

  const removeSubtopic = (subtopic: string) => {
    setFormData(prev => ({
      ...prev,
      subtopics: prev.subtopics?.filter(s => s !== subtopic) || []
    }))
  }

  return (
    <Card className="w-full max-w-2xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          🤖 AI Article Generator
          <Badge variant="secondary">Enhanced Citations</Badge>
        </CardTitle>
        <CardDescription>
          Generate professional articles with automatic citations and references from verified web sources
        </CardDescription>
        <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-start gap-3">
            <span className="text-blue-600 text-xl">📚</span>
            <div>
              <h4 className="font-semibold text-blue-800 text-sm">Enhanced Citation System</h4>
              <p className="text-blue-700 text-sm mt-1">
                Articles now include real citations from Wikipedia, DuckDuckGo, and other trusted sources. 
                All facts will be backed by verifiable references with clickable links.
              </p>
              <div className="flex items-center gap-4 mt-2 text-xs text-blue-600">
                <span>✅ Web source verification</span>
                <span>✅ Automatic fact-checking</span>
                <span>✅ Clickable references</span>
              </div>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Topic Input */}
          <div className="space-y-2">
            <Label htmlFor="topic">Article Topic *</Label>
            <Input
              id="topic"
              placeholder="e.g., Artificial Intelligence in Healthcare"
              value={formData.topic}
              onChange={(e) => setFormData(prev => ({ ...prev, topic: e.target.value }))}
              required
            />
          </div>

          {/* Subtopics */}
          <div className="space-y-2">
            <Label htmlFor="subtopics">Subtopics (Optional)</Label>
            <div className="flex gap-2">
              <Input
                id="subtopics"
                placeholder="Add specific subtopic"
                value={subtopicInput}
                onChange={(e) => setSubtopicInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && (e.preventDefault(), addSubtopic())}
              />
              <Button type="button" variant="outline" onClick={addSubtopic}>
                Add
              </Button>
            </div>
            {formData.subtopics && formData.subtopics.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {formData.subtopics.map((subtopic) => (
                  <Badge key={subtopic} variant="secondary" className="cursor-pointer" 
                         onClick={() => removeSubtopic(subtopic)}>
                    {subtopic} ×
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* Article Settings */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="article_type">Article Type</Label>
              <select
                id="article_type"
                className="w-full px-3 py-2 border border-input bg-background rounded-md"
                value={formData.article_type}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  article_type: e.target.value as ArticleRequest['article_type'] 
                }))}
              >
                <option value="comprehensive">Comprehensive</option>
                <option value="summary">Summary</option>
                <option value="technical">Technical</option>
                <option value="overview">Overview</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="target_length">Target Length</Label>
              <select
                id="target_length"
                className="w-full px-3 py-2 border border-input bg-background rounded-md"
                value={formData.target_length}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  target_length: e.target.value as ArticleRequest['target_length'] 
                }))}
              >
                <option value="short">Short (~500 words)</option>
                <option value="medium">Medium (~1000 words)</option>
                <option value="long">Long (~2000 words)</option>
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="writing_style">Writing Style</Label>
              <select
                id="writing_style"
                className="w-full px-3 py-2 border border-input bg-background rounded-md"
                value={formData.writing_style}
                onChange={(e) => setFormData(prev => ({ 
                  ...prev, 
                  writing_style: e.target.value as ArticleRequest['writing_style'] 
                }))}
              >
                <option value="professional">Professional</option>
                <option value="academic">Academic</option>
                <option value="casual">Casual</option>
                <option value="technical">Technical</option>
              </select>
            </div>
          </div>

          {/* Generate Button */}
          <Button 
            type="submit" 
            className="w-full" 
            disabled={isGenerating || !formData.topic.trim()}
          >
            {isGenerating ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                Generating Article with Citations...
              </>
            ) : (
              <>
                🚀 Generate Article with Enhanced Citations
              </>
            )}
          </Button>
        </form>

        {isGenerating && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <div className="flex items-center gap-2 text-blue-700">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-700" />
              <span className="font-medium">AI Article Generation in Progress</span>
              <Badge variant="outline" className="ml-2">{generationStatus}</Badge>
            </div>
            <div className="mt-2 text-sm text-blue-600">
              {progress ? (
                <p className="font-medium">📊 {progress}</p>
              ) : (
                <p>🔄 Initializing article generation...</p>
              )}
              <div className="mt-2 space-y-1 text-xs opacity-75">
                <p>🔍 Multi-language web search enabled</p>
                <p>📚 Automatic citation collection</p>
                <p>⏱️ Protected by 5-minute timeout</p>
              </div>
            </div>
          </div>
        )}

        {generationStatus === 'completed' && !isGenerating && (
          <div className="mt-4 p-4 bg-green-50 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-green-700">
                <span className="text-lg">✅</span>
                <span className="font-medium">Article Generation Completed!</span>
              </div>
              <Button onClick={resetGenerationState} variant="outline" size="sm">
                Generate Another
              </Button>
            </div>
            <p className="mt-1 text-sm text-green-600">
              Your article has been generated successfully with citations.
            </p>
          </div>
        )}

        {generationStatus === 'failed' && !isGenerating && (
          <div className="mt-4 p-4 bg-red-50 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-red-700">
                <span className="text-lg">❌</span>
                <span className="font-medium">Generation Failed</span>
              </div>
              <Button onClick={resetGenerationState} variant="outline" size="sm">
                Try Again
              </Button>
            </div>
            <p className="mt-1 text-sm text-red-600">
              {progress || 'An error occurred during article generation. Please try again.'}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}