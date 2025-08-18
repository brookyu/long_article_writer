import React, { useState, useCallback, useRef } from 'react'
import { 
  Play, 
  Pause, 
  Square, 
  RotateCcw, 
  Trash2, 
  CheckCircle,
  AlertCircle,
  Clock,
  Upload,
  Settings,
  FolderOpen
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { FilePreview } from './FilePreview'
import { folderUploadApi } from '@/lib/api'

interface QueueItem {
  id: string
  jobId?: string
  files: Array<{
    file: File
    status: 'pending' | 'processing' | 'completed' | 'failed'
    progress: number
    error?: string
    relativePath?: string
  }>
  settings: {
    preserveStructure: boolean
    skipUnsupported: boolean
    maxFileSizeMb: number
    batchSize: number
  }
  status: 'queued' | 'processing' | 'paused' | 'completed' | 'failed' | 'cancelled'
  progress: {
    totalFiles: number
    processedFiles: number
    successfulFiles: number
    failedFiles: number
    percentage: number
  }
  timestamps: {
    queued: Date
    started?: Date
    completed?: Date
  }
  errors: string[]
}

interface UploadQueueProps {
  collectionId: number
  onUploadComplete: (results: any) => void
  onUploadError: (error: string) => void
}

export const UploadQueue = React.forwardRef<
  {
    addToQueue: (files: File[], settings: any, relativePaths?: string[]) => string
    resumeProcessing: () => void
    pauseProcessing: () => void
  },
  UploadQueueProps
>(({ collectionId, onUploadComplete, onUploadError }, ref) => {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  
  const queueRef = useRef<QueueItem[]>([])
  const processingRef = useRef<boolean>(false)

  // Keep refs in sync
  React.useEffect(() => {
    queueRef.current = queue
    processingRef.current = isProcessing
  }, [queue, isProcessing])

  // Load existing backend jobs on mount
  React.useEffect(() => {
    const loadExistingJobs = async () => {
      try {
        const response = await folderUploadApi.listJobs(collectionId)
        const activeJobs = response.jobs.filter(job => 
          ['pending', 'processing'].includes(job.status) && 
          job.file_list && 
          job.file_list.length > 0 &&
          // Filter out stuck jobs that have 100% processed but 0% successful
          !(job.progress.processed_files === job.progress.total_files && job.progress.successful_files === 0)
        )
        
        // Convert backend jobs to queue items
        const queueItems = activeJobs.map(job => ({
          id: `backend_${job.job_id}`,
          jobId: job.job_id,
          files: job.file_list.map((filePath: string, index: number) => {
            // Calculate individual file progress based on job progress
            const totalFiles = job.progress.total_files
            const processedFiles = job.progress.processed_files
            const successfulFiles = job.progress.successful_files || 0
            
            // Determine individual file status and progress
            let fileStatus, fileProgress
            if (job.status === 'completed') {
              // For completed jobs, files are either successful or failed
              fileStatus = index < successfulFiles ? 'completed' : 'failed'
              fileProgress = index < successfulFiles ? 100 : 0
            } else if (job.status === 'failed') {
              fileStatus = 'failed'
              fileProgress = 0
            } else {
              // For processing jobs, show gradual progress
              if (index < processedFiles) {
                fileStatus = index < successfulFiles ? 'completed' : 'failed'
                fileProgress = index < successfulFiles ? 100 : 0
              } else {
                fileStatus = 'processing'
                fileProgress = 0
              }
            }
            
            return {
              file: new File([], filePath.split('/').pop() || 'unknown'),
              status: fileStatus,
              progress: fileProgress,
              relativePath: filePath
            }
          }),
          settings: {
            preserveStructure: job.preserve_structure,
            skipUnsupported: job.skip_unsupported,
            maxFileSizeMb: job.max_file_size_mb,
            batchSize: 10
          },
          status: job.status === 'completed' ? 'completed' : 
                  job.status === 'failed' ? 'failed' : 'processing',
          progress: {
            totalFiles: job.progress.total_files,
            processedFiles: job.progress.processed_files,
            successfulFiles: job.progress.successful_files || 0,
            failedFiles: job.progress.failed_files || 0,
            percentage: job.progress.percentage || 0
          },
          timestamps: {
            queued: new Date(job.created_at),
            started: job.started_at ? new Date(job.started_at) : undefined,
            completed: job.completed_at ? new Date(job.completed_at) : undefined
          },
          errors: job.error_log ? [job.error_log] : []
        }))
        
        // Add backend jobs to queue (but don't duplicate existing ones)
        setQueue(prev => {
          const existingJobIds = new Set(prev.map(item => item.jobId).filter(Boolean))
          const newJobs = queueItems.filter(item => item.jobId && !existingJobIds.has(item.jobId))
          return [...prev, ...newJobs]
        })
        
        // Start polling for active jobs
        activeJobs.forEach(job => {
          if (['pending', 'processing'].includes(job.status)) {
            pollJobStatus(`backend_${job.job_id}`, job.job_id)
          }
        })
        
      } catch (error) {
        console.error('Failed to load existing jobs:', error)
      }
    }
    
    loadExistingJobs()
  }, [collectionId])

  const generateId = () => Math.random().toString(36).substr(2, 9)

  const addToQueue = useCallback((
    files: File[], 
    settings: QueueItem['settings'],
    relativePaths?: string[]
  ) => {
    console.log('🔵 addToQueue called:', { fileCount: files.length, settings });
    const queueItem: QueueItem = {
      id: generateId(),
      files: files.map((file, index) => ({
        file,
        status: 'pending',
        progress: 0,
        relativePath: relativePaths?.[index]
      })),
      settings,
      status: 'queued',
      progress: {
        totalFiles: files.length,
        processedFiles: 0,
        successfulFiles: 0,
        failedFiles: 0,
        percentage: 0
      },
      timestamps: {
        queued: new Date()
      },
      errors: []
    }

    setQueue(prev => [...prev, queueItem])
    return queueItem.id
  }, [])

  const removeFromQueue = useCallback((itemId: string) => {
    setQueue(prev => prev.filter(item => item.id !== itemId))
  }, [])

  const clearCompleted = useCallback(() => {
    setQueue(prev => prev.filter(item => 
      !['completed', 'failed', 'cancelled'].includes(item.status)
    ))
  }, [])

  const clearAll = useCallback(() => {
    setQueue([])
    setIsProcessing(false)
    setCurrentJobId(null)
  }, [])

  const retryItem = useCallback((itemId: string) => {
    setQueue(prev => prev.map(item => {
      if (item.id === itemId) {
        return {
          ...item,
          status: 'queued' as const,
          files: item.files.map(f => ({
            ...f,
            status: f.status === 'failed' ? 'pending' as const : f.status,
            error: f.status === 'failed' ? undefined : f.error
          })),
          errors: []
        }
      }
      return item
    }))
  }, [])

  const processQueue = useCallback(async () => {
    if (processingRef.current) return

    setIsProcessing(true)

    while (queueRef.current.length > 0) {
      const nextItem = queueRef.current.find(item => item.status === 'queued')
      if (!nextItem) break

      try {
        // Update item status to processing
        setQueue(prev => prev.map(item => 
          item.id === nextItem.id 
            ? { ...item, status: 'processing', timestamps: { ...item.timestamps, started: new Date() } }
            : item
        ))

        // Simulate file processing (replace with actual upload logic)
        await processQueueItem(nextItem)

      } catch (error) {
        console.error('Queue processing error:', error)
        setQueue(prev => prev.map(item => 
          item.id === nextItem.id 
            ? { 
                ...item, 
                status: 'failed',
                timestamps: { ...item.timestamps, completed: new Date() },
                errors: [...item.errors, error instanceof Error ? error.message : 'Unknown error']
              }
            : item
        ))
      }

      if (!processingRef.current) break // Check if paused
    }

    setIsProcessing(false)
    setCurrentJobId(null)
  }, [])

  const pauseProcessing = useCallback(() => {
    setIsProcessing(false)
    // Cancel current job if any
    if (currentJobId) {
      // TODO: Implement job cancellation API call
    }
  }, [currentJobId])

  const resumeProcessing = useCallback(() => {
    setIsProcessing(true)
    processQueue()
  }, [processQueue])

  // Expose methods via ref
  React.useImperativeHandle(ref, () => ({
    addToQueue,
    resumeProcessing,
    pauseProcessing
  }), [addToQueue, resumeProcessing, pauseProcessing])

  const processQueueItem = async (item: QueueItem) => {
    // Real backend integration with streaming progress
    try {
      // Create FormData with files
      const formData = new FormData()
      item.files.forEach(fileInfo => {
        formData.append('files', fileInfo.file)
      })
      
      formData.append('preserve_structure', item.settings.preserveStructure.toString())
      formData.append('skip_unsupported', item.settings.skipUnsupported.toString())
      formData.append('max_file_size_mb', item.settings.maxFileSizeMb.toString())

      // Start upload job
      const uploadResult = await folderUploadApi.uploadMultipleFiles(collectionId, formData)
      const jobId = uploadResult.job_id

      // Update queue item with job ID
      setQueue(prev => prev.map(qItem => 
        qItem.id === item.id 
          ? { ...qItem, jobId, status: 'processing' }
          : qItem
      ))

      // Set up Server-Sent Events for real-time progress
      const eventSource = folderUploadApi.streamJobProgress(collectionId, jobId)
      
      eventSource.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          switch (data.type) {
            case 'job_status':
            case 'progress_update':
              updateQueueItemFromJobData(item.id, data.data)
              break
              
            case 'job_complete':
              updateQueueItemFromJobData(item.id, data.data)
              eventSource.close()
              break
              
            case 'error':
              setQueue(prev => prev.map(qItem => 
                qItem.id === item.id 
                  ? { 
                      ...qItem, 
                      status: 'failed',
                      errors: [...qItem.errors, data.message]
                    }
                  : qItem
              ))
              eventSource.close()
              break
          }
        } catch (error) {
          console.error('Error parsing SSE data:', error)
        }
      }

      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error)
        eventSource.close()
        
        // Fallback to polling
        pollJobStatus(item.id, jobId)
      }

      // Store event source for cleanup
      item.jobId = jobId
      
    } catch (error) {
      // Handle upload start error
      setQueue(prev => prev.map(qItem => 
        qItem.id === item.id 
          ? { 
              ...qItem, 
              status: 'failed',
              errors: [...qItem.errors, `Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`]
            }
          : qItem
      ))
    }
  }

  const updateQueueItemFromJobData = (itemId: string, jobData: any) => {
    setQueue(prev => prev.map(qItem => {
      if (qItem.id !== itemId) return qItem

      const progress = jobData.progress || {}
      const timestamps = jobData.timestamps || {}
      
      // Update individual file progress based on job progress
      const updatedFiles = qItem.files.map((fileInfo, index) => {
        const processedFiles = progress.processed_files || 0
        const successfulFiles = progress.successful_files || 0
        
        let fileStatus, fileProgress
        if (jobData.status === 'completed') {
          fileStatus = index < successfulFiles ? 'completed' : 'failed'
          fileProgress = index < successfulFiles ? 100 : 0
        } else if (jobData.status === 'failed') {
          fileStatus = 'failed'
          fileProgress = 0
        } else {
          // For processing jobs
          if (index < processedFiles) {
            fileStatus = index < successfulFiles ? 'completed' : 'failed'
            fileProgress = index < successfulFiles ? 100 : 0
          } else {
            fileStatus = 'processing'
            fileProgress = 0
          }
        }
        
        return {
          ...fileInfo,
          status: fileStatus,
          progress: fileProgress
        }
      })
      
      return {
        ...qItem,
        files: updatedFiles,
        status: jobData.status === 'completed' ? 'completed' : 
                jobData.status === 'failed' ? 'failed' : 'processing',
        progress: {
          ...qItem.progress,
          processedFiles: progress.processed_files || 0,
          successfulFiles: progress.successful_files || 0,
          failedFiles: progress.failed_files || 0,
          percentage: progress.percentage || 0
        },
        timestamps: {
          ...qItem.timestamps,
          started: timestamps.started_at ? new Date(timestamps.started_at) : qItem.timestamps.started,
          completed: timestamps.completed_at ? new Date(timestamps.completed_at) : undefined
        },
        errors: jobData.errors || qItem.errors
      }
    }))
  }

  const pollJobStatus = async (itemId: string, jobId: string) => {
    // Fallback polling if SSE fails
    const pollInterval = setInterval(async () => {
      try {
        const jobStatus = await folderUploadApi.getJobStatus(collectionId, jobId)
        updateQueueItemFromJobData(itemId, jobStatus)
        
        if (['completed', 'failed', 'cancelled'].includes(jobStatus.status)) {
          clearInterval(pollInterval)
        }
      } catch (error) {
        console.error('Polling error:', error)
        clearInterval(pollInterval)
      }
    }, 2000) // Poll every 2 seconds
  }

  const getQueueStats = () => {
    const total = queue.length
    const queued = queue.filter(item => item.status === 'queued').length
    const processing = queue.filter(item => item.status === 'processing').length
    const completed = queue.filter(item => item.status === 'completed').length
    const failed = queue.filter(item => item.status === 'failed').length
    
    const totalFiles = queue.reduce((sum, item) => sum + item.files.length, 0)
    const completedFiles = queue.reduce((sum, item) => sum + item.progress.successfulFiles, 0)
    
    return { total, queued, processing, completed, failed, totalFiles, completedFiles }
  }

  const stats = getQueueStats()

  return (
    <div className="space-y-6">
      {/* Queue Controls */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Upload Queue
            </CardTitle>
            <div className="flex gap-2">
              {!isProcessing ? (
                <Button
                  onClick={resumeProcessing}
                  disabled={stats.queued === 0}
                  size="sm"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Start
                </Button>
              ) : (
                <Button
                  onClick={pauseProcessing}
                  variant="outline"
                  size="sm"
                >
                  <Pause className="h-4 w-4 mr-2" />
                  Pause
                </Button>
              )}
              
              <Button
                onClick={clearCompleted}
                variant="outline"
                size="sm"
                disabled={stats.completed === 0 && stats.failed === 0}
              >
                <CheckCircle className="h-4 w-4 mr-2" />
                Clear Completed
              </Button>
              
              <Button
                onClick={clearAll}
                variant="outline"
                size="sm"
                disabled={queue.length === 0}
              >
                <Trash2 className="h-4 w-4 mr-2" />
                Clear All
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Queue Statistics */}
          <div className="grid grid-cols-2 md:grid-cols-6 gap-4 text-sm mb-4">
            <div className="text-center">
              <div className="text-lg font-bold">{stats.total}</div>
              <div className="text-muted-foreground">Total Jobs</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-blue-600">{stats.queued}</div>
              <div className="text-muted-foreground">Queued</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-yellow-600">{stats.processing}</div>
              <div className="text-muted-foreground">Processing</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-green-600">{stats.completed}</div>
              <div className="text-muted-foreground">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-red-600">{stats.failed}</div>
              <div className="text-muted-foreground">Failed</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold">{stats.completedFiles}/{stats.totalFiles}</div>
              <div className="text-muted-foreground">Files Done</div>
            </div>
          </div>

          {/* Overall Progress */}
          {stats.totalFiles > 0 && (
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Overall Progress</span>
                <span>{Math.round((stats.completedFiles / stats.totalFiles) * 100)}%</span>
              </div>
              <Progress value={(stats.completedFiles / stats.totalFiles) * 100} className="h-2" />
            </div>
          )}

          {/* Processing Status */}
          {isProcessing && (
            <div className="mt-4 flex items-center gap-2 text-sm text-blue-600">
              <Clock className="h-4 w-4 animate-pulse" />
              Processing queue...
            </div>
          )}
        </CardContent>
      </Card>

      {/* Queue Items */}
      {queue.length === 0 ? (
        <Card>
          <CardContent className="text-center py-8 text-muted-foreground">
            <FolderOpen className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p>Upload queue is empty</p>
            <p className="text-sm">Add files to start batch processing</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {queue.map((item, index) => (
            <Card key={item.id} className="overflow-hidden">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    {item.status === 'processing' && <Clock className="h-5 w-5 text-blue-500 animate-pulse" />}
                    {item.status === 'completed' && <CheckCircle className="h-5 w-5 text-green-500" />}
                    {item.status === 'failed' && <AlertCircle className="h-5 w-5 text-red-500" />}
                    {item.status === 'queued' && <Clock className="h-5 w-5 text-gray-400" />}
                    
                    Job #{index + 1}
                    <Badge variant={
                      item.status === 'completed' ? 'default' :
                      item.status === 'failed' ? 'destructive' :
                      item.status === 'processing' ? 'secondary' : 'outline'
                    }>
                      {item.status}
                    </Badge>
                  </CardTitle>
                  
                  <div className="flex gap-2">
                    {item.status === 'failed' && (
                      <Button
                        onClick={() => retryItem(item.id)}
                        variant="outline"
                        size="sm"
                      >
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Retry
                      </Button>
                    )}
                    
                    {['completed', 'failed', 'cancelled'].includes(item.status) && (
                      <Button
                        onClick={() => removeFromQueue(item.id)}
                        variant="outline"
                        size="sm"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    )}
                  </div>
                </div>
                
                {/* Job Progress */}
                {item.status === 'processing' && (
                  <div className="mt-2">
                    <div className="flex justify-between text-sm mb-1">
                      <span>Progress</span>
                      <span>{item.progress.processedFiles} / {item.progress.totalFiles} files</span>
                    </div>
                    <Progress value={item.progress.percentage} className="h-2" />
                  </div>
                )}
              </CardHeader>
              
              <CardContent>
                {/* File Preview */}
                <FilePreview
                  files={item.files.map(f => ({
                    ...f,
                    relativePath: f.relativePath
                  }))}
                  showPreviews={false} // Disable previews in queue for performance
                />

                {/* Job Settings */}
                <Separator className="my-4" />
                <div className="text-sm text-muted-foreground">
                  <div className="flex items-center gap-4">
                    <span>Settings:</span>
                    <span>Structure: {item.settings.preserveStructure ? 'Preserved' : 'Flat'}</span>
                    <span>Skip unsupported: {item.settings.skipUnsupported ? 'Yes' : 'No'}</span>
                    <span>Max size: {item.settings.maxFileSizeMb}MB</span>
                  </div>
                </div>

                {/* Timestamps */}
                <div className="mt-2 text-xs text-muted-foreground">
                  <span>Queued: {item.timestamps.queued.toLocaleTimeString()}</span>
                  {item.timestamps.started && (
                    <span className="ml-4">Started: {item.timestamps.started.toLocaleTimeString()}</span>
                  )}
                  {item.timestamps.completed && (
                    <span className="ml-4">Completed: {item.timestamps.completed.toLocaleTimeString()}</span>
                  )}
                </div>

                {/* Errors */}
                {item.errors.length > 0 && (
                  <div className="mt-4 space-y-1">
                    <div className="text-sm font-medium text-red-600">Errors:</div>
                    {item.errors.slice(0, 3).map((error, errorIndex) => (
                      <div key={errorIndex} className="text-xs text-red-600 bg-red-50 p-2 rounded">
                        {error}
                      </div>
                    ))}
                    {item.errors.length > 3 && (
                      <div className="text-xs text-muted-foreground">
                        ... and {item.errors.length - 3} more errors
                      </div>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
})

UploadQueue.displayName = 'UploadQueue'