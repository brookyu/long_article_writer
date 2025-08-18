import React, { useState, useEffect } from 'react'
import { 
  ChevronRight, 
  Home, 
  Folder, 
  File,
  Search,
  SortAsc,
  SortDesc,
  Grid,
  List,
  Calendar,
  Hash,
  Tag,
  Edit,
  Trash2,
  Download,
  Eye
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

interface FolderNode {
  id: number
  name: string
  full_path: string
  parent_id?: number
  depth: number
  document_count: number
  total_documents: number
  total_size_bytes: number
  folder_metadata: {
    folder_type: string
    is_nested: boolean
    root_folder?: string
    immediate_parent?: string
  }
  auto_tags: string[]
  content_summary?: string
  last_updated?: string
  created_at?: string
  breadcrumb?: Array<{
    name: string
    path: string
    depth: number
    is_current: boolean
  }>
  children?: FolderNode[]
  documents?: Array<{
    id: number
    filename: string
    size_bytes: number
    status: string
    relative_path: string
    mime_type?: string
    created_at?: string
    updated_at?: string
  }>
}

interface FolderBrowserProps {
  collectionId: number
  initialFolderId?: number
  onFileSelect?: (file: any) => void
  onFolderChange?: (folder: FolderNode) => void
  showDocuments?: boolean
  allowEdit?: boolean
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const getFileIcon = (filename: string, mimeType?: string) => {
  const ext = filename.toLowerCase().split('.').pop()
  
  const iconMap = {
    'pdf': '📄',
    'doc': '📝', 'docx': '📝',
    'txt': '📄', 'md': '📄',
    'html': '🌐', 'htm': '🌐',
    'json': '📋', 'csv': '📊',
    'jpg': '🖼️', 'jpeg': '🖼️', 'png': '🖼️', 'gif': '🖼️',
    'zip': '📦', 'tar': '📦', 'gz': '📦'
  }
  
  return iconMap[ext as keyof typeof iconMap] || '📄'
}

export function FolderBrowser({ 
  collectionId, 
  initialFolderId,
  onFileSelect,
  onFolderChange,
  showDocuments = true,
  allowEdit = false
}: FolderBrowserProps) {
  const [currentFolder, setCurrentFolder] = useState<FolderNode | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [sortBy, setSortBy] = useState<'name' | 'size' | 'date'>('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [viewMode, setViewMode] = useState<'list' | 'grid'>('list')
  const [filteredItems, setFilteredItems] = useState<{
    folders: FolderNode[]
    documents: any[]
  }>({ folders: [], documents: [] })

  // Load folder details
  const loadFolder = async (folderId?: number) => {
    try {
      setLoading(true)
      setError(null)
      
      let url = `/api/kb/collections/${collectionId}/folder-tree/`
      if (folderId) {
        url = `/api/kb/collections/${collectionId}/folders/${folderId}/`
      }
      
      const params = new URLSearchParams()
      if (showDocuments) params.append('include_documents', 'true')
      params.append('include_children', 'true')
      
      const response = await fetch(`${url}?${params}`)
      
      if (!response.ok) {
        throw new Error(`Failed to load folder: ${response.statusText}`)
      }
      
      const data = await response.json()
      
      if (folderId) {
        setCurrentFolder(data)
      } else {
        // Root level - create virtual root folder
        setCurrentFolder({
          id: 0,
          name: 'Root',
          full_path: '',
          depth: 0,
          document_count: 0,
          total_documents: 0,
          total_size_bytes: 0,
          folder_metadata: { folder_type: 'root', is_nested: false },
          auto_tags: [],
          children: data.folder_tree || [],
          documents: [],
          breadcrumb: [{ name: 'Root', path: '', depth: 0, is_current: true }]
        })
      }
      
    } catch (error) {
      console.error('Error loading folder:', error)
      setError(error instanceof Error ? error.message : 'Failed to load folder')
    } finally {
      setLoading(false)
    }
  }

  // Load initial folder
  useEffect(() => {
    loadFolder(initialFolderId)
  }, [collectionId, initialFolderId])

  // Update filtered items when folder changes or search/sort changes
  useEffect(() => {
    if (!currentFolder) {
      setFilteredItems({ folders: [], documents: [] })
      return
    }

    let folders = currentFolder.children || []
    let documents = currentFolder.documents || []

    // Apply search filter
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase()
      folders = folders.filter(folder => 
        folder.name.toLowerCase().includes(query) ||
        folder.auto_tags.some(tag => tag.toLowerCase().includes(query))
      )
      documents = documents.filter(doc => 
        doc.filename.toLowerCase().includes(query)
      )
    }

    // Sort folders
    folders.sort((a, b) => {
      let comparison = 0
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name)
          break
        case 'size':
          comparison = a.total_size_bytes - b.total_size_bytes
          break
        case 'date':
          const dateA = new Date(a.last_updated || a.created_at || 0)
          const dateB = new Date(b.last_updated || b.created_at || 0)
          comparison = dateA.getTime() - dateB.getTime()
          break
      }
      return sortOrder === 'asc' ? comparison : -comparison
    })

    // Sort documents
    documents.sort((a, b) => {
      let comparison = 0
      switch (sortBy) {
        case 'name':
          comparison = a.filename.localeCompare(b.filename)
          break
        case 'size':
          comparison = a.size_bytes - b.size_bytes
          break
        case 'date':
          const dateA = new Date(a.updated_at || a.created_at || 0)
          const dateB = new Date(b.updated_at || b.created_at || 0)
          comparison = dateA.getTime() - dateB.getTime()
          break
      }
      return sortOrder === 'asc' ? comparison : -comparison
    })

    setFilteredItems({ folders, documents })
  }, [currentFolder, searchQuery, sortBy, sortOrder])

  // Navigate to folder
  const navigateToFolder = async (folderId: number, folder?: FolderNode) => {
    if (folder) {
      setCurrentFolder(folder)
      if (onFolderChange) {
        onFolderChange(folder)
      }
    } else {
      await loadFolder(folderId)
    }
  }

  // Navigate to parent
  const navigateToParent = async () => {
    if (currentFolder?.parent_id) {
      await loadFolder(currentFolder.parent_id)
    } else {
      await loadFolder() // Go to root
    }
  }

  // Toggle sort order
  const toggleSortOrder = () => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
  }

  // Handle file selection
  const handleFileSelect = (file: any) => {
    if (onFileSelect) {
      onFileSelect(file)
    }
  }

  const renderBreadcrumb = () => {
    if (!currentFolder?.breadcrumb) return null

    return (
      <div className="flex items-center gap-1 text-sm text-muted-foreground mb-4">
        <Home className="h-4 w-4" />
        {currentFolder.breadcrumb.map((crumb, index) => (
          <React.Fragment key={index}>
            {index > 0 && <ChevronRight className="h-4 w-4" />}
            <button
              onClick={() => {
                if (crumb.path === '') {
                  loadFolder() // Root
                } else {
                  // Find folder by path and navigate
                  // This would need more sophisticated path resolution
                }
              }}
              className={`hover:text-foreground transition-colors ${
                crumb.is_current ? 'text-foreground font-medium' : ''
              }`}
            >
              {crumb.name}
            </button>
          </React.Fragment>
        ))}
      </div>
    )
  }

  const renderFolderGrid = () => (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
      {filteredItems.folders.map(folder => (
        <Card
          key={folder.id}
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => navigateToFolder(folder.id, folder)}
        >
          <CardContent className="p-4 text-center">
            <Folder className="h-8 w-8 text-blue-500 mx-auto mb-2" />
            <div className="text-sm font-medium truncate">{folder.name}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {folder.total_documents} items
            </div>
            {folder.auto_tags.length > 0 && (
              <div className="mt-2">
                <Badge variant="outline" className="text-xs">
                  {folder.auto_tags[0]}
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>
      ))}
      
      {showDocuments && filteredItems.documents.map(doc => (
        <Card
          key={doc.id}
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => handleFileSelect(doc)}
        >
          <CardContent className="p-4 text-center">
            <div className="text-2xl mb-2">{getFileIcon(doc.filename, doc.mime_type)}</div>
            <div className="text-sm font-medium truncate">{doc.filename}</div>
            <div className="text-xs text-muted-foreground mt-1">
              {formatFileSize(doc.size_bytes)}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )

  const renderFolderList = () => (
    <div className="space-y-2">
      {filteredItems.folders.map(folder => (
        <div
          key={folder.id}
          className="flex items-center gap-3 p-3 rounded-md hover:bg-muted/50 cursor-pointer transition-colors"
          onClick={() => navigateToFolder(folder.id, folder)}
        >
          <Folder className="h-5 w-5 text-blue-500 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium truncate">{folder.name}</span>
              {folder.folder_metadata.folder_type !== 'general' && (
                <Badge variant="secondary" className="text-xs">
                  {folder.folder_metadata.folder_type}
                </Badge>
              )}
            </div>
            <div className="text-sm text-muted-foreground">
              {folder.total_documents} items • {formatFileSize(folder.total_size_bytes)}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {folder.auto_tags.slice(0, 2).map(tag => (
              <Badge key={tag} variant="outline" className="text-xs">
                {tag}
              </Badge>
            ))}
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          </div>
        </div>
      ))}
      
      {showDocuments && filteredItems.documents.map(doc => (
        <div
          key={doc.id}
          className="flex items-center gap-3 p-3 rounded-md hover:bg-muted/50 cursor-pointer transition-colors"
          onClick={() => handleFileSelect(doc)}
        >
          <div className="text-lg flex-shrink-0">{getFileIcon(doc.filename, doc.mime_type)}</div>
          <div className="flex-1 min-w-0">
            <div className="font-medium truncate">{doc.filename}</div>
            <div className="text-sm text-muted-foreground">
              {formatFileSize(doc.size_bytes)} • {doc.status}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {allowEdit && (
              <>
                <Button variant="ghost" size="sm">
                  <Eye className="h-4 w-4" />
                </Button>
                <Button variant="ghost" size="sm">
                  <Edit className="h-4 w-4" />
                </Button>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  )

  if (loading) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-center">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="text-center text-red-600">
            <p>Error loading folder</p>
            <p className="text-sm mt-2">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Folder className="h-5 w-5" />
              {currentFolder?.name || 'Folder Browser'}
            </CardTitle>
            
            <div className="flex items-center gap-2">
              {/* View Mode Toggle */}
              <div className="flex border rounded-md">
                <Button
                  variant={viewMode === 'list' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('list')}
                >
                  <List className="h-4 w-4" />
                </Button>
                <Button
                  variant={viewMode === 'grid' ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setViewMode('grid')}
                >
                  <Grid className="h-4 w-4" />
                </Button>
              </div>
              
              {/* Sort Controls */}
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as any)}
                className="px-3 py-1 border rounded-md text-sm"
              >
                <option value="name">Name</option>
                <option value="size">Size</option>
                <option value="date">Date</option>
              </select>
              
              <Button
                variant="ghost"
                size="sm"
                onClick={toggleSortOrder}
              >
                {sortOrder === 'asc' ? <SortAsc className="h-4 w-4" /> : <SortDesc className="h-4 w-4" />}
              </Button>
            </div>
          </div>
          
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search in this folder..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>
        </CardHeader>
        
        <CardContent>
          {/* Breadcrumb */}
          {renderBreadcrumb()}
          
          {/* Navigation */}
          {currentFolder && currentFolder.id !== 0 && (
            <div className="mb-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={navigateToParent}
                className="text-muted-foreground"
              >
                ← Back to parent folder
              </Button>
            </div>
          )}
          
          {/* Content */}
          {filteredItems.folders.length === 0 && filteredItems.documents.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Folder className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>This folder is empty</p>
              {searchQuery && (
                <p className="text-sm">No items match your search</p>
              )}
            </div>
          ) : (
            <>
              {viewMode === 'grid' ? renderFolderGrid() : renderFolderList()}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}