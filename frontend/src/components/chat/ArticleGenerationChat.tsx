import React, { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { 
  Conversation, 
  ConversationContent, 
  ConversationScrollToBottom,
  Message,
  MessageContent,
  MessageAvatar,
  PromptInput,
  PromptInputTextarea,
  PromptInputActions
} from '@/components/ai-elements'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

import { Progress } from '@/components/ui/progress'
import { CheckCircle, RefreshCw, Edit3, Send, Loader2, BookOpen, Download, RotateCcw } from 'lucide-react'
import { OutlinePreview } from '@/components/ui/markdown-preview'

interface ArticleMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  type?: 'status' | 'outline' | 'content' | 'feedback'
  outlineData?: any
  timestamp: Date
}

interface ArticleGenerationChatProps {
  collectionId?: number
}

export function ArticleGenerationChat({ collectionId }: ArticleGenerationChatProps) {
  const { t } = useTranslation()
  const [messages, setMessages] = useState<ArticleMessage[]>([])
  const [isGenerating, setIsGenerating] = useState(false)
  const [currentStep, setCurrentStep] = useState<'topic' | 'research' | 'outline' | 'content' | 'complete'>('topic')
  const [feedback, setFeedback] = useState('')
  const [topic, setTopic] = useState('')
  const [outline, setOutline] = useState<any>(null)
  const [articleId, setArticleId] = useState<number | null>(null)
  const [progressPercentage, setProgressPercentage] = useState(0)
  const [currentActivity, setCurrentActivity] = useState('')
  
  const feedbackRef = useRef<HTMLTextAreaElement>(null)
  const topicRef = useRef<HTMLTextAreaElement>(null)

  const addMessage = (content: string, role: 'user' | 'assistant' | 'system' = 'assistant', type?: 'status' | 'outline' | 'content' | 'feedback', outlineData?: any) => {
    const message: ArticleMessage = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      role,
      content,
      type,
      outlineData,
      timestamp: new Date()
    }
    setMessages(prev => [...prev, message])
    return message
  }

  const handleStartGeneration = async () => {
    if (!topic.trim()) return

    setIsGenerating(true)
    setCurrentStep('research')
    updateProgress('research', t('chat.searchingKnowledge'))
    
    // Add user message
    addMessage(topic, 'user')
    addMessage(t('chat.processingMessage'), 'system', 'status')

    try {
      // Step 1: Research phase
      const researchResponse = await fetch(`/api/articles/${collectionId}/generate-outline-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          collection_id: collectionId,
          topic,
          subtopics: [],
          article_type: "comprehensive",
          target_length: "medium"
        }),
      })

      if (researchResponse.ok && researchResponse.body) {
        const reader = researchResponse.body.getReader()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += new TextDecoder().decode(value)
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                handleStreamMessage(data)
              } catch (e) {
                console.error('Error parsing stream data:', e)
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error during generation:', error)
      addMessage(t('chat.errorMessage', { error: error instanceof Error ? error.message : 'Unknown error' }), 'system', 'status')
    } finally {
      setIsGenerating(false)
    }
  }

  const updateProgress = (step: string, activity: string = '') => {
    const stepProgress: Record<string, number> = {
      'topic': 0,
      'research': 25,
      'outline': 50,
      'content': 75,
      'complete': 100
    }
    setProgressPercentage(stepProgress[step] || 0)
    setCurrentActivity(activity)
  }

  const handleStreamMessage = (data: any) => {
    switch (data.type) {
      case 'research_complete':
        setCurrentStep('outline')
        updateProgress('outline', t('chat.creatingOutline'))
        
        // Handle different source types
        if (data.source_type === 'web_search') {
          addMessage(t('chat.researchCompleteWeb', { 
            web_results: data.web_results, 
            chunks: data.chunks_found 
          }), 'system', 'status')
        } else {
          addMessage(t('chat.researchComplete', { 
            chunks: data.chunks_found, 
            documents: data.documents_searched 
          }), 'system', 'status')
        }
        break
      case 'outline':
        // Stay in outline step until user approves or provides feedback
        setCurrentStep('outline')
        updateProgress('outline', t('chat.outlineComplete'))
        setOutline(data.outline)
        setArticleId(data.article_id)
        addMessage(t('chat.outlineGenerated', { topic }), 'assistant', 'outline', data.outline)
        break
      case 'content':
        addMessage(data.content, 'assistant', 'content')
        setCurrentStep('complete')
        updateProgress('complete', t('chat.generationComplete'))
        break
      case 'error':
        addMessage(t('chat.errorMessage', { error: data.message }), 'system', 'status')
        break
    }
  }

  const handleApproveOutline = async () => {
    if (!articleId) return
    
    setIsGenerating(true)
    setCurrentStep('content')
    updateProgress('content', t('chat.generatingContent'))
    addMessage(t('chat.generatingContent'), 'system', 'status')

    try {
      const response = await fetch(`/api/articles/${collectionId}/${articleId}/generate-content-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feedback: feedback || ''
        }),
      })

      if (response.ok && response.body) {
        const reader = response.body.getReader()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += new TextDecoder().decode(value)
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                handleStreamMessage(data)
              } catch (e) {
                console.error('Error parsing stream data:', e)
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error generating content:', error)
      addMessage(t('chat.errorMessage', { error: error instanceof Error ? error.message : 'Unknown error' }), 'system', 'status')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleRefineOutline = async () => {
    if (!articleId || !feedback.trim()) return
    
    setIsGenerating(true)
    addMessage(t('outline.refining'), 'system', 'status')

    try {
      const response = await fetch(`/api/articles/${collectionId}/${articleId}/refine-outline-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          refinement_instructions: feedback
        }),
      })

      if (response.ok && response.body) {
        const reader = response.body.getReader()
        let buffer = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += new TextDecoder().decode(value)
          const lines = buffer.split('\n')
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                handleStreamMessage(data)
              } catch (e) {
                console.error('Error parsing stream data:', e)
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error refining outline:', error)
      addMessage(t('chat.errorMessage', { error: error instanceof Error ? error.message : 'Unknown error' }), 'system', 'status')
    } finally {
      setIsGenerating(false)
      setFeedback('') // Clear feedback after use
    }
  }

  const handleSendFeedback = () => {
    if (!feedback.trim()) return
    
    addMessage(feedback, 'user', 'feedback')
    
    if (currentStep === 'outline' && outline) {
      handleRefineOutline()
    } else if (currentStep === 'content') {
      // Handle content refinement
      handleRefineContent()
    }
  }

  const handleRefineContent = async () => {
    // Implementation for content refinement
    // Similar to outline refinement but for content
  }



  const getSmartSuggestions = () => {
    switch (currentStep) {
      case 'research':
        return [
          { text: t('chat.suggestions.focusOnRecent'), icon: RefreshCw },
          { text: t('chat.suggestions.expandScope'), icon: BookOpen },
          { text: t('chat.suggestions.addSpecificTerms'), icon: Edit3 }
        ]
      case 'outline':
        return [
          { text: t('chat.suggestions.makeMoreDetailed'), icon: Edit3 },
          { text: t('chat.suggestions.reorderSections'), icon: RefreshCw },
          { text: t('chat.suggestions.addMoreSections'), icon: BookOpen }
        ]
      case 'content':
        return [
          { text: t('chat.suggestions.addMoreSources'), icon: BookOpen },
          { text: t('chat.suggestions.changeTone'), icon: RefreshCw },
          { text: t('chat.suggestions.expandExamples'), icon: Edit3 }
        ]
      default:
        return [
          { text: t('chat.suggestions.makeMoreDetailed'), icon: Edit3 },
          { text: t('chat.suggestions.addMoreSources'), icon: BookOpen },
          { text: t('chat.suggestions.changeTone'), icon: RefreshCw }
        ]
    }
  }

  const exportConversation = () => {
    const conversationData = {
      topic,
      collectionId,
      messages: messages.map(msg => ({
        role: msg.role,
        content: msg.content,
        type: msg.type,
        timestamp: msg.timestamp
      })),
      currentStep,
      articleId,
      exportTime: new Date().toISOString()
    }

    const blob = new Blob([JSON.stringify(conversationData, null, 2)], {
      type: 'application/json'
    })

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `conversation-${topic.replace(/[^a-zA-Z0-9]/g, '-')}-${Date.now()}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const resetConversation = () => {
    setMessages([])
    setCurrentStep('topic')
    setFeedback('')
    setTopic('')
    setOutline(null)
    setArticleId(null)
    setProgressPercentage(0)
    setCurrentActivity('')
    setIsGenerating(false)
  }

  return (
    <div className="flex flex-col min-h-screen max-w-6xl mx-auto">
      {/* Progress indicator */}
      <div className="bg-card border-b p-4 sticky top-0 z-10">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <BookOpen className="w-5 h-5" />
            {t('chat.articleGeneration')}
          </h2>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={exportConversation}
              disabled={messages.length === 0}
              className="flex items-center gap-1"
            >
              <Download className="w-4 h-4" />
              {t('chat.export')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={resetConversation}
              disabled={isGenerating}
              className="flex items-center gap-1"
            >
              <RotateCcw className="w-4 h-4" />
              {t('chat.reset')}
            </Button>
            <Badge variant={currentStep === 'complete' ? 'default' : 'secondary'}>
              {t(`chat.step.${currentStep}`)}
            </Badge>
          </div>
        </div>
        <div className="space-y-2">
          <Progress value={progressPercentage} className="w-full" />
          {currentActivity && (
            <p className="text-sm text-muted-foreground">{currentActivity}</p>
          )}
        </div>
      </div>

      <div className="flex flex-1 gap-4 p-4">
        {/* Main conversation area */}
        <div className="flex-1 flex flex-col">
          {/* Input area moved to top for better visibility */}
          <div className="mb-4 border-b pb-4 sticky top-20 bg-background z-5">
            {currentStep === 'topic' ? (
              <PromptInput onSubmit={(e: React.FormEvent) => { e.preventDefault(); handleStartGeneration(); }}>
                <PromptInputTextarea
                  ref={topicRef}
                  value={topic}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setTopic(e.target.value)}
                  placeholder={t('chat.topicPlaceholder')}
                  disabled={isGenerating}
                  className="min-h-[80px]"
                />
                <PromptInputActions>
                  <Button 
                    type="submit" 
                    disabled={!topic.trim() || isGenerating}
                    className="flex items-center gap-2"
                  >
                    <Send className="w-4 h-4" />
                    {t('chat.startGeneration')}
                  </Button>
                </PromptInputActions>
              </PromptInput>
            ) : (
              <PromptInput onSubmit={(e: React.FormEvent) => { e.preventDefault(); handleSendFeedback(); }}>
                <PromptInputTextarea
                  ref={feedbackRef}
                  value={feedback}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setFeedback(e.target.value)}
                  placeholder={t('chat.feedbackPlaceholder')}
                  disabled={isGenerating}
                  className="min-h-[80px]"
                />
                <PromptInputActions>
                  <Button 
                    type="submit" 
                    disabled={!feedback.trim() || isGenerating}
                    className="flex items-center gap-2"
                  >
                    <Send className="w-4 h-4" />
                    {t('chat.sendFeedback')}
                  </Button>
                </PromptInputActions>
              </PromptInput>
            )}
          </div>

          {/* Conversation area with natural height */}
          <Conversation className="border rounded-lg">
            <ConversationContent className="space-y-4">
              {messages.map((message) => (
                <Message key={message.id} from={message.role}>
                  <MessageAvatar 
                    src={message.role === 'user' ? '/user-avatar.png' : '/ai-avatar.png'}
                    name={message.role === 'user' ? 'You' : 'AI'}
                  />
                  <MessageContent>
                    {message.type === 'outline' && message.outlineData && (
                      <OutlinePreview 
                        outline={message.outlineData}
                        topic={topic}
                        articleType="comprehensive"
                        targetLength="medium"
                        onApprove={handleApproveOutline}
                        onRefine={() => feedbackRef.current?.focus()}
                        isGenerating={isGenerating}
                      />
                    )}
                    {message.type !== 'outline' && (
                      <div className="prose prose-sm max-w-none">
                        {message.type === 'content' ? (
                          <div className="bg-muted/30 p-4 rounded-lg">
                            <div dangerouslySetInnerHTML={{ __html: message.content.replace(/\n/g, '<br/>') }} />
                          </div>
                        ) : (
                          message.content
                        )}
                      </div>
                    )}
                  </MessageContent>
                </Message>
              ))}
              {isGenerating && (
                <Message from="assistant">
                  <MessageAvatar src="/ai-avatar.png" name="AI" />
                  <MessageContent>
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      {t('chat.generating')}
                    </div>
                  </MessageContent>
                </Message>
              )}
            </ConversationContent>
            <ConversationScrollToBottom />
          </Conversation>
        </div>

        {/* Sidebar for quick actions and context */}
        <div className="w-80 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">{t('chat.quickActions')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
{getSmartSuggestions().map((suggestion, index) => (
                <Button 
                  key={index}
                  variant="outline" 
                  size="sm" 
                  className="w-full justify-start"
                  disabled={currentStep === 'topic' || isGenerating}
                  onClick={() => setFeedback(suggestion.text)}
                >
                  <suggestion.icon className="w-4 h-4 mr-2" />
                  {suggestion.text}
                </Button>
              ))}
            </CardContent>
          </Card>

          {currentStep !== 'topic' && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">{t('chat.currentContext')}</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-sm text-muted-foreground">
                  <p><strong>{t('chat.topic')}:</strong> {topic}</p>
                  {collectionId && <p><strong>{t('chat.collection')}:</strong> {collectionId}</p>}
                  <p><strong>{t('chat.status')}:</strong> {t(`chat.step.${currentStep}`)}</p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}

