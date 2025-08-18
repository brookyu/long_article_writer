import React, { useState, useEffect } from 'react'
import { 
  ChevronRight, 
  ChevronDown, 
  Folder, 
  FolderOpen, 
  File,
  Search,
  Filter,
  BarChart3,
  Tag,
  Calendar,
  FileText,
  Hash
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'

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
  children?: FolderNode[]
  documents?: Array<{
    id: number
    filename: string
    size_bytes: number
    status: string
    relative_path: string
  }>
}

interface FolderTreeProps {
  collectionId: number
  onFolderSelect?: (folder: FolderNode) => void
  includeDocuments?: boolean
  maxDepth?: number
  searchable?: boolean
  showStatistics?: boolean
}

interface FolderStats {
  total_folders: number
  total_documents: number
  total_size_bytes: number
  max_depth: number
  folder_types: Record<string, number>
  content_categories: Record<string, number>
}

const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

const getFolderTypeIcon = (folderType: string) => {
  const icons = {
    documentation: <FileText className="h-4 w-4 text-blue-500" />,
    source: <Hash className="h-4 w-4 text-green-500" />,
    data: <BarChart3 className="h-4 w-4 text-purple-500" />,
    media: <File className="h-4 w-4 text-orange-500" />,
    test: <Search className="h-4 w-4 text-red-500" />,
    configuration: <Filter className="h-4 w-4 text-gray-500" />,
  }
  return icons[folderType] || <Folder className="h-4 w-4 text-gray-400" />
}

const getFolderTypeColor = (folderType: string) => {
  const colors = {
    documentation: 'bg-blue-100 text-blue-800',
    source: 'bg-green-100 text-green-800',
    data: 'bg-purple-100 text-purple-800',
    media: 'bg-orange-100 text-orange-800',
    test: 'bg-red-100 text-red-800',
    configuration: 'bg-gray-100 text-gray-800',
  }
  return colors[folderType] || 'bg-gray-100 text-gray-600'
}

