import React, { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Database, Plus, PenTool } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DocumentUpload } from '@/components/documents/DocumentUpload'
import { FolderUpload } from '@/components/documents/FolderUpload'
import { EnhancedFolderUpload } from '@/components/documents/EnhancedFolderUpload'
import { DocumentList } from '@/components/documents/DocumentList'
import { DocumentSearch } from '@/components/documents/DocumentSearch'
import { FolderTree } from '@/components/folders/FolderTree'
import { FolderBrowser } from '@/components/folders/FolderBrowser'
import { collectionsApi } from '@/lib/api'
import { Collection } from '@/types/collections'
import { Document } from '@/types/documents'
import { formatDistanceToNow } from 'date-fns'

export function CollectionDetailPage() {
  const { id } = useParams<{ id: string }>()
  const collectionId = parseInt(id || '0')
  
  const [collection, setCollection] = useState<Collection | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadMode, setUploadMode] = useState<'individual' | 'folder' | 'enhanced'>('enhanced')
  const [viewMode, setViewMode] = useState<'documents' | 'folders' | 'browser'>('documents')
  const [refreshKey, setRefreshKey] = useState(0)

  const loadCollection = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await collectionsApi.get(collectionId)
      setCollection(response)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load collection')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (collectionId) {
      loadCollection()
    }
  }, [collectionId])

  const handleUploadComplete = (document: Document) => {
    setRefreshKey(prev => prev + 1)
    // Refresh collection stats
    loadCollection()
  }

  const handleUploadError = (error: string) => {
    console.error('Upload error:', error)
  }

  const handleDocumentDelete = (document: Document) => {
    setRefreshKey(prev => prev + 1)
    // Refresh collection stats
    loadCollection()
  }

  if (loading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      </div>
    )
  }

  if (error || !collection) {
    return (
      <div className="container mx-auto py-8">
        <Card>
          <CardContent>
            <div className="text-center py-8">
              <p className="text-destructive mb-4">
                {error || 'Collection not found'}
              </p>
              <Link to="/collections">
                <Button variant="outline">
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  Back to Collections
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/collections">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <Database className="h-6 w-6 text-muted-foreground" />
            <div>
              <h1 className="text-2xl font-bold">{collection.name}</h1>
              {collection.description && (
                <p className="text-muted-foreground">{collection.description}</p>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="default">
            <Link to={`/write/${collectionId}`}>
              <PenTool className="h-4 w-4 mr-2" />
              Write Article
            </Link>
          </Button>
          <Button onClick={() => setShowUpload(!showUpload)} variant="outline">
            <Plus className="h-4 w-4 mr-2" />
            Upload Documents
          </Button>
        </div>
      </div>

      {/* Collection Info */}
      <Card>
        <CardHeader>
          <CardTitle>Collection Details</CardTitle>
          <CardDescription>
            Information about this knowledge base collection
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-muted-foreground">Documents</p>
              <p className="text-2xl font-bold">{collection.total_documents}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Chunks</p>
              <p className="text-2xl font-bold">{collection.total_chunks.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Embedding Model</p>
              <p className="text-sm font-medium">{collection.embedding_model || 'Default'}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Created</p>
              <p className="text-sm font-medium">
                {formatDistanceToNow(new Date(collection.created_at), { addSuffix: true })}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Document Upload */}
      {showUpload && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Upload Documents</CardTitle>
                <CardDescription>
                  Add documents to this collection for AI-powered analysis
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  variant={uploadMode === 'enhanced' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setUploadMode('enhanced')}
                >
                  Enhanced Upload
                </Button>
                <Button
                  variant={uploadMode === 'folder' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setUploadMode('folder')}
                >
                  Simple Folder
                </Button>
                <Button
                  variant={uploadMode === 'individual' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setUploadMode('individual')}
                >
                  Individual Files
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {uploadMode === 'enhanced' ? (
              <EnhancedFolderUpload
                collectionId={collectionId}
                onUploadComplete={handleUploadComplete}
                onUploadError={handleUploadError}
              />
            ) : uploadMode === 'folder' ? (
              <FolderUpload
                collectionId={collectionId}
                onUploadComplete={handleUploadComplete}
                onUploadError={handleUploadError}
              />
            ) : (
              <DocumentUpload
                collectionId={collectionId}
                onUploadComplete={handleUploadComplete}
                onUploadError={handleUploadError}
              />
            )}
          </CardContent>
        </Card>
      )}

      {/* View Mode Selector */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Content Views</CardTitle>
            <div className="flex gap-2">
              <Button
                variant={viewMode === 'documents' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('documents')}
              >
                Document List
              </Button>
              <Button
                variant={viewMode === 'folders' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('folders')}
              >
                Folder Tree
              </Button>
              <Button
                variant={viewMode === 'browser' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setViewMode('browser')}
              >
                Folder Browser
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Content Views */}
      {viewMode === 'documents' && (
        <>
          {/* Document Search */}
          <DocumentSearch collectionId={collectionId} />

          {/* Document List */}
          <DocumentList
            collectionId={collectionId}
            refreshKey={refreshKey}
            onDelete={handleDocumentDelete}
          />
        </>
      )}

      {viewMode === 'folders' && (
        <FolderTree 
          collectionId={collectionId}
          includeDocuments={true}
          searchable={true}
          showStatistics={true}
        />
      )}

      {viewMode === 'browser' && (
        <FolderBrowser 
          collectionId={collectionId}
          showDocuments={true}
          allowEdit={false}
        />
      )}
    </div>
  )
}