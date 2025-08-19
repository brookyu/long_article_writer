import React, { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Upload, Square, CheckCircle, AlertCircle, FileText, Folder, X } from 'lucide-react'
import { folderUploadApi } from '@/lib/api'

interface StreamingDocumentUploadProps {
  collectionId: number
  onUploadComplete?: (successCount: number, totalCount: number) => void
  onUploadError?: (error: string) => void
  onClose?: () => void
}

interface UploadProgress {
  processed: number
  successful: number
  failed: number
  total: number
  percentage: number
}

interface FileStatus {
  filename: string
  status: 'pending' | 'processing' | 'success' | 'failed'
  error?: string
  document_id?: number
  chunks_created?: number
}

export function StreamingDocumentUpload({ 
  collectionId, 
  onUploadComplete, 
  onUploadError,
  onClose 
}: StreamingDocumentUploadProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [progress, setProgress] = useState<UploadProgress>({ processed: 0, successful: 0, failed: 0, total: 0, percentage: 0 })
  const [fileStatuses, setFileStatuses] = useState<FileStatus[]>([])
  const [currentMessage, setCurrentMessage] = useState<string>('')
  const [uploadType, setUploadType] = useState<'files' | 'folder' | 'directory'>(() => {
    // Try to restore upload type from localStorage
    const saved = localStorage.getItem(`uploadType_${collectionId}`)
    console.log('🔄 Restoring upload type from localStorage:', saved)
    return (saved as 'files' | 'folder' | 'directory') || 'files'
  })

  // Debug upload type changes
  const setUploadTypeWithLogging = (type: 'files' | 'folder' | 'directory') => {
    console.log('🔄 Upload type changing from', uploadType, 'to', type)
    setUploadType(type)
    // Save to localStorage
    localStorage.setItem(`uploadType_${collectionId}`, type)
  }

  // Save upload type to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem(`uploadType_${collectionId}`, uploadType)
    console.log('💾 Saved upload type to localStorage:', uploadType)
  }, [uploadType, collectionId])

  // Monitor upload type changes
  useEffect(() => {
    console.log('📊 Upload type state changed to:', uploadType)
  }, [uploadType])

  // Monitor component renders and key changes
  useEffect(() => {
    console.log('🔄 StreamingDocumentUpload component rendered/re-rendered')
    console.log('🔄 Current uploadType on render:', uploadType)
    console.log('🔄 Current isUploading on render:', isUploading)
    console.log('🔄 Component key should be:', `upload-${collectionId}`)
  })

  // Monitor when component mounts/unmounts
  useEffect(() => {
    console.log('🎯 StreamingDocumentUpload component MOUNTED')
    return () => {
      console.log('💀 StreamingDocumentUpload component UNMOUNTED')
    }
  }, [])
  const [isCollapsed, setIsCollapsed] = useState(false)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const directoryInputRef = useRef<HTMLInputElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const handleFileUpload = (files: FileList) => {
    if (isUploading) return
    
    setIsUploading(true)
    setIsCollapsed(false)
    setProgress({ processed: 0, successful: 0, failed: 0, total: files.length, percentage: 0 })
    setFileStatuses(Array.from(files).map(f => ({ filename: f.name, status: 'pending' })))
    setCurrentMessage('Starting file upload...')
    
    abortControllerRef.current = folderUploadApi.streamUploadWithFetch(
      collectionId,
      files,
      (data) => {
        console.log('📨 Streaming data:', data)
        
        switch (data.type) {
          case 'start':
            setCurrentMessage(data.message)
            break
            
          case 'file_start':
            setCurrentMessage(`Processing: ${data.filename}`)
            setFileStatuses(prev => prev.map(f => 
              f.filename === data.filename 
                ? { ...f, status: 'processing' }
                : f
            ))
            break
            
          case 'file_success':
            setFileStatuses(prev => prev.map(f => 
              f.filename === data.filename 
                ? { ...f, status: 'success', document_id: data.document_id, chunks_created: data.chunks_created }
                : f
            ))
            break
            
          case 'file_failed':
            setFileStatuses(prev => prev.map(f => 
              f.filename === data.filename 
                ? { ...f, status: 'failed', error: data.error }
                : f
            ))
            break
            
          case 'progress':
            setProgress({
              processed: data.processed,
              successful: data.successful,
              failed: data.failed,
              total: data.total,
              percentage: Math.round(data.percentage)
            })
            setCurrentMessage(`Progress: ${data.processed}/${data.total} files (${Math.round(data.percentage)}%)`)
            break
            
          case 'complete':
            setCurrentMessage(data.message)
            setIsUploading(false)
            onUploadComplete?.(data.successful || progress.successful, data.total || progress.total)
            break
            
          case 'error':
            setCurrentMessage(`Error: ${data.message}`)
            setIsUploading(false)
            onUploadError?.(data.message)
            break
        }
      },
      (error) => {
        console.error('❌ Upload error:', error)
        setCurrentMessage(`Upload failed: ${error.message}`)
        setIsUploading(false)
        onUploadError?.(error.message)
      },
      () => {
        console.log('✅ Upload complete!')
        setIsUploading(false)
        if (progress.total > 0) {
          onUploadComplete?.(progress.successful, progress.total)
        }
      }
    )
  }

  const handleDirectoryUpload = (files: FileList) => {
    console.log('🔍 handleDirectoryUpload called with files:', files)
    console.log('📁 Number of files selected:', files.length)
    console.log('📁 Current upload type at start:', uploadType)
    console.log('📂 Files list:', Array.from(files).map(f => ({
      name: f.name,
      size: f.size,
      type: f.type,
      webkitRelativePath: (f as any).webkitRelativePath
    })))

    if (isUploading) {
      console.log('⚠️ Already uploading, ignoring directory upload')
      return
    }

    if (!files || files.length === 0) {
      console.warn('⚠️ No files selected in directory upload')
      setCurrentMessage('No files found in the selected folder. Please try selecting a folder with supported file types.')
      return
    }

    // Filter for supported file types
    const supportedExtensions = ['.txt', '.md', '.pdf', '.docx', '.doc', '.html', '.csv', '.json', '.rtf']
    const supportedFiles = Array.from(files).filter(file => {
      const extension = '.' + file.name.split('.').pop()?.toLowerCase()
      return supportedExtensions.includes(extension)
    })

    console.log('📋 Supported files found:', supportedFiles.length)
    console.log('📋 Supported files:', supportedFiles.map(f => f.name))

    if (supportedFiles.length === 0) {
      console.warn('⚠️ No supported files found in directory')
      setCurrentMessage(`No supported files found in the selected folder. Supported formats: ${supportedExtensions.join(', ')}`)
      return
    }

    setIsUploading(true)
    setIsCollapsed(false)
    setProgress({ processed: 0, successful: 0, failed: 0, total: supportedFiles.length, percentage: 0 })
    setFileStatuses([])
    setCurrentMessage(`Starting directory upload... Found ${supportedFiles.length} supported files`)

    // Create a FileList-like object from the supported files
    const createFileList = (files: File[]): FileList => {
      const fileList = {
        length: files.length,
        item: (index: number) => files[index] || null,
        [Symbol.iterator]: function* () {
          for (const file of files) {
            yield file
          }
        }
      }
      // Add array-like access
      files.forEach((file, index) => {
        (fileList as any)[index] = file
      })
      return fileList as FileList
    }

    const fileList = createFileList(supportedFiles)

    // Use the same file upload handler since we now have individual files
    abortControllerRef.current = folderUploadApi.streamUploadWithFetch(
      collectionId,
      fileList,
      (data) => {
        console.log('📨 Streaming directory data:', data)
        
        switch (data.type) {
          case 'start':
            setCurrentMessage(data.message)
            break
            
          case 'file_start':
            setCurrentMessage(`Processing: ${data.filename}`)
            setFileStatuses(prev => {
              const existing = prev.find(f => f.filename === data.filename)
              if (existing) {
                return prev.map(f => 
                  f.filename === data.filename 
                    ? { ...f, status: 'processing' }
                    : f
                )
              } else {
                return [...prev, { filename: data.filename, status: 'processing' }]
              }
            })
            break
            
          case 'file_success':
            setFileStatuses(prev => prev.map(f => 
              f.filename === data.filename 
                ? { ...f, status: 'success', document_id: data.document_id, chunks_created: data.chunks_created }
                : f
            ))
            break
            
          case 'file_failed':
            setFileStatuses(prev => prev.map(f => 
              f.filename === data.filename 
                ? { ...f, status: 'failed', error: data.error }
                : f
            ))
            break
            
          case 'progress':
            setProgress({
              processed: data.processed,
              successful: data.successful,
              failed: data.failed,
              total: data.total,
              percentage: data.percentage
            })
            break
            
          case 'complete':
            setCurrentMessage(data.message)
            setIsUploading(false)
            if (data.summary) {
              onUploadComplete?.(data.summary.successful, data.summary.total)
            }
            break
            
          case 'error':
            setCurrentMessage(`Error: ${data.message}`)
            setIsUploading(false)
            onUploadError?.(data.message)
            break
        }
      },
      (error) => {
        console.error('❌ Directory upload error:', error)
        setCurrentMessage(`Upload failed: ${error.message}`)
        setIsUploading(false)
        onUploadError?.(error.message)
      },
      () => {
        console.log('✅ Directory upload complete!')
        setIsUploading(false)
        if (progress.total > 0) {
          onUploadComplete?.(progress.successful, progress.total)
        }
      }
    )
  }

  const handleFolderUpload = (file: File) => {
    if (isUploading) return
    
    setIsUploading(true)
    setIsCollapsed(false)
    setProgress({ processed: 0, successful: 0, failed: 0, total: 0, percentage: 0 })
    setFileStatuses([])
    setCurrentMessage('Starting ZIP folder upload...')
    
    abortControllerRef.current = folderUploadApi.streamFolderUploadWithFetch(
      collectionId,
      file,
      (data) => {
        console.log('📨 Streaming folder data:', data)
        
        switch (data.type) {
          case 'start':
            setCurrentMessage(data.message)
            break
            
          case 'extraction_complete':
            setCurrentMessage(data.message)
            setProgress(prev => ({ ...prev, total: data.total_files }))
            setFileStatuses([])
            break
            
          case 'file_start':
            setCurrentMessage(`Processing: ${data.filename}`)
            setFileStatuses(prev => {
              const existing = prev.find(f => f.filename === data.filename)
              if (existing) {
                return prev.map(f => 
                  f.filename === data.filename 
                    ? { ...f, status: 'processing' }
                    : f
                )
              } else {
                return [...prev, { filename: data.filename, status: 'processing' }]
              }
            })
            break
            
          case 'file_success':
            setFileStatuses(prev => prev.map(f => 
              f.filename === data.filename 
                ? { ...f, status: 'success', document_id: data.document_id, chunks_created: data.chunks_created }
                : f
            ))
            break
            
          case 'file_failed':
            setFileStatuses(prev => prev.map(f => 
              f.filename === data.filename 
                ? { ...f, status: 'failed', error: data.error }
                : f
            ))
            break
            
          case 'progress':
            setProgress({
              processed: data.processed,
              successful: data.successful,
              failed: data.failed,
              total: data.total,
              percentage: Math.round(data.percentage)
            })
            setCurrentMessage(`Progress: ${data.processed}/${data.total} files (${Math.round(data.percentage)}%)`)
            break
            
          case 'complete':
            setCurrentMessage(data.message)
            setIsUploading(false)
            onUploadComplete?.(data.successful || progress.successful, data.total || progress.total)
            break
            
          case 'error':
            setCurrentMessage(`Error: ${data.message}`)
            setIsUploading(false)
            onUploadError?.(data.message)
            break
        }
      },
      (error) => {
        console.error('❌ Folder upload error:', error)
        setCurrentMessage(`Folder upload failed: ${error.message}`)
        setIsUploading(false)
        onUploadError?.(error.message)
      },
      () => {
        console.log('✅ Folder upload complete!')
        setIsUploading(false)
        if (progress.total > 0) {
          onUploadComplete?.(progress.successful, progress.total)
        }
      }
    )
  }

  const stopUpload = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsUploading(false)
    setCurrentMessage('Upload cancelled')
  }

  const clearResults = () => {
    setProgress({ processed: 0, successful: 0, failed: 0, total: 0, percentage: 0 })
    setFileStatuses([])
    setCurrentMessage('')
    // Clear localStorage when clearing results
    localStorage.removeItem(`uploadType_${collectionId}`)
    setUploadType('files') // Reset to default
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Real-Time Document Upload
          </CardTitle>
          <div className="flex items-center gap-2">
            {!isUploading && progress.total > 0 && (
              <Button onClick={clearResults} variant="ghost" size="sm">
                Clear
              </Button>
            )}
            {onClose && (
              <Button
                onClick={() => {
                  // Clear localStorage when closing
                  localStorage.removeItem(`uploadType_${collectionId}`)
                  onClose()
                }}
                variant="ghost"
                size="sm"
              >
                <X className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          Upload individual files, folders directly, or ZIP files with real-time progress tracking.
          Supports: PDF, Word, TXT, Markdown, HTML, CSV
        </p>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Upload Type Selection */}
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={uploadType === 'files' ? 'default' : 'outline'}
            onClick={() => setUploadTypeWithLogging('files')}
            disabled={isUploading}
            size="sm"
          >
            <FileText className="h-4 w-4 mr-2" />
            Multiple Files
          </Button>
          <Button
            variant={uploadType === 'directory' ? 'default' : 'outline'}
            onClick={() => setUploadTypeWithLogging('directory')}
            disabled={isUploading}
            size="sm"
          >
            <Folder className="h-4 w-4 mr-2" />
            📁 Folder
          </Button>
          <Button
            variant={uploadType === 'folder' ? 'default' : 'outline'}
            onClick={() => setUploadTypeWithLogging('folder')}
            disabled={isUploading}
            size="sm"
          >
            <Folder className="h-4 w-4 mr-2" />
            ZIP File
          </Button>
        </div>

        {/* File/Folder Input */}
        <div className="space-y-4">
          {uploadType === 'files' ? (
            <div>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept=".txt,.md,.pdf,.docx,.doc,.html,.csv,.json,.rtf"
                onChange={(e) => {
                  console.log('📄 Regular file input onChange triggered')
                  console.log('📄 Current upload type:', uploadType)
                  console.log('📄 Files:', e.target.files)
                  if (e.target.files && uploadType === 'files') {
                    handleFileUpload(e.target.files)
                  } else if (uploadType !== 'files') {
                    console.warn('⚠️ Regular file input triggered but upload type is not files:', uploadType)
                  }
                }}
                disabled={isUploading}
                className="hidden"
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="w-full"
                size="lg"
              >
                <Upload className="h-4 w-4 mr-2" />
                {isUploading ? 'Uploading...' : 'Select Files to Upload'}
              </Button>
            </div>
          ) : uploadType === 'directory' ? (
            <div>
              <input
                ref={directoryInputRef}
                type="file"
                multiple
                webkitdirectory="true"
                onChange={(e) => {
                  console.log('📁 Directory input onChange triggered')
                  console.log('📂 Current upload type:', uploadType)
                  console.log('📂 Event target files:', e.target.files)
                  console.log('📂 Files length:', e.target.files?.length)

                  // Ensure we're still in directory mode
                  if (uploadType !== 'directory') {
                    console.warn('⚠️ Upload type changed during directory selection, resetting to directory')
                    setUploadTypeWithLogging('directory')
                  }

                  if (e.target.files && e.target.files.length > 0) {
                    handleDirectoryUpload(e.target.files)
                  } else {
                    console.warn('⚠️ No files in onChange event')
                  }

                  // Reset the input value to allow selecting the same folder again
                  e.target.value = ''
                }}
                disabled={isUploading}
                className="hidden"
                accept=""
              />
              <Button
                onClick={() => {
                  console.log('📁 Folder button clicked')
                  console.log('📂 Directory input ref:', directoryInputRef.current)

                  // Check if browser supports directory upload
                  const input = directoryInputRef.current
                  if (input && 'webkitdirectory' in input) {
                    console.log('✅ Browser supports webkitdirectory')
                    input.click()
                  } else {
                    console.error('❌ Browser does not support directory upload')
                    setCurrentMessage('Browser does not support folder upload. Please use ZIP file upload instead.')
                  }
                }}
                disabled={isUploading}
                className="w-full"
                size="lg"
              >
                <Folder className="h-4 w-4 mr-2" />
                {isUploading ? 'Processing...' : 'Select Folder to Upload'}
              </Button>
              <p className="text-xs text-muted-foreground mt-2">
                📁 Choose a folder and all files within it (including subfolders) will be uploaded
                <br />
                <span className="text-orange-600">Note: If folder selection doesn't work, try using ZIP file upload instead</span>
              </p>
            </div>
          ) : (
            <div>
              <input
                ref={folderInputRef}
                type="file"
                accept=".zip"
                onChange={(e) => e.target.files?.[0] && handleFolderUpload(e.target.files[0])}
                disabled={isUploading}
                className="hidden"
              />
              <Button
                onClick={() => folderInputRef.current?.click()}
                disabled={isUploading}
                className="w-full"
                size="lg"
              >
                <Folder className="h-4 w-4 mr-2" />
                {isUploading ? 'Processing...' : 'Select ZIP File to Upload'}
              </Button>
            </div>
          )}
        </div>

        {/* Progress Display */}
        {progress.total > 0 && !isCollapsed && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Upload Progress</span>
              <div className="flex gap-2">
                <Badge variant="outline">{progress.processed}/{progress.total} processed</Badge>
                <Badge variant="default">{progress.successful} success</Badge>
                {progress.failed > 0 && <Badge variant="destructive">{progress.failed} failed</Badge>}
              </div>
            </div>
            
            <Progress value={progress.percentage} className="w-full" />
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">{progress.percentage}% complete</span>
              <div className="flex gap-2">
                {isUploading && (
                  <Button onClick={stopUpload} variant="outline" size="sm">
                    <Square className="h-4 w-4 mr-2" />
                    Stop Upload
                  </Button>
                )}
                <Button 
                  onClick={() => setIsCollapsed(!isCollapsed)} 
                  variant="ghost" 
                  size="sm"
                >
                  {isCollapsed ? 'Show Details' : 'Hide Details'}
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Collapsed Progress Summary */}
        {progress.total > 0 && isCollapsed && (
          <div className="p-3 bg-muted rounded-lg flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-sm font-medium">
                {progress.processed}/{progress.total} files processed
              </span>
              <div className="flex gap-2">
                <Badge variant="default" size="sm">{progress.successful} success</Badge>
                {progress.failed > 0 && <Badge variant="destructive" size="sm">{progress.failed} failed</Badge>}
              </div>
            </div>
            <Button 
              onClick={() => setIsCollapsed(false)} 
              variant="ghost" 
              size="sm"
            >
              Show Details
            </Button>
          </div>
        )}

        {/* Current Status */}
        {currentMessage && !isCollapsed && (
          <div className="p-3 bg-muted rounded-lg">
            <p className="text-sm">{currentMessage}</p>
          </div>
        )}

        {/* File Status List */}
        {fileStatuses.length > 0 && !isCollapsed && (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">File Status ({fileStatuses.length} files):</h4>
              {fileStatuses.length > 5 && (
                <span className="text-xs text-muted-foreground">
                  Scroll to see all files
                </span>
              )}
            </div>
            {fileStatuses.map((file, index) => (
              <div key={index} className="flex items-center justify-between p-2 border rounded text-sm">
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  {file.status === 'success' && <CheckCircle className="h-4 w-4 text-green-500 flex-shrink-0" />}
                  {file.status === 'failed' && <AlertCircle className="h-4 w-4 text-red-500 flex-shrink-0" />}
                  {file.status === 'processing' && (
                    <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin flex-shrink-0" />
                  )}
                  <span className="truncate" title={file.filename}>{file.filename}</span>
                  {file.error && (
                    <span className="text-xs text-red-500 truncate" title={file.error}>
                      - {file.error}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                  <Badge 
                    variant={
                      file.status === 'success' ? 'default' :
                      file.status === 'failed' ? 'destructive' :
                      file.status === 'processing' ? 'secondary' : 'outline'
                    }
                    className="text-xs"
                  >
                    {file.status}
                  </Badge>
                  {file.chunks_created && (
                    <span className="text-xs text-muted-foreground">
                      {file.chunks_created} chunks
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Success Summary */}
        {!isUploading && progress.total > 0 && progress.processed === progress.total && (
          <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 text-green-800">
              <CheckCircle className="h-5 w-5" />
              <span className="font-medium">
                Upload Complete! {progress.successful}/{progress.total} files processed successfully.
              </span>
            </div>
            {progress.failed > 0 && (
              <p className="text-sm text-green-700 mt-1">
                {progress.failed} files failed to process. Check the file list above for details.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}