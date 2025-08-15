import React, { useState, useEffect } from 'react'
import { FileText, Download, Trash2, Clock, HardDrive } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { documentsApi } from '@/lib/api'
import { Document, DocumentStatus } from '@/types/documents'
import { formatDistanceToNow } from 'date-fns'

interface DocumentListProps {
  collectionId: number
  refreshKey: number
  onDelete: (document: Document) => void
}

export function DocumentList({ collectionId, refreshKey, onDelete }: DocumentListProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadDocuments = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await documentsApi.list(collectionId)
      setDocuments(response.documents)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDocuments()
  }, [collectionId, refreshKey])

  // Poll for processing status updates
  useEffect(() => {
    const pendingDocuments = documents.filter(
      doc => doc.status === DocumentStatus.PENDING || doc.status === DocumentStatus.PROCESSING
    )
    
    if (pendingDocuments.length === 0) return

    const pollInterval = setInterval(async () => {
      try {
        for (const doc of pendingDocuments) {
          const status = await documentsApi.getProcessingStatus(collectionId, doc.id)
          
          // Update document in local state if status changed
          if (status.status !== doc.status || status.chunk_count !== doc.chunk_count) {
            setDocuments(prevDocs => 
              prevDocs.map(d => 
                d.id === doc.id 
                  ? { ...d, status: status.status, chunk_count: status.chunk_count }
                  : d
              )
            )
          }
        }
      } catch (error) {
        console.error('Error polling processing status:', error)
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(pollInterval)
  }, [documents, collectionId])

  const formatFileSize = (bytes: number | undefined) => {
    if (!bytes) return 'Unknown'
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getStatusBadge = (status: DocumentStatus) => {
    switch (status) {
      case DocumentStatus.COMPLETED:
        return <Badge variant="default" className="bg-green-500">✅ Completed</Badge>
      case DocumentStatus.PROCESSING:
        return <Badge variant="secondary">🔄 Processing</Badge>
      case DocumentStatus.PENDING:
        return <Badge variant="outline">⏳ Pending</Badge>
      case DocumentStatus.FAILED:
        return <Badge variant="destructive">❌ Failed</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const handleDelete = async (document: Document) => {
    if (window.confirm(`Are you sure you want to delete "${document.original_filename}"?`)) {
      try {
        await documentsApi.delete(collectionId, document.id)
        onDelete(document)
        loadDocuments() // Refresh list
      } catch (error) {
        alert('Failed to delete document: ' + (error instanceof Error ? error.message : 'Unknown error'))
      }
    }
  }

  if (loading) {
    return (
      <Card>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-destructive mb-4">Error: {error}</p>
            <Button onClick={loadDocuments} variant="outline">
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (documents.length === 0) {
    return (
      <Card>
        <CardContent>
          <div className="text-center py-12">
            <FileText className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Documents Found</h3>
            <p className="text-muted-foreground">
              Upload your first document to get started
            </p>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold">Documents</h3>
          <p className="text-muted-foreground">
            {documents.length} document{documents.length !== 1 ? 's' : ''} in this collection
          </p>
        </div>
      </div>

      {/* Documents Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Size</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Chunks</TableHead>
              <TableHead>Uploaded</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {documents.map((document) => (
              <TableRow key={document.id}>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    <span className="truncate max-w-[200px]" title={document.original_filename}>
                      {document.original_filename}
                    </span>
                  </div>
                </TableCell>
                <TableCell>
                  <span className="text-xs bg-secondary px-2 py-1 rounded">
                    {document.mime_type?.split('/')[1]?.toUpperCase() || 'Unknown'}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <HardDrive className="h-4 w-4 text-muted-foreground" />
                    {formatFileSize(document.size_bytes)}
                  </div>
                </TableCell>
                <TableCell>
                  {getStatusBadge(document.status)}
                </TableCell>
                <TableCell>
                  <span className="text-sm font-mono">
                    {document.chunk_count || 0}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    {formatDistanceToNow(new Date(document.created_at), { addSuffix: true })}
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDelete(document)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>

      {/* Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Total Files</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{documents.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Total Size</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatFileSize(documents.reduce((sum, doc) => sum + (doc.size_bytes || 0), 0))}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Total Chunks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {documents.reduce((sum, doc) => sum + (doc.chunk_count || 0), 0)}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}