import React from 'react'
import ReactMarkdown from 'react-markdown'
import { Card, CardContent, CardHeader, CardTitle } from './card'
import { Badge } from './badge'

interface MarkdownPreviewProps {
  content: string
  title?: string
  className?: string
}

export function MarkdownPreview({ content, title, className = '' }: MarkdownPreviewProps) {
  return (
    <div className={`markdown-preview ${className}`}>
      {title && (
        <div className="mb-4">
          <h3 className="text-lg font-semibold mb-2">{title}</h3>
        </div>
      )}
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <ReactMarkdown
          components={{
            // Custom styling for different markdown elements
            h1: ({ children }) => <h1 className="text-xl font-bold mb-3 text-primary">{children}</h1>,
            h2: ({ children }) => <h2 className="text-lg font-semibold mb-2 text-primary">{children}</h2>,
            h3: ({ children }) => <h3 className="text-md font-medium mb-2">{children}</h3>,
            h4: ({ children }) => <h4 className="text-sm font-medium mb-1">{children}</h4>,
            p: ({ children }) => <p className="mb-2 leading-relaxed">{children}</p>,
            ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
            li: ({ children }) => <li className="text-sm">{children}</li>,
            strong: ({ children }) => <strong className="font-semibold text-primary">{children}</strong>,
            em: ({ children }) => <em className="italic text-muted-foreground">{children}</em>,
            code: ({ children }) => (
              <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">{children}</code>
            ),
            pre: ({ children }) => (
              <pre className="bg-muted p-3 rounded-lg overflow-x-auto text-xs">{children}</pre>
            ),
            blockquote: ({ children }) => (
              <blockquote className="border-l-4 border-primary pl-4 italic text-muted-foreground">
                {children}
              </blockquote>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  )
}

interface OutlinePreviewProps {
  outline: any
  topic: string
  articleType: string
  targetLength: string
  onApprove: () => void
  onRefine: () => void
  isGenerating: boolean
}

export function OutlinePreview({ 
  outline, 
  topic, 
  articleType, 
  targetLength, 
  onApprove, 
  onRefine, 
  isGenerating 
}: OutlinePreviewProps) {
  // Extract markdown content from outline
  const getMarkdownContent = (outline: any): string => {
    if (typeof outline === 'string') {
      // Check if it's already markdown-like content
      if (outline.includes('#') || outline.includes('\n')) {
        return outline
      }
      return outline
    }
    
    if (outline && typeof outline === 'object') {
      // If it's a structured outline, convert to markdown
      if (outline.outline_text) {
        return outline.outline_text
      }
      
      // Try to extract content from various possible structures
      if (outline.content) {
        return outline.content
      }
      
      // Handle the common JSON structure with topic and outline_text
      if (outline.topic && outline.outline_text) {
        return `# ${outline.topic}\n\n${outline.outline_text}`
      }
      
      if (outline.sections && Array.isArray(outline.sections)) {
        let markdown = `# ${topic}\n\n`
        outline.sections.forEach((section: any, index: number) => {
          if (typeof section === 'string') {
            markdown += `## ${index + 1}. ${section}\n\n`
          } else if (section.title) {
            markdown += `## ${section.title}\n\n`
            if (section.content) {
              markdown += `${section.content}\n\n`
            }
            if (section.subsections && Array.isArray(section.subsections)) {
              section.subsections.forEach((subsection: any) => {
                if (typeof subsection === 'string') {
                  markdown += `### ${subsection}\n\n`
                } else if (subsection.title) {
                  markdown += `### ${subsection.title}\n\n`
                  if (subsection.content) {
                    markdown += `${subsection.content}\n\n`
                  }
                }
              })
            }
          }
        })
        return markdown
      }
    }
    
    // Fallback: if it looks like JSON, format it nicely
    try {
      const parsed = typeof outline === 'string' ? JSON.parse(outline) : outline
      if (parsed && typeof parsed === 'object') {
        // Try to extract readable content from JSON
        if (parsed.outline_text) {
          return parsed.outline_text
        }
        if (parsed.content) {
          return parsed.content
        }
        // Otherwise show formatted JSON
        return `\`\`\`json\n${JSON.stringify(parsed, null, 2)}\n\`\`\``
      }
    } catch {
      // If JSON parsing fails, return as string
    }
    
    return String(outline)
  }

  const markdownContent = getMarkdownContent(outline)

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">📋 Article Outline</CardTitle>
          <div className="flex gap-2">
            <Badge variant="secondary">{articleType}</Badge>
            <Badge variant="outline">{targetLength}</Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <MarkdownPreview 
            content={markdownContent}
            className="border rounded-lg p-4 bg-muted/30"
          />
          
          <div className="flex gap-2 pt-2 border-t">
            <button 
              onClick={onApprove} 
              disabled={isGenerating}
              className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>✅</span>
              Approve & Continue
            </button>
            <button 
              variant="outline" 
              onClick={onRefine}
              disabled={isGenerating}
              className="flex items-center gap-2 px-4 py-2 border border-input bg-background hover:bg-accent hover:text-accent-foreground rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span>✏️</span>
              Provide Feedback
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}