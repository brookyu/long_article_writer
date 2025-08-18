import React, { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Textarea } from '@/components/ui/textarea'
import { 
  Send, 
  Loader2, 
  RefreshCw, 
  ThumbsUp, 
  ThumbsDown,
  Copy,
  Edit3,
  BookOpen,
  FileText,
  Lightbulb,
  CheckCircle,
  AlertCircle
} from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  type?: 'text' | 'outline' | 'research' | 'status' | 'error'
  data?: any
  feedback?: 'positive' | 'negative' | null
}

interface ChatSession {
  sessionId: string
  collectionId: number
  collectionName?: string
  phase: 'initial' | 'research' | 'outline' | 'refinement' | 'content'
}

interface AIArticleChatProps {
  collectionId: number
  collectionName?: string
  onArticleGenerated?: (article: any) => void
}

interface StreamEvent {
  event_type: string
  data: any
  timestamp: string
  session_id?: string
}

export function AIArticleChat({ 
  collectionId, 
  collectionName, 
  onArticleGenerated 
}: AIArticleChatProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputValue, setInputValue] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [session, setSession] = useState<ChatSession | null>(null)
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [currentPhase, setCurrentPhase] = useState<string>('initial')
  
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const addMessage = useCallback((message: Omit<Message, 'id' | 'timestamp'>) => {
    const newMessage: Message = {
      ...message,
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      feedback: null
    }
    setMessages(prev => [...prev, newMessage])
    return newMessage.id
  }, [])

  const updateMessage = useCallback((id: string, updates: Partial<Message>) => {
    setMessages(prev => prev.map(msg => 
      msg.id === id ? { ...msg, ...updates } : msg
    ))
  }, [])

  const startSession = async () => {
    try {
      const response = await fetch('/api/chat/start-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          collection_id: collectionId,
          initial_message: {
            content: "I'd like to create an article",
            message_type: "user"
          },
          user_preferences: {
            article_type: "comprehensive",
            target_length: "medium",
            writing_style: "professional"
          }
        })
      })

      if (!response.ok) throw new Error('Failed to start session')
      
      const result = await response.json()
      setSession({
        sessionId: result.session_id,
        collectionId,
        collectionName,
        phase: 'initial'
      })

      // Add welcome message
      addMessage({
        role: 'assistant',
        content: `Welcome! I'm your AI writing assistant. I'll help you create a comprehensive article using the "${collectionName || `Collection ${collectionId}`}" knowledge base.\n\nWhat topic would you like to write about?`,
        type: 'text'
      })

      // Add suggestions
      setSuggestions([
        "Research recent developments in artificial intelligence",
        "Create an outline for a guide on sustainable technology",
        "Write about the future of remote work",
        "Analyze trends in digital transformation"
      ])

    } catch (error) {
      console.error('Failed to start session:', error)
      addMessage({
        role: 'system',
        content: 'Failed to start chat session. Please try again.',
        type: 'error'
      })
    }
  }

  const handleStream = async (response: Response, messageId: string) => {
    if (!response.body) return

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const eventData: StreamEvent = JSON.parse(line.slice(6))
              await handleStreamEvent(eventData, messageId)
            } catch (e) {
              console.error('Failed to parse stream event:', e)
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  }

  const handleStreamEvent = async (event: StreamEvent, messageId: string) => {
    switch (event.event_type) {
      case 'status':
        updateMessage(messageId, {
          content: event.data.message,
          type: 'status'
        })
        break

      case 'intent_detected':
        updateMessage(messageId, {
          content: `🎯 ${event.data.message}`,
          type: 'status'
        })
        break

      case 'agent_response':
        const result = event.data.result
        let content = ''
        let type: Message['type'] = 'text'

        if (event.data.workflow_type === 'research') {
          content = `🔍 **Research Complete**\n\nFound relevant information from ${result.data?.research_results?.length || 0} sources.`
          type = 'research'
        } else if (event.data.workflow_type === 'outline') {
          content = `📋 **Outline Created**\n\n${formatOutline(result.data)}`
          type = 'outline'
        } else if (event.data.workflow_type === 'feedback') {
          content = `💡 **Feedback Processed**\n\nRecommended actions: ${result.data?.recommended_actions?.join(', ') || 'None'}`
          type = 'text'
        }

        updateMessage(messageId, { content, type, data: result.data })
        break

      case 'phase_update':
        setCurrentPhase(event.data.phase)
        updatePhaseActions(event.data.next_actions)
        break

      case 'usage_stats':
        // Could display usage info in a subtle way
        console.log('Usage stats:', event.data)
        break

      case 'error':
        updateMessage(messageId, {
          content: `❌ Error: ${event.data.message}`,
          type: 'error'
        })
        break
    }
  }

  const formatOutline = (outlineData: any): string => {
    if (!outlineData) return 'Outline data not available'
    
    // Format outline based on the structure
    if (outlineData.title) {
      let formatted = `# ${outlineData.title}\n\n`
      
      if (outlineData.introduction) {
        formatted += `## Introduction\n${outlineData.introduction}\n\n`
      }
      
      if (outlineData.sections) {
        outlineData.sections.forEach((section: any, index: number) => {
          formatted += `## ${index + 1}. ${section.title}\n`
          if (section.description) {
            formatted += `${section.description}\n`
          }
          if (section.key_points) {
            section.key_points.forEach((point: string) => {
              formatted += `- ${point}\n`
            })
          }
          formatted += '\n'
        })
      }
      
      if (outlineData.conclusion) {
        formatted += `## Conclusion\n${outlineData.conclusion}\n`
      }
      
      return formatted
    }
    
    return JSON.stringify(outlineData, null, 2)
  }

  const updatePhaseActions = (actions: string[]) => {
    const actionSuggestions: string[] = []
    
    actions.forEach(action => {
      switch (action) {
        case 'create_outline':
          actionSuggestions.push('Create an outline from this research')
          break
        case 'refine_outline':
          actionSuggestions.push('Refine the outline structure')
          break
        case 'generate_content':
          actionSuggestions.push('Generate the full article content')
          break
        case 'refine_research':
          actionSuggestions.push('Research additional related topics')
          break
        default:
          actionSuggestions.push(`Next: ${action.replace(/_/g, ' ')}`)
      }
    })
    
    setSuggestions(actionSuggestions)
  }

  const sendMessage = async (content: string = inputValue) => {
    if (!content.trim() || !session || isStreaming) return

    // Add user message
    const userMessageId = addMessage({
      role: 'user',
      content: content.trim(),
      type: 'text'
    })

    // Add loading assistant message
    const assistantMessageId = addMessage({
      role: 'assistant',
      content: 'Processing your request...',
      type: 'status'
    })

    setInputValue('')
    setSuggestions([])
    setIsStreaming(true)

    try {
      abortControllerRef.current = new AbortController()
      
      const response = await fetch(`/api/chat/message/${session.sessionId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: content.trim(),
          message_type: 'user'
        }),
        signal: abortControllerRef.current.signal
      })

      if (!response.ok) throw new Error('Failed to send message')

      await handleStream(response, assistantMessageId)

    } catch (error: any) {
      if (error.name !== 'AbortError') {
        console.error('Failed to send message:', error)
        updateMessage(assistantMessageId, {
          content: 'Sorry, I encountered an error processing your request. Please try again.',
          type: 'error'
        })
      }
    } finally {
      setIsStreaming(false)
      abortControllerRef.current = null
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion)
  }

  const handleFeedback = async (messageId: string, feedback: 'positive' | 'negative') => {
    updateMessage(messageId, { feedback })
    // Could send feedback to backend for learning
  }

  const copyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content)
      // Could show a toast notification
    } catch (error) {
      console.error('Failed to copy:', error)
    }
  }

  const clearChat = () => {
    setMessages([])
    setSuggestions([])
    setSession(null)
    setCurrentPhase('initial')
  }

  // Initialize session on mount
  useEffect(() => {
    if (!session) {
      startSession()
    }
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const getPhaseIcon = (phase: string) => {
    switch (phase) {
      case 'research': return <BookOpen className="w-4 h-4" />
      case 'outline': return <FileText className="w-4 h-4" />
      case 'refinement': return <Edit3 className="w-4 h-4" />
      case 'content': return <CheckCircle className="w-4 h-4" />
      default: return <Lightbulb className="w-4 h-4" />
    }
  }

  const getMessageIcon = (type: Message['type']) => {
    switch (type) {
      case 'research': return <BookOpen className="w-4 h-4 text-blue-500" />
      case 'outline': return <FileText className="w-4 h-4 text-green-500" />
      case 'status': return <Loader2 className="w-4 h-4 text-yellow-500 animate-spin" />
      case 'error': return <AlertCircle className="w-4 h-4 text-red-500" />
      default: return null
    }
  }

  if (!session) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-4" />
          <p>Initializing AI assistant...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full max-h-screen bg-gradient-to-b from-background to-muted/20">
      {/* Header */}
      <div className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center justify-between p-4">
          <div className="flex items-center gap-3">
            {getPhaseIcon(currentPhase)}
            <div>
              <h2 className="text-xl font-semibold">AI Article Assistant</h2>
              <p className="text-sm text-muted-foreground">
                {collectionName || `Collection ${collectionId}`} • Phase: {currentPhase}
              </p>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={clearChat}
            disabled={isStreaming}
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
          <div key={message.id} className="space-y-2">
            <div className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <Card className={`max-w-[85%] ${
                message.role === 'user' 
                  ? 'bg-primary text-primary-foreground' 
                  : message.type === 'error'
                  ? 'bg-destructive/10 border-destructive'
                  : message.type === 'status'
                  ? 'bg-blue-50 border-blue-200'
                  : 'bg-muted/50'
              }`}>
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    {message.role !== 'user' && getMessageIcon(message.type)}
                    <div className="flex-1 space-y-2">
                      <div className="prose prose-sm max-w-none">
                        {message.content.split('\n').map((line, index) => (
                          <p key={index} className="whitespace-pre-wrap">
                            {line}
                          </p>
                        ))}
                      </div>
                      
                      {/* Message actions */}
                      {message.role === 'assistant' && message.type !== 'status' && (
                        <div className="flex items-center gap-2 pt-2 border-t border-border/40">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleFeedback(message.id, 'positive')}
                            className={`h-8 ${message.feedback === 'positive' ? 'bg-green-100 text-green-700' : ''}`}
                          >
                            <ThumbsUp className="w-3 h-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleFeedback(message.id, 'negative')}
                            className={`h-8 ${message.feedback === 'negative' ? 'bg-red-100 text-red-700' : ''}`}
                          >
                            <ThumbsDown className="w-3 h-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => copyMessage(message.content)}
                            className="h-8"
                          >
                            <Copy className="w-3 h-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                    <span className="text-xs opacity-60 mt-1">
                      {message.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        ))}
        
        {isStreaming && (
          <div className="flex justify-start">
            <Card className="bg-muted/50">
              <CardContent className="p-3">
                <div className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span className="text-sm">AI is thinking...</span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="border-t bg-background/95 p-4">
          <div className="space-y-2">
            <p className="text-sm font-medium text-muted-foreground">Suggestions:</p>
            <div className="flex flex-wrap gap-2">
              {suggestions.map((suggestion, index) => (
                <Badge
                  key={index}
                  variant="secondary"
                  className="cursor-pointer hover:bg-secondary/80 transition-colors"
                  onClick={() => handleSuggestionClick(suggestion)}
                >
                  {suggestion}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Input */}
      <div className="border-t bg-background/95 p-4">
        <div className="flex gap-2">
          <Textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message... (Shift+Enter for new line)"
            disabled={isStreaming}
            className="min-h-[40px] max-h-32 resize-none"
            rows={1}
          />
          <Button
            onClick={() => sendMessage()}
            disabled={isStreaming || !inputValue.trim()}
            size="sm"
            className="self-end"
          >
            {isStreaming ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>
      </div>
    </div>
  )
}