export function FolderTree({ 
  collectionId, 
  onFolderSelect, 
  includeDocuments = false,
  maxDepth,
  searchable = true,
  showStatistics = true
}: FolderTreeProps) {
  const [folderTree, setFolderTree] = useState<FolderNode[]>([])
  const [folderStats, setFolderStats] = useState<FolderStats | null>(null)
  const [expandedFolders, setExpandedFolders] = useState<Set<number>>(new Set())
  const [selectedFolder, setSelectedFolder] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filteredTree, setFilteredTree] = useState<FolderNode[]>([])

  // Load folder tree
  useEffect(() => {
    const loadFolderTree = async () => {
      try {
        setLoading(true)
        
        const params = new URLSearchParams()
        if (includeDocuments) params.append('include_documents', 'true')
        if (maxDepth !== undefined) params.append('max_depth', maxDepth.toString())
        
        const response = await fetch(
          `/api/kb/collections/${collectionId}/folder-tree/?${params}`,
          { method: 'GET' }
        )
        
        if (!response.ok) {
          throw new Error(`Failed to load folder tree: ${response.statusText}`)
        }
        
        const data = await response.json()
        setFolderTree(data.folder_tree || [])
        setFilteredTree(data.folder_tree || [])
        
        // Auto-expand first level
        if (data.folder_tree?.length > 0) {
          const firstLevelIds = data.folder_tree.map((folder: FolderNode) => folder.id)
          setExpandedFolders(new Set(firstLevelIds))
        }
        
      } catch (error) {
        console.error('Error loading folder tree:', error)
        setError(error instanceof Error ? error.message : 'Failed to load folder tree')
      } finally {
        setLoading(false)
      }
    }

    loadFolderTree()
  }, [collectionId, includeDocuments, maxDepth])

  // Load folder statistics
  useEffect(() => {
    if (!showStatistics) return

    const loadFolderStats = async () => {
      try {
        const response = await fetch(
          `/api/kb/collections/${collectionId}/folder-stats/`,
          { method: 'GET' }
        )
        
        if (!response.ok) {
          throw new Error(`Failed to load folder stats: ${response.statusText}`)
        }
        
        const data = await response.json()
        setFolderStats(data)
        
      } catch (error) {
        console.error('Error loading folder stats:', error)
      }
    }

    loadFolderStats()
  }, [collectionId, showStatistics])

  // Filter tree based on search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredTree(folderTree)
      return
    }

    const filterTree = (nodes: FolderNode[]): FolderNode[] => {
      return nodes.filter(node => {
        const matchesSearch = 
          node.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          node.full_path.toLowerCase().includes(searchQuery.toLowerCase()) ||
          (node.content_summary && node.content_summary.toLowerCase().includes(searchQuery.toLowerCase())) ||
          node.auto_tags.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))

        const hasMatchingChildren = node.children ? filterTree(node.children).length > 0 : false

        if (matchesSearch || hasMatchingChildren) {
          return {
            ...node,
            children: node.children ? filterTree(node.children) : undefined
          }
        }

        return false
      }).filter(Boolean) as FolderNode[]
    }

    setFilteredTree(filterTree(folderTree))
  }, [searchQuery, folderTree])

  const toggleFolder = (folderId: number) => {
    const newExpanded = new Set(expandedFolders)
    if (newExpanded.has(folderId)) {
      newExpanded.delete(folderId)
    } else {
      newExpanded.add(folderId)
    }
    setExpandedFolders(newExpanded)
  }

  const selectFolder = (folder: FolderNode) => {
    setSelectedFolder(folder.id)
    if (onFolderSelect) {
      onFolderSelect(folder)
    }
  }

  const renderFolderNode = (folder: FolderNode, level: number = 0) => {
    const isExpanded = expandedFolders.has(folder.id)
    const isSelected = selectedFolder === folder.id
    const hasChildren = folder.children && folder.children.length > 0
    const hasDocuments = folder.documents && folder.documents.length > 0

    return (
      <div key={folder.id} className="select-none">
        {/* Folder Row */}
        <div
          className={`flex items-center gap-2 py-2 px-2 rounded-md cursor-pointer hover:bg-muted/50 transition-colors ${
            isSelected ? 'bg-primary/10 border border-primary/20' : ''
          }`}
          style={{ paddingLeft: `${level * 20 + 8}px` }}
          onClick={() => selectFolder(folder)}
        >
          {/* Expand/Collapse Button */}
          {hasChildren ? (
            <Button
              variant="ghost"
              size="sm"
              className="h-6 w-6 p-0"
              onClick={(e) => {
                e.stopPropagation()
                toggleFolder(folder.id)
              }}
            >
              {isExpanded ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronRight className="h-4 w-4" />
              )}
            </Button>
          ) : (
            <div className="w-6" />
          )}

          {/* Folder Icon */}
          <div className="flex-shrink-0">
            {hasChildren && isExpanded ? (
              <FolderOpen className="h-4 w-4 text-blue-500" />
            ) : (
              getFolderTypeIcon(folder.folder_metadata?.folder_type || 'general')
            )}
          </div>

          {/* Folder Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-medium text-sm truncate">{folder.name}</span>
              
              {/* Folder Type Badge */}
              {folder.folder_metadata?.folder_type && folder.folder_metadata.folder_type !== 'general' && (
                <Badge
                  variant="secondary"
                  className={`text-xs ${getFolderTypeColor(folder.folder_metadata.folder_type)}`}
                >
                  {folder.folder_metadata.folder_type}
                </Badge>
              )}
            </div>
            
            {/* Stats */}
            <div className="flex items-center gap-3 text-xs text-muted-foreground mt-1">
              {folder.document_count > 0 && (
                <span className="flex items-center gap-1">
                  <File className="h-3 w-3" />
                  {folder.document_count}
                </span>
              )}
              
              {folder.total_documents !== folder.document_count && (
                <span className="flex items-center gap-1">
                  <Folder className="h-3 w-3" />
                  {folder.total_documents} total
                </span>
              )}
              
              {folder.total_size_bytes > 0 && (
                <span>{formatFileSize(folder.total_size_bytes)}</span>
              )}
            </div>
          </div>

          {/* Tags */}
          {folder.auto_tags && folder.auto_tags.length > 0 && (
            <div className="flex items-center gap-1">
              <Tag className="h-3 w-3 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">
                {folder.auto_tags.slice(0, 2).join(', ')}
                {folder.auto_tags.length > 2 && '...'}
              </span>
            </div>
          )}
        </div>

        {/* Children */}
        {hasChildren && (
          <Collapsible open={isExpanded}>
            <CollapsibleContent>
              <div className="pl-4">
                {folder.children!.map(child => renderFolderNode(child, level + 1))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        )}

        {/* Documents */}
        {hasDocuments && isExpanded && includeDocuments && (
          <div className="pl-8 mt-1">
            {folder.documents!.map(doc => (
              <div
                key={doc.id}
                className="flex items-center gap-2 py-1 px-2 text-sm text-muted-foreground hover:bg-muted/30 rounded"
              >
                <File className="h-3 w-3" />
                <span className="flex-1 truncate">{doc.filename}</span>
                <span className="text-xs">{formatFileSize(doc.size_bytes)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

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
            <p>Error loading folder structure</p>
            <p className="text-sm mt-2">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-4">
      {/* Statistics */}
      {showStatistics && folderStats && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" />
              Collection Statistics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">{folderStats.total_folders}</div>
                <div className="text-muted-foreground">Folders</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{folderStats.total_documents}</div>
                <div className="text-muted-foreground">Documents</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold">{formatFileSize(folderStats.total_size_bytes)}</div>
                <div className="text-muted-foreground">Total Size</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">{folderStats.max_depth}</div>
                <div className="text-muted-foreground">Max Depth</div>
              </div>
            </div>
            
            {/* Folder Types */}
            {Object.keys(folderStats.folder_types).length > 0 && (
              <div className="mt-4 pt-4 border-t">
                <div className="text-sm font-medium mb-2">Folder Types</div>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(folderStats.folder_types).map(([type, count]) => (
                    <Badge key={type} variant="outline" className="text-xs">
                      {type}: {count}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Folder Tree */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Folder className="h-5 w-5" />
              Folder Structure
            </CardTitle>
            
            {/* Search */}
            {searchable && (
              <div className="flex items-center gap-2">
                <div className="relative">
                  <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Search folders..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-8 w-64"
                  />
                </div>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {filteredTree.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Folder className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p>No folders found</p>
              {searchQuery && (
                <p className="text-sm">Try adjusting your search criteria</p>
              )}
            </div>
          ) : (
            <div className="space-y-1 max-h-96 overflow-y-auto">
              {filteredTree.map(folder => renderFolderNode(folder))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}