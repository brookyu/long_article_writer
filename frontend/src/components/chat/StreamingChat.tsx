import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, Send, Download, RefreshCw } from 'lucide-react'

interface StreamingChatProps {
  collectionId: number
  collectionName?: string
}

interface Message {
  id: string
  type: 'user' | 'system' | 'content' | 'status' | 'error'
  content: string
  timestamp: Date
  step?: number
  totalSteps?: number
}

interface StreamingChatState {
  messages: Message[]
  isStreaming: boolean
  currentStep: number
  totalSteps: number
  generatedContent: string
  articleTitle: string
}

export function StreamingChat({ collectionId, collectionName }: StreamingChatProps) {
  const [state, setState] = useState<StreamingChatState>({
    messages: [],
    isStreaming: false,
    currentStep: 0,
    totalSteps: 0,
    generatedContent: '',
    articleTitle: ''
  })
  
  const [topic, setTopic] = useState('')
  const [subtopics, setSubtopics] = useState<string[]>([])
  const [subtopicInput, setSubtopicInput] = useState('')
  const [articleType, setArticleType] = useState<'comprehensive' | 'tutorial' | 'analysis' | 'overview' | 'technical'>('comprehensive')
  const [targetLength, setTargetLength] = useState<'short' | 'medium' | 'long'>('medium')
  const [writingStyle, setWritingStyle] = useState<'professional' | 'conversational' | 'academic' | 'technical' | 'casual'>('professional')
  
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [state.messages])

  const addMessage = (message: Omit<Message, 'id' | 'timestamp'>) => {
    setState(prev => ({
      ...prev,
      messages: [...prev.messages, {
        ...message,
        id: Date.now().toString(),
        timestamp: new Date()
      }]
    }))
  }

  const addSubtopic = () => {
    if (subtopicInput.trim() && !subtopics.includes(subtopicInput.trim())) {
      setSubtopics([...subtopics, subtopicInput.trim()])
      setSubtopicInput('')
    }
  }

  const removeSubtopic = (index: number) => {
    setSubtopics(subtopics.filter((_, i) => i !== index))
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      if (subtopicInput.trim()) {
        addSubtopic()
      } else if (topic.trim() && !state.isStreaming) {
        generateOutline()
      }
    }
  }

  const generateOutline = async () => {
    if (!topic.trim()) return

    // Add user message
    addMessage({
      type: 'user',
      content: `Generate outline for: "${topic}"${subtopics.length > 0 ? ` (Subtopics: ${subtopics.join(', ')})` : ''}`
    })

    setState(prev => ({
      ...prev,
      isStreaming: true,
      currentStep: 0,
      totalSteps: 0
    }))

    try {
      const response = await fetch('/api/articles/outline', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          collection_id: collectionId,
          topic,
          subtopics: subtopics.length > 0 ? subtopics : null,
          article_type: articleType,
          target_length: targetLength
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                handleStreamMessage(data)
              } catch (e) {
                console.error('Failed to parse stream data:', e)
              }
            }
          }
        }
      }
    } catch (error) {
      addMessage({
        type: 'error',
        content: `Failed to generate outline: ${error instanceof Error ? error.message : 'Unknown error'}`
      })
    } finally {
      setState(prev => ({ ...prev, isStreaming: false }))
    }
  }

  const generateDraft = async () => {
    if (!topic.trim()) return

    // Add user message
    addMessage({
      type: 'user',
      content: `Generate full article draft for: "${topic}"`
    })

    setState(prev => ({
      ...prev,
      isStreaming: true,
      currentStep: 0,
      totalSteps: 0,
      generatedContent: '',
      articleTitle: ''
    }))

    try {
      const response = await fetch('/api/articles/draft', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          collection_id: collectionId,
          topic,
          subtopics: subtopics.length > 0 ? subtopics : null,
          article_type: articleType,
          target_length: targetLength,
          writing_style: writingStyle
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (reader) {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                handleStreamMessage(data)
              } catch (e) {
                console.error('Failed to parse stream data:', e)
              }
            }
          }
        }
      }
    } catch (error) {
      addMessage({
        type: 'error',
        content: `Failed to generate article: ${error instanceof Error ? error.message : 'Unknown error'}`
      })
    } finally {
      setState(prev => ({ ...prev, isStreaming: false }))
    }
  }

  const handleStreamMessage = (data: any) => {
    switch (data.type) {
      case 'status':
        setState(prev => ({
          ...prev,
          currentStep: data.step || prev.currentStep,
          totalSteps: data.total_steps || prev.totalSteps
        }))
        addMessage({
          type: 'status',
          content: data.message,
          step: data.step,
          totalSteps: data.total_steps
        })
        break

      case 'research':
        addMessage({
          type: 'system',
          content: `Research complete: Found ${data.data.total_chunks_found} relevant chunks from ${data.data.unique_documents.length} documents`
        })
        break

      case 'outline':
        addMessage({
          type: 'content',
          content: `**Generated Outline:**\n\n${data.data.outline_text}`
        })
        break

      case 'title':
        setState(prev => ({ ...prev, articleTitle: data.data }))
        break

      case 'content':
        setState(prev => ({
          ...prev,
          generatedContent: prev.generatedContent + data.data
        }))
        break

      case 'complete':
        addMessage({
          type: 'system',
          content: data.message
        })
        if (state.generatedContent) {
          addMessage({
            type: 'content',
            content: state.generatedContent
          })
        }
        break

      case 'error':
        addMessage({
          type: 'error',
          content: data.message
        })
        break
    }
  }

  const exportArticle = async () => {
    if (!state.generatedContent || !state.articleTitle) return

    try {
      const response = await fetch('/api/articles/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: state.articleTitle,
          content: state.generatedContent,
          topic,
          collection_id: collectionId
        })
      })

      const result = await response.json()
      
      if (result.status === 'success') {
        // Create download link
        const blob = new Blob([result.markdown], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = result.filename
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)

        addMessage({
          type: 'system',
          content: `Article exported as ${result.filename}`
        })
      }
    } catch (error) {
      addMessage({
        type: 'error',
        content: `Export failed: ${error instanceof Error ? error.message : 'Unknown error'}`
      })
    }
  }

  const clearChat = () => {
    setState({
      messages: [],
      isStreaming: false,
      currentStep: 0,
      totalSteps: 0,
      generatedContent: '',
      articleTitle: ''
    })
    setTopic('')
    setSubtopics([])
  }

  return (
    <div className="flex flex-col h-full max-h-screen">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-semibold">AI Article Writer</h2>
            <p className="text-sm text-muted-foreground">
              Collection: {collectionName || `ID ${collectionId}`}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={clearChat}
            disabled={state.isStreaming}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Clear
          </Button>
        </div>
      </div>

      {/* Configuration Panel */}
      <div className="border-b p-4 bg-muted/30">
        <div className="space-y-4">
          {/* Topic Input */}
          <div>
            <label className="text-sm font-medium">Article Topic</label>
            <Input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="Enter the main topic for your article..."
              disabled={state.isStreaming}
              onKeyPress={handleKeyPress}
              className="mt-1"
            />
          </div>

          {/* Subtopics */}
          <div>
            <label className="text-sm font-medium">Subtopics (Optional)</label>
            <div className="flex gap-2 mt-1">
              <Input
                value={subtopicInput}
                onChange={(e) => setSubtopicInput(e.target.value)}
                placeholder="Add subtopic..."
                disabled={state.isStreaming}
                onKeyPress={handleKeyPress}
              />
              <Button
                type="button"
                variant="outline"
                onClick={addSubtopic}
                disabled={state.isStreaming || !subtopicInput.trim()}
              >
                Add
              </Button>
            </div>
            {subtopics.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {subtopics.map((subtopic, index) => (
                  <Badge
                    key={index}
                    variant="secondary"
                    className="cursor-pointer"
                    onClick={() => removeSubtopic(index)}
                  >
                    {subtopic} ×
                  </Badge>
                ))}
              </div>
            )}
          </div>

          {/* Options */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium">Article Type</label>
              <select
                value={articleType}
                onChange={(e) => setArticleType(e.target.value as any)}
                disabled={state.isStreaming}
                className="w-full mt-1 px-3 py-2 border rounded-md"
              >
                <option value="comprehensive">Comprehensive</option>
                <option value="tutorial">Tutorial</option>
                <option value="analysis">Analysis</option>
                <option value="overview">Overview</option>
                <option value="technical">Technical</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">Length</label>
              <select
                value={targetLength}
                onChange={(e) => setTargetLength(e.target.value as any)}
                disabled={state.isStreaming}
                className="w-full mt-1 px-3 py-2 border rounded-md"
              >
                <option value="short">Short (500-1000 words)</option>
                <option value="medium">Medium (1000-2500 words)</option>
                <option value="long">Long (2500+ words)</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">Writing Style</label>
              <select
                value={writingStyle}
                onChange={(e) => setWritingStyle(e.target.value as any)}
                disabled={state.isStreaming}
                className="w-full mt-1 px-3 py-2 border rounded-md"
              >
                <option value="professional">Professional</option>
                <option value="conversational">Conversational</option>
                <option value="academic">Academic</option>
                <option value="technical">Technical</option>
                <option value="casual">Casual</option>
              </select>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <Button
              onClick={generateOutline}
              disabled={state.isStreaming || !topic.trim()}
              className="flex-1"
            >
              {state.isStreaming ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Generate Outline
                </>
              )}
            </Button>
            <Button
              onClick={generateDraft}
              disabled={state.isStreaming || !topic.trim()}
              variant="outline"
              className="flex-1"
            >
              {state.isStreaming ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4 mr-2" />
                  Generate Full Article
                </>
              )}
            </Button>
            {state.generatedContent && (
              <Button
                onClick={exportArticle}
                variant="secondary"
                disabled={state.isStreaming}
              >
                <Download className="w-4 h-4 mr-2" />
                Export
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {state.messages.map((message) => (
          <div key={message.id} className="space-y-2">
            <div className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
              <Card className={`max-w-[80%] ${
                message.type === 'user' 
                  ? 'bg-primary text-primary-foreground' 
                  : message.type === 'error'
                  ? 'bg-destructive/10 border-destructive'
                  : message.type === 'status'
                  ? 'bg-blue-50 border-blue-200'
                  : 'bg-muted'
              }`}>
                <CardContent className="p-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      {message.type === 'status' && message.step && message.totalSteps && (
                        <div className="flex items-center gap-2 mb-2">
                          <Badge variant="outline" className="text-xs">
                            Step {message.step}/{message.totalSteps}
                          </Badge>
                        </div>
                      )}
                      <div className="whitespace-pre-wrap text-sm">
                        {message.content}
                      </div>
                    </div>
                    <span className="text-xs opacity-60 ml-2">
                      {message.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        ))}
        
        {state.isStreaming && (
          <div className="flex justify-start">
            <Card className="bg-muted">
              <CardContent className="p-3">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">
                    {state.currentStep > 0 && state.totalSteps > 0 
                      ? `Processing step ${state.currentStep}/${state.totalSteps}...`
                      : 'Processing...'
                    }
                  </span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </div>
  )
}