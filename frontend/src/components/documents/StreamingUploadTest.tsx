import React, { useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Upload, Play, Square, CheckCircle, AlertCircle, FileText, Folder } from 'lucide-react'
import { folderUploadApi } from '@/lib/api'

interface StreamingUploadTestProps {
  collectionId: number
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

export function StreamingUploadTest({ collectionId }: StreamingUploadTestProps) {
  const [isUploading, setIsUploading] = useState(false)
  const [progress, setProgress] = useState<UploadProgress>({ processed: 0, successful: 0, failed: 0, total: 0, percentage: 0 })
  const [fileStatuses, setFileStatuses] = useState<FileStatus[]>([])
  const [currentMessage, setCurrentMessage] = useState<string>('')
  const [uploadType, setUploadType] = useState<'files' | 'folder'>('files')
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const handleFileUpload = (files: FileList) => {
    if (isUploading) return
    
    setIsUploading(true)
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
            break
            
          case 'error':
            setCurrentMessage(`Error: ${data.message}`)
            setIsUploading(false)
            break
        }
      },
      (error) => {
        console.error('❌ Upload error:', error)
        setCurrentMessage(`Upload failed: ${error.message}`)
        setIsUploading(false)
      },
      () => {
        console.log('✅ Upload complete!')
        setIsUploading(false)
      }
    )
  }

  const handleFolderUpload = (file: File) => {
    if (isUploading) return
    
    setIsUploading(true)
    setProgress({ processed: 0, successful: 0, failed: 0, total: 0, percentage: 0 })
    setFileStatuses([])
    setCurrentMessage('Starting folder upload...')
    
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
            break
            
          case 'error':
            setCurrentMessage(`Error: ${data.message}`)
            setIsUploading(false)
            break
        }
      },
      (error) => {
        console.error('❌ Folder upload error:', error)
        setCurrentMessage(`Folder upload failed: ${error.message}`)
        setIsUploading(false)
      },
      () => {
        console.log('✅ Folder upload complete!')
        setIsUploading(false)
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

  return (
    <Card className="w-full max-w-4xl">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          🚀 Real-Time Streaming Upload Test
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-6">
        {/* Upload Type Selection */}
        <div className="flex gap-2">
          <Button
            variant={uploadType === 'files' ? 'default' : 'outline'}
            onClick={() => setUploadType('files')}
            disabled={isUploading}
          >
            <FileText className="h-4 w-4 mr-2" />
            Upload Files
          </Button>
          <Button
            variant={uploadType === 'folder' ? 'default' : 'outline'}
            onClick={() => setUploadType('folder')}
            disabled={isUploading}
          >
            <Folder className="h-4 w-4 mr-2" />
            Upload Folder (ZIP)
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
                accept=".txt,.md,.pdf,.docx,.doc,.html,.csv"
                onChange={(e) => e.target.files && handleFileUpload(e.target.files)}
                disabled={isUploading}
                className="hidden"
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                className="w-full"
              >
                <Upload className="h-4 w-4 mr-2" />
                Select Files to Upload
              </Button>
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
              >
                <Folder className="h-4 w-4 mr-2" />
                Select ZIP File to Upload
              </Button>
            </div>
          )}
        </div>

        {/* Progress Display */}
        {progress.total > 0 && (
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">Upload Progress</span>
              <div className="flex gap-2">
                <Badge variant="outline">{progress.processed}/{progress.total} processed</Badge>
                <Badge variant="default">{progress.successful} success</Badge>
                <Badge variant="destructive">{progress.failed} failed</Badge>
              </div>
            </div>
            
            <Progress value={progress.percentage} className="w-full" />
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-muted-foreground">{progress.percentage}% complete</span>
              {isUploading && (
                <Button onClick={stopUpload} variant="outline" size="sm">
                  <Square className="h-4 w-4 mr-2" />
                  Stop Upload
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Current Status */}
        {currentMessage && (
          <div className="p-3 bg-muted rounded-lg">
            <p className="text-sm">{currentMessage}</p>
          </div>
        )}

        {/* File Status List */}
        {fileStatuses.length > 0 && (
          <div className="space-y-2 max-h-60 overflow-y-auto">
            <h4 className="text-sm font-medium">File Status:</h4>
            {fileStatuses.map((file, index) => (
              <div key={index} className="flex items-center justify-between p-2 border rounded">
                <div className="flex items-center gap-2">
                  {file.status === 'success' && <CheckCircle className="h-4 w-4 text-green-500" />}
                  {file.status === 'failed' && <AlertCircle className="h-4 w-4 text-red-500" />}
                  {file.status === 'processing' && <div className="h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />}
                  <span className="text-sm">{file.filename}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={
                    file.status === 'success' ? 'default' :
                    file.status === 'failed' ? 'destructive' :
                    file.status === 'processing' ? 'secondary' : 'outline'
                  }>
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
      </CardContent>
    </Card>
  )
}