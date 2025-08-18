import React, { useState, useRef, useCallback } from 'react'
import { FolderOpen, Upload, FileText, AlertCircle, CheckCircle, X, Pause, Play } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { folderUploadApi } from '@/lib/api'

interface FolderUploadProps {
  collectionId: number
  onUploadComplete: (results: any) => void
  onUploadError: (error: string) => void
}

interface UploadJob {
  job_id: string
  status: string
  progress: {
    total_files: number
    processed_files: number
    successful_files: number
    failed_files: number
    percentage: number
  }
  timestamps: {
    started_at: string | null
    completed_at: string | null
    duration_seconds: number | null
  }
  metadata: {
    upload_path: string | null
    folder_structure: any
    preserve_structure: boolean
    skip_unsupported: boolean
  }
  errors: any[]
}

export function FolderUpload({ collectionId, onUploadComplete, onUploadError }: FolderUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [currentJob, setCurrentJob] = useState<UploadJob | null>(null)
  const [uploadSettings, setUploadSettings] = useState({
    preserveStructure: true,
    skipUnsupported: true,
    maxFileSizeMb: 10
  })
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const zipInputRef = useRef<HTMLInputElement>(null)
  const statusCheckInterval = useRef<NodeJS.Timeout | null>(null)

  const startStatusPolling = useCallback((jobId: string) => {
    statusCheckInterval.current = setInterval(async () => {
      try {
        const status = await folderUploadApi.getJobStatus(collectionId, jobId)
        setCurrentJob(status)
        
        if (status.status === 'completed' || status.status === 'failed' || status.status === 'cancelled') {
          if (statusCheckInterval.current) {
            clearInterval(statusCheckInterval.current)
            statusCheckInterval.current = null
          }
          
          if (status.status === 'completed') {
            onUploadComplete(status)
          } else if (status.status === 'failed') {
            onUploadError(`Upload failed: ${status.errors?.[0] || 'Unknown error'}`)
          }
        }
      } catch (error) {
        console.error('Failed to check job status:', error)
        if (statusCheckInterval.current) {
          clearInterval(statusCheckInterval.current)
          statusCheckInterval.current = null
        }
      }
    }, 2000) // Check every 2 seconds
  }, [collectionId, onUploadComplete, onUploadError])

  const handleFolderUpload = async (files: FileList) => {
    if (files.length === 0) return

    try {
      // Create FormData with multiple files
      const formData = new FormData()
      Array.from(files).forEach(file => {
        formData.append('files', file)
      })
      
      formData.append('preserve_structure', uploadSettings.preserveStructure.toString())
      formData.append('skip_unsupported', uploadSettings.skipUnsupported.toString())
      formData.append('max_file_size_mb', uploadSettings.maxFileSizeMb.toString())

      const result = await folderUploadApi.uploadMultipleFiles(collectionId, formData)
      
      setCurrentJob({
        job_id: result.job_id,
        status: 'processing',
        progress: {
          total_files: 0,
          processed_files: 0,
          successful_files: 0,
          failed_files: 0,
          percentage: 0
        },
        timestamps: {
          started_at: new Date().toISOString(),
          completed_at: null,
          duration_seconds: null
        },
        metadata: {
          upload_path: null,
          folder_structure: null,
          preserve_structure: uploadSettings.preserveStructure,
          skip_unsupported: uploadSettings.skipUnsupported
        },
        errors: []
      })

      startStatusPolling(result.job_id)
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      onUploadError(errorMessage)
    }
  }

  const handleZipUpload = async (file: File) => {
    try {
      const formData = new FormData()
      formData.append('zip_file', file)
      formData.append('preserve_structure', uploadSettings.preserveStructure.toString())
      formData.append('skip_unsupported', uploadSettings.skipUnsupported.toString())
      formData.append('max_file_size_mb', uploadSettings.maxFileSizeMb.toString())

      const result = await folderUploadApi.uploadZipFolder(collectionId, formData)
      
      setCurrentJob({
        job_id: result.job_id,
        status: 'processing',
        progress: {
          total_files: 0,
          processed_files: 0,
          successful_files: 0,
          failed_files: 0,
          percentage: 0
        },
        timestamps: {
          started_at: new Date().toISOString(),
          completed_at: null,
          duration_seconds: null
        },
        metadata: {
          upload_path: file.name,
          folder_structure: null,
          preserve_structure: uploadSettings.preserveStructure,
          skip_unsupported: uploadSettings.skipUnsupported
        },
        errors: []
      })

      startStatusPolling(result.job_id)
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'ZIP upload failed'
      onUploadError(errorMessage)
    }
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const items = Array.from(e.dataTransfer.items)
    const files: File[] = []
    
    // Handle dropped files/folders
    for (const item of items) {
      if (item.kind === 'file') {
        const entry = item.webkitGetAsEntry()
        if (entry) {
          if (entry.isDirectory) {
            // Handle directory drop
            await traverseDirectory(entry as FileSystemDirectoryEntry, files)
          } else {
            // Handle single file
            const file = item.getAsFile()
            if (file) files.push(file)
          }
        }
      }
    }
    
    if (files.length > 0) {
      const fileList = new DataTransfer()
      files.forEach(file => fileList.items.add(file))
      await handleFolderUpload(fileList.files)
    }
  }

  const traverseDirectory = async (entry: FileSystemDirectoryEntry, files: File[]) => {
    const reader = entry.createReader()
    
    return new Promise<void>((resolve) => {
      const readEntries = () => {
        reader.readEntries(async (entries) => {
          if (entries.length === 0) {
            resolve()
            return
          }
          
          for (const entry of entries) {
            if (entry.isFile) {
              const file = await new Promise<File>((fileResolve) => {
                (entry as FileSystemFileEntry).file(fileResolve)
              })
              files.push(file)
            } else if (entry.isDirectory) {
              await traverseDirectory(entry as FileSystemDirectoryEntry, files)
            }
          }
          
          readEntries() // Continue reading
        })
      }
      
      readEntries()
    })
  }

  const cancelJob = async () => {
    if (currentJob) {
      try {
        await folderUploadApi.cancelJob(collectionId, currentJob.job_id)
        if (statusCheckInterval.current) {
          clearInterval(statusCheckInterval.current)
          statusCheckInterval.current = null
        }
        setCurrentJob(null)
      } catch (error) {
        console.error('Failed to cancel job:', error)
      }
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500'
      case 'failed': return 'bg-red-500'
      case 'cancelled': return 'bg-gray-500'
      case 'processing': return 'bg-blue-500'
      default: return 'bg-yellow-500'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4" />
      case 'failed': return <AlertCircle className="h-4 w-4" />
      case 'processing': return <Upload className="h-4 w-4 animate-spin" />
      default: return <Upload className="h-4 w-4" />
    }
  }

  return (
    <div className="space-y-6">
      {/* Upload Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderOpen className="h-5 w-5" />
            Folder Upload Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center space-x-2">
            <Checkbox
              id="preserve-structure"
              checked={uploadSettings.preserveStructure}
              onCheckedChange={(checked) => 
                setUploadSettings(prev => ({ ...prev, preserveStructure: !!checked }))
              }
            />
            <Label htmlFor="preserve-structure">Preserve folder structure</Label>
          </div>
          
          <div className="flex items-center space-x-2">
            <Checkbox
              id="skip-unsupported"
              checked={uploadSettings.skipUnsupported}
              onCheckedChange={(checked) => 
                setUploadSettings(prev => ({ ...prev, skipUnsupported: !!checked }))
              }
            />
            <Label htmlFor="skip-unsupported">Skip unsupported file types</Label>
          </div>
          
          <div className="flex items-center space-x-2">
            <Label htmlFor="max-size">Max file size (MB):</Label>
            <input
              id="max-size"
              type="number"
              min="1"
              max="100"
              value={uploadSettings.maxFileSizeMb}
              onChange={(e) => 
                setUploadSettings(prev => ({ ...prev, maxFileSizeMb: parseInt(e.target.value) || 10 }))
              }
              className="w-20 px-2 py-1 border rounded"
            />
          </div>
        </CardContent>
      </Card>

      {/* Upload Area */}
      <Card 
        className={`border-2 border-dashed transition-colors cursor-pointer ${
          isDragOver 
            ? 'border-primary bg-primary/5' 
            : 'border-muted-foreground/25 hover:border-primary/50'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <CardContent className="flex flex-col items-center justify-center py-12">
          <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
          <div className="text-center mb-6">
            <p className="text-lg font-medium mb-2">
              Drop folders here or select upload method
            </p>
            <p className="text-sm text-muted-foreground">
              Supports all document formats: PDF, DOCX, MD, HTML, CSV, JSON, RTF, TXT
            </p>
          </div>
          
          <div className="flex gap-4">
            <Button 
              onClick={() => folderInputRef.current?.click()}
              disabled={!!currentJob}
            >
              <FolderOpen className="h-4 w-4 mr-2" />
              Select Folder
            </Button>
            
            <Button 
              variant="outline"
              onClick={() => zipInputRef.current?.click()}
              disabled={!!currentJob}
            >
              <Upload className="h-4 w-4 mr-2" />
              Upload ZIP
            </Button>
            
            <Button 
              variant="outline"
              onClick={() => fileInputRef.current?.click()}
              disabled={!!currentJob}
            >
              <FileText className="h-4 w-4 mr-2" />
              Multiple Files
            </Button>
          </div>
          
          {/* Hidden inputs */}
          <input
            ref={folderInputRef}
            type="file"
            webkitdirectory=""
            multiple
            onChange={(e) => e.target.files && handleFolderUpload(e.target.files)}
            className="hidden"
          />
          
          <input
            ref={zipInputRef}
            type="file"
            accept=".zip"
            onChange={(e) => e.target.files?.[0] && handleZipUpload(e.target.files[0])}
            className="hidden"
          />
          
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.txt,.doc,.docx,.md,.markdown,.html,.htm,.rtf,.csv,.json"
            onChange={(e) => e.target.files && handleFolderUpload(e.target.files)}
            className="hidden"
          />
        </CardContent>
      </Card>

      {/* Upload Progress */}
      {currentJob && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                {getStatusIcon(currentJob.status)}
                Upload Progress
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge className={getStatusColor(currentJob.status)}>
                  {currentJob.status.toUpperCase()}
                </Badge>
                {currentJob.status === 'processing' && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={cancelJob}
                  >
                    <X className="h-4 w-4" />
                    Cancel
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>Progress</span>
                <span>{currentJob.progress.processed_files} / {currentJob.progress.total_files} files</span>
              </div>
              <Progress value={currentJob.progress.percentage} className="w-full" />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>{currentJob.progress.percentage.toFixed(1)}% complete</span>
                <span>
                  ✅ {currentJob.progress.successful_files} success, 
                  ❌ {currentJob.progress.failed_files} failed
                </span>
              </div>
            </div>
            
            {currentJob.metadata.upload_path && (
              <div className="text-sm">
                <strong>Source:</strong> {currentJob.metadata.upload_path}
              </div>
            )}
            
            {currentJob.timestamps.duration_seconds && (
              <div className="text-sm">
                <strong>Duration:</strong> {currentJob.timestamps.duration_seconds.toFixed(1)}s
              </div>
            )}
            
            {currentJob.errors.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-red-600">Errors:</h4>
                <div className="max-h-32 overflow-y-auto space-y-1">
                  {currentJob.errors.slice(0, 5).map((error, index) => (
                    <div key={index} className="text-xs text-red-600 bg-red-50 p-2 rounded">
                      {typeof error === 'string' ? error : JSON.stringify(error)}
                    </div>
                  ))}
                  {currentJob.errors.length > 5 && (
                    <div className="text-xs text-muted-foreground">
                      ... and {currentJob.errors.length - 5} more errors
                    </div>
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}