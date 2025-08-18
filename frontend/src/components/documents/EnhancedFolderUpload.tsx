import React, { useState, useRef, useCallback } from 'react'
import { 
  FolderOpen, 
  Upload, 
  Settings, 
  Zap, 
  AlertTriangle,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { FilePreview } from './FilePreview'
import { UploadQueue } from './UploadQueue'
import { folderUploadApi } from '@/lib/api'

interface EnhancedFolderUploadProps {
  collectionId: number
  onUploadComplete: (results: any) => void
  onUploadError: (error: string) => void
}

interface UploadSettings {
  preserveStructure: boolean
  skipUnsupported: boolean
  maxFileSizeMb: number
  batchSize: number
  concurrentJobs: number
  autoStart: boolean
  enablePreviews: boolean
  filterExtensions: string[]
}

interface FileWithPath {
  file: File
  relativePath: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  progress: number
  error?: string
}

export function EnhancedFolderUpload({ 
  collectionId, 
  onUploadComplete, 
  onUploadError 
}: EnhancedFolderUploadProps) {
  const [isDragOver, setIsDragOver] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<FileWithPath[]>([])
  const [uploadSettings, setUploadSettings] = useState<UploadSettings>({
    preserveStructure: true,
    skipUnsupported: true,
    maxFileSizeMb: 500,
    batchSize: 5,
    concurrentJobs: 2,
    autoStart: true,
    enablePreviews: true,
    filterExtensions: []
  })
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false)
  const [supportedFormats, setSupportedFormats] = useState<string[]>([])
  const [activeTab, setActiveTab] = useState('upload')
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const folderInputRef = useRef<HTMLInputElement>(null)
  const zipInputRef = useRef<HTMLInputElement>(null)
  const queueRef = useRef<any>(null)

  // Debug ref availability
  React.useEffect(() => {
    console.log('🔄 EnhancedFolderUpload - queueRef status:', {
      current: !!queueRef.current,
      addToQueue: !!queueRef.current?.addToQueue,
      activeTab
    })
  }, [activeTab])

  // Load supported formats on component mount
  React.useEffect(() => {
    const loadSupportedFormats = async () => {
      try {
        const response = await folderUploadApi.getSupportedFormats()
        setSupportedFormats(response.supported_extensions)
      } catch (error) {
        console.error('Failed to load supported formats:', error)
      }
    }
    loadSupportedFormats()
  }, [])

  const validateFile = (file: File): string | null => {
    // Check file size
    const maxSizeBytes = uploadSettings.maxFileSizeMb * 1024 * 1024
    if (file.size > maxSizeBytes) {
      return `File size exceeds ${uploadSettings.maxFileSizeMb}MB limit`
    }

    // Check if supported format
    const ext = '.' + file.name.toLowerCase().split('.').pop()
    if (!supportedFormats.includes(ext)) {
      if (!uploadSettings.skipUnsupported) {
        return `Unsupported file format: ${ext}`
      }
      return 'skipped' // Special return value for skipped files
    }

    // Check filter extensions
    if (uploadSettings.filterExtensions.length > 0) {
      if (!uploadSettings.filterExtensions.includes(ext)) {
        return 'Filtered out by extension filter'
      }
    }

    return null
  }

  const processFiles = (files: FileList, basePath: string = ''): FileWithPath[] => {
    const processedFiles: FileWithPath[] = []
    
    Array.from(files).forEach((file) => {
      const validation = validateFile(file)
      
      if (validation === 'skipped') {
        return // Skip this file
      }
      
      const relativePath = basePath || file.name
      
      processedFiles.push({
        file,
        relativePath,
        status: validation ? 'failed' : 'pending',
        progress: 0,
        error: validation || undefined
      })
    })

    return processedFiles
  }

  const handleFileSelection = useCallback((files: FileList, basePath?: string) => {
    const newFiles = processFiles(files, basePath)
    setSelectedFiles(prev => [...prev, ...newFiles])
    
    // Auto-switch to preview tab when files are added
    if (newFiles.length > 0) {
      setActiveTab('preview')
    }
  }, [uploadSettings, supportedFormats])

  const handleFolderUpload = async (files: FileList) => {
    handleFileSelection(files, 'folder/')
  }

  const handleZipUpload = async (file: File) => {
    // For ZIP files, we'll let the backend handle extraction
    const zipFiles = new DataTransfer()
    zipFiles.items.add(file)
    handleFileSelection(zipFiles.files, 'zip/')
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
    
    for (const item of items) {
      if (item.kind === 'file') {
        const entry = item.webkitGetAsEntry()
        if (entry) {
          if (entry.isDirectory) {
            await traverseDirectory(entry as FileSystemDirectoryEntry, files, entry.name + '/')
          } else {
            const file = item.getAsFile()
            if (file) files.push(file)
          }
        }
      }
    }
    
    if (files.length > 0) {
      const fileList = new DataTransfer()
      files.forEach(file => fileList.items.add(file))
      handleFileSelection(fileList.files)
    }
  }

  const traverseDirectory = async (
    entry: FileSystemDirectoryEntry, 
    files: File[], 
    path: string = ''
  ) => {
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
              // Store the relative path in the file object
              Object.defineProperty(file, 'webkitRelativePath', {
                value: path + file.name,
                writable: false
              })
              files.push(file)
            } else if (entry.isDirectory) {
              await traverseDirectory(
                entry as FileSystemDirectoryEntry, 
                files, 
                path + entry.name + '/'
              )
            }
          }
          
          readEntries()
        })
      }
      
      readEntries()
    })
  }

  const removeFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index))
  }

  const retryFile = (index: number) => {
    setSelectedFiles(prev => prev.map((file, i) => 
      i === index 
        ? { ...file, status: 'pending', error: undefined }
        : file
    ))
  }

  const clearAllFiles = () => {
    setSelectedFiles([])
  }

  const startUpload = async () => {
    const validFiles = selectedFiles.filter(f => f.status === 'pending')
    
    if (validFiles.length === 0) {
      onUploadError('No valid files to upload')
      return
    }

    try {
      console.log('startUpload called with', validFiles.length, 'valid files')
      console.log('queueRef.current:', queueRef.current)
      console.log('queueRef.current?.addToQueue:', queueRef.current?.addToQueue)
      
      // Switch to queue tab to show progress
      setActiveTab('queue')
      
      // Add files to the upload queue
      console.log('Queue ref check:', {
        queueRefExists: !!queueRef.current,
        addToQueueExists: queueRef.current?.addToQueue,
        activeTab: activeTab
      })
      
      if (queueRef.current && queueRef.current.addToQueue) {
        console.log('✅ Using queue - adding files to queue')
        const files = validFiles.map(f => f.file)
        const relativePaths = validFiles.map(f => f.relativePath)
        
        queueRef.current.addToQueue(files, uploadSettings, relativePaths)
        
        // Clear selected files after adding to queue
        setSelectedFiles([])
        
        // Auto-start if enabled
        if (uploadSettings.autoStart) {
          setTimeout(() => {
            if (queueRef.current && queueRef.current.resumeProcessing) {
              queueRef.current.resumeProcessing()
            }
          }, 500)
        }
      } else {
        console.log('❌ Queue ref not available - using fallback direct upload')
        // Fallback to direct upload if queue ref not available
        const formData = new FormData()
        validFiles.forEach(fileInfo => {
          formData.append('files', fileInfo.file)
        })
        
        formData.append('preserve_structure', uploadSettings.preserveStructure.toString())
        formData.append('skip_unsupported', uploadSettings.skipUnsupported.toString())
        formData.append('max_file_size_mb', uploadSettings.maxFileSizeMb.toString())

        const result = await folderUploadApi.uploadMultipleFiles(collectionId, formData)
        onUploadComplete(result)
        
        // Clear selected files after successful upload
        setSelectedFiles([])
      }
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'
      onUploadError(errorMessage)
    }
  }

  const getFileStats = () => {
    const total = selectedFiles.length
    const valid = selectedFiles.filter(f => f.status !== 'failed').length
    const failed = selectedFiles.filter(f => f.status === 'failed').length
    const totalSize = selectedFiles.reduce((acc, f) => acc + f.file.size, 0)
    
    return { total, valid, failed, totalSize }
  }

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  const stats = getFileStats()

  return (
    <div className="space-y-6">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="upload">
            <Upload className="h-4 w-4 mr-2" />
            Upload
          </TabsTrigger>
          <TabsTrigger value="preview" disabled={selectedFiles.length === 0}>
            <Eye className="h-4 w-4 mr-2" />
            Preview ({selectedFiles.length})
          </TabsTrigger>
          <TabsTrigger value="queue">
            <Zap className="h-4 w-4 mr-2" />
            Queue
          </TabsTrigger>
        </TabsList>

        {/* Upload Tab */}
        <TabsContent value="upload" className="space-y-6">
          {/* Advanced Settings */}
          <Card>
            <Collapsible open={showAdvancedSettings} onOpenChange={setShowAdvancedSettings}>
              <CollapsibleTrigger asChild>
                <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                  <CardTitle className="flex items-center justify-between">
                    <span className="flex items-center gap-2">
                      <Settings className="h-5 w-5" />
                      Upload Settings
                    </span>
                    {showAdvancedSettings ? (
                      <ChevronUp className="h-4 w-4" />
                    ) : (
                      <ChevronDown className="h-4 w-4" />
                    )}
                  </CardTitle>
                </CardHeader>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Basic Settings */}
                    <div className="space-y-3">
                      <h4 className="text-sm font-medium">File Processing</h4>
                      
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
                        <Label htmlFor="skip-unsupported">Skip unsupported files</Label>
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Checkbox
                          id="enable-previews"
                          checked={uploadSettings.enablePreviews}
                          onCheckedChange={(checked) => 
                            setUploadSettings(prev => ({ ...prev, enablePreviews: !!checked }))
                          }
                        />
                        <Label htmlFor="enable-previews">Enable file previews</Label>
                      </div>
                    </div>

                    {/* Advanced Settings */}
                    <div className="space-y-3">
                      <h4 className="text-sm font-medium">Performance</h4>
                      
                      <div className="flex items-center space-x-2">
                        <Label htmlFor="max-size" className="w-32">Max file size (MB):</Label>
                        <input
                          id="max-size"
                          type="number"
                          min="1"
                          max="1000"
                          value={uploadSettings.maxFileSizeMb}
                          onChange={(e) => 
                            setUploadSettings(prev => ({ 
                              ...prev, 
                              maxFileSizeMb: parseInt(e.target.value) || 500 
                            }))
                          }
                          className="w-20 px-2 py-1 border rounded"
                        />
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Label htmlFor="batch-size" className="w-32">Batch size:</Label>
                        <input
                          id="batch-size"
                          type="number"
                          min="1"
                          max="20"
                          value={uploadSettings.batchSize}
                          onChange={(e) => 
                            setUploadSettings(prev => ({ 
                              ...prev, 
                              batchSize: parseInt(e.target.value) || 5 
                            }))
                          }
                          className="w-20 px-2 py-1 border rounded"
                        />
                      </div>
                      
                      <div className="flex items-center space-x-2">
                        <Label htmlFor="concurrent-jobs" className="w-32">Concurrent jobs:</Label>
                        <input
                          id="concurrent-jobs"
                          type="number"
                          min="1"
                          max="5"
                          value={uploadSettings.concurrentJobs}
                          onChange={(e) => 
                            setUploadSettings(prev => ({ 
                              ...prev, 
                              concurrentJobs: parseInt(e.target.value) || 2 
                            }))
                          }
                          className="w-20 px-2 py-1 border rounded"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Supported Formats */}
                  <div className="pt-4 border-t">
                    <h4 className="text-sm font-medium mb-2">Supported Formats</h4>
                    <div className="flex flex-wrap gap-1">
                      {supportedFormats.map(ext => (
                        <Badge key={ext} variant="outline" className="text-xs">
                          {ext}
                        </Badge>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </CollapsibleContent>
            </Collapsible>
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
                  Supports {supportedFormats.length} formats: {supportedFormats.slice(0, 5).join(', ')}
                  {supportedFormats.length > 5 && '...'}
                </p>
              </div>
              
              <div className="flex gap-4">
                <Button 
                  onClick={() => folderInputRef.current?.click()}
                >
                  <FolderOpen className="h-4 w-4 mr-2" />
                  Select Folder
                </Button>
                
                <Button 
                  variant="outline"
                  onClick={() => zipInputRef.current?.click()}
                >
                  <Upload className="h-4 w-4 mr-2" />
                  Upload ZIP
                </Button>
                
                <Button 
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <RefreshCw className="h-4 w-4 mr-2" />
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
                accept={supportedFormats.join(',')}
                onChange={(e) => e.target.files && handleFileSelection(e.target.files)}
                className="hidden"
              />
            </CardContent>
          </Card>

          {/* Quick Stats */}
          {selectedFiles.length > 0 && (
            <Card>
              <CardContent className="flex items-center justify-between py-4">
                <div className="flex items-center gap-4 text-sm">
                  <span><strong>{stats.valid}</strong> valid files</span>
                  {stats.failed > 0 && (
                    <span className="text-red-600">
                      <AlertTriangle className="h-4 w-4 inline mr-1" />
                      <strong>{stats.failed}</strong> failed
                    </span>
                  )}
                  <span><strong>{formatFileSize(stats.totalSize)}</strong> total</span>
                </div>
                
                <div className="flex gap-2">
                  <Button
                    onClick={() => setActiveTab('preview')}
                    variant="outline"
                    size="sm"
                  >
                    <Eye className="h-4 w-4 mr-2" />
                    Preview
                  </Button>
                  <Button
                    onClick={startUpload}
                    disabled={stats.valid === 0}
                  >
                    <Zap className="h-4 w-4 mr-2" />
                    Start Upload
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Preview Tab */}
        <TabsContent value="preview" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>File Preview</CardTitle>
                <div className="flex gap-2">
                  <Button
                    onClick={clearAllFiles}
                    variant="outline"
                    size="sm"
                    disabled={selectedFiles.length === 0}
                  >
                    Clear All
                  </Button>
                  <Button
                    onClick={startUpload}
                    disabled={stats.valid === 0}
                  >
                    <Zap className="h-4 w-4 mr-2" />
                    Upload {stats.valid} Files
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <FilePreview
                files={selectedFiles}
                onRemoveFile={removeFile}
                onRetryFile={retryFile}
                showPreviews={uploadSettings.enablePreviews}
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Queue Tab */}
        <TabsContent value="queue">
          {/* Queue content is rendered below outside tabs */}
        </TabsContent>
      </Tabs>
      
      {/* Always render UploadQueue - visible when queue tab is active */}
      <div className={activeTab === 'queue' ? 'block' : 'hidden'}>
        <UploadQueue
          ref={queueRef}
          collectionId={collectionId}
          onUploadComplete={onUploadComplete}
          onUploadError={onUploadError}
        />
      </div>
    </div>
  )
}