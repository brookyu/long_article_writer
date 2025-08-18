import React, { useState, useEffect } from 'react'
import { 
  FileText, 
  Image, 
  FileCode, 
  Database, 
  Archive,
  AlertCircle,
  CheckCircle,
  Clock,
  X,
  Eye,
  Download
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

interface FileInfo {
  file: File
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  error?: string
  preview?: string
  relativePath?: string
}

interface FilePreviewProps {
  files: FileInfo[]
  onRemoveFile?: (index: number) => void
  onRetryFile?: (index: number) => void
  showPreviews?: boolean
  maxPreviewSize?: number
}

const getFileIcon = (fileName: string) => {
  const ext = fileName.toLowerCase().split('.').pop()
  
  switch (ext) {
    case 'txt':
    case 'md':
    case 'markdown':
    case 'doc':
    case 'docx':
    case 'pdf':
    case 'rtf':
      return <FileText className="h-4 w-4" />
    case 'jpg':
    case 'jpeg':
    case 'png':
    case 'gif':
    case 'svg':
    case 'webp':
      return <Image className="h-4 w-4" />
    case 'html':
    case 'htm':
    case 'css':
    case 'js':
    case 'ts':
    case 'jsx':
    case 'tsx':
    case 'json':
      return <FileCode className="h-4 w-4" />
    case 'csv':
    case 'xlsx':
    case 'xls':
      return <Database className="h-4 w-4" />
    case 'zip':
    case 'tar':
    case 'gz':
    case 'rar':
      return <Archive className="h-4 w-4" />
    default:
      return <FileText className="h-4 w-4" />
  }
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />
    case 'failed':
      return <AlertCircle className="h-4 w-4 text-red-500" />
    case 'processing':
      return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />
    default:
      return <Clock className="h-4 w-4 text-gray-400" />
  }
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800'
    case 'failed':
      return 'bg-red-100 text-red-800'
    case 'processing':
      return 'bg-blue-100 text-blue-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const readFilePreview = async (file: File, maxSize: number = 1000): Promise<string> => {
  return new Promise((resolve) => {
    const reader = new FileReader()
    
    reader.onload = (e) => {
      const text = e.target?.result as string
      if (text.length > maxSize) {
        resolve(text.substring(0, maxSize) + '...')
      } else {
        resolve(text)
      }
    }
    
    reader.onerror = () => {
      resolve('Preview not available')
    }
    
    // Only preview text-based files
    const ext = file.name.toLowerCase().split('.').pop()
    const textFormats = ['txt', 'md', 'markdown', 'html', 'htm', 'css', 'js', 'ts', 'json', 'csv']
    
    if (textFormats.includes(ext || '')) {
      reader.readAsText(file)
    } else {
      resolve('Binary file - preview not available')
    }
  })
}

export function FilePreview({ 
  files, 
  onRemoveFile, 
  onRetryFile,
  showPreviews = true,
  maxPreviewSize = 500
}: FilePreviewProps) {
  const [expandedFiles, setExpandedFiles] = useState<Set<number>>(new Set())
  const [filePreviews, setFilePreviews] = useState<Map<number, string>>(new Map())

  useEffect(() => {
    if (!showPreviews) return

    const loadPreviews = async () => {
      const newPreviews = new Map<number, string>()
      
      for (let i = 0; i < files.length; i++) {
        const file = files[i]
        if (file.file.size < 100 * 1024) { // Only preview files smaller than 100KB
          try {
            const preview = await readFilePreview(file.file, maxPreviewSize)
            newPreviews.set(i, preview)
          } catch (error) {
            newPreviews.set(i, 'Error loading preview')
          }
        } else {
          newPreviews.set(i, 'File too large for preview')
        }
      }
      
      setFilePreviews(newPreviews)
    }

    loadPreviews()
  }, [files, showPreviews, maxPreviewSize])

  const toggleExpanded = (index: number) => {
    const newExpanded = new Set(expandedFiles)
    if (newExpanded.has(index)) {
      newExpanded.delete(index)
    } else {
      newExpanded.add(index)
    }
    setExpandedFiles(newExpanded)
  }

  const getFileStats = () => {
    const total = files.length
    const completed = files.filter(f => f.status === 'completed').length
    const failed = files.filter(f => f.status === 'failed').length
    const processing = files.filter(f => f.status === 'processing').length
    const pending = files.filter(f => f.status === 'pending').length
    
    const totalSize = files.reduce((acc, f) => acc + f.file.size, 0)
    
    return { total, completed, failed, processing, pending, totalSize }
  }

  const stats = getFileStats()

  if (files.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <FileText className="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p>No files selected</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* File Statistics */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>File Upload Overview</span>
            <Badge variant="outline">
              {stats.total} file{stats.total !== 1 ? 's' : ''}
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
            <div className="text-center">
              <div className="text-2xl font-bold text-green-600">{stats.completed}</div>
              <div className="text-muted-foreground">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-600">{stats.processing}</div>
              <div className="text-muted-foreground">Processing</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-gray-600">{stats.pending}</div>
              <div className="text-muted-foreground">Pending</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-red-600">{stats.failed}</div>
              <div className="text-muted-foreground">Failed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">{formatFileSize(stats.totalSize)}</div>
              <div className="text-muted-foreground">Total Size</div>
            </div>
          </div>
          
          {/* Overall Progress */}
          {stats.processing > 0 || stats.completed > 0 ? (
            <div className="mt-4">
              <div className="flex justify-between text-sm mb-1">
                <span>Overall Progress</span>
                <span>{Math.round((stats.completed / stats.total) * 100)}%</span>
              </div>
              <Progress value={(stats.completed / stats.total) * 100} className="h-2" />
            </div>
          ) : null}
        </CardContent>
      </Card>

      {/* File List */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {files.map((fileInfo, index) => (
          <Card key={index} className="transition-all duration-200 hover:shadow-md">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                {/* File Icon */}
                <div className="flex-shrink-0">
                  {getFileIcon(fileInfo.file.name)}
                </div>
                
                {/* File Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-sm font-medium truncate">
                      {fileInfo.relativePath || fileInfo.file.name}
                    </p>
                    <Badge className={`text-xs ${getStatusColor(fileInfo.status)}`}>
                      {fileInfo.status}
                    </Badge>
                  </div>
                  
                  <div className="flex items-center gap-4 text-xs text-muted-foreground">
                    <span>{formatFileSize(fileInfo.file.size)}</span>
                    <span>{fileInfo.file.type || 'Unknown type'}</span>
                    {fileInfo.file.lastModified && (
                      <span>{new Date(fileInfo.file.lastModified).toLocaleDateString()}</span>
                    )}
                  </div>
                  
                  {/* Progress Bar */}
                  {fileInfo.status === 'processing' && (
                    <div className="mt-2">
                      <Progress value={fileInfo.progress} className="h-1" />
                    </div>
                  )}
                  
                  {/* Error Message */}
                  {fileInfo.error && (
                    <div className="mt-2 text-xs text-red-600 bg-red-50 p-2 rounded">
                      {fileInfo.error}
                    </div>
                  )}
                </div>
                
                {/* Status & Actions */}
                <div className="flex items-center gap-2">
                  {getStatusIcon(fileInfo.status)}
                  
                  {showPreviews && filePreviews.has(index) && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => toggleExpanded(index)}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  )}
                  
                  {fileInfo.status === 'failed' && onRetryFile && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onRetryFile(index)}
                    >
                      Retry
                    </Button>
                  )}
                  
                  {onRemoveFile && fileInfo.status === 'pending' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onRemoveFile(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              </div>
              
              {/* File Preview */}
              {showPreviews && expandedFiles.has(index) && filePreviews.has(index) && (
                <Collapsible open={expandedFiles.has(index)}>
                  <CollapsibleContent>
                    <div className="mt-3 pt-3 border-t">
                      <div className="text-xs text-muted-foreground mb-2">File Preview:</div>
                      <pre className="text-xs bg-gray-50 p-3 rounded max-h-32 overflow-auto whitespace-pre-wrap">
                        {filePreviews.get(index)}
                      </pre>
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}