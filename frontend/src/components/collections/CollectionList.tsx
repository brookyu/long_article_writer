import React, { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, Database, FileText, Clock, ExternalLink } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { collectionsApi } from '@/lib/api'
import { Collection } from '@/types/collections'
import { formatDistanceToNow } from 'date-fns'

interface CollectionListProps {
  onCreateNew: () => void
  onEdit: (collection: Collection) => void
  onDelete: (collection: Collection) => void
}

export function CollectionList({ onCreateNew, onEdit, onDelete }: CollectionListProps) {
  const [collections, setCollections] = useState<Collection[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadCollections = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await collectionsApi.list()
      setCollections(response.collections)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load collections')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCollections()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  if (error) {
    return (
      <Card>
        <CardContent>
          <div className="text-center py-8">
            <p className="text-destructive mb-4">Error: {error}</p>
            <Button onClick={loadCollections} variant="outline">
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (collections.length === 0) {
    return (
      <Card>
        <CardContent>
          <div className="text-center py-12">
            <Database className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Collections Found</h3>
            <p className="text-muted-foreground mb-6">
              Create your first knowledge base collection to get started
            </p>
            <Button onClick={onCreateNew}>
              <Plus className="h-4 w-4 mr-2" />
              Create Collection
            </Button>
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
          <h2 className="text-2xl font-bold">Knowledge Base Collections</h2>
          <p className="text-muted-foreground">
            Manage your document collections and knowledge bases
          </p>
        </div>
        <Button onClick={onCreateNew}>
          <Plus className="h-4 w-4 mr-2" />
          New Collection
        </Button>
      </div>

      {/* Collections Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Description</TableHead>
              <TableHead>Documents</TableHead>
              <TableHead>Chunks</TableHead>
              <TableHead>Model</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {collections.map((collection) => (
              <TableRow key={collection.id}>
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-muted-foreground" />
                    <Link 
                      to={`/collections/${collection.id}`}
                      className="hover:underline font-medium"
                    >
                      {collection.name}
                    </Link>
                  </div>
                </TableCell>
                <TableCell>
                  <span className="text-muted-foreground">
                    {collection.description || 'No description'}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    {collection.total_documents}
                  </div>
                </TableCell>
                <TableCell>
                  <span className="text-sm font-mono">
                    {collection.total_chunks.toLocaleString()}
                  </span>
                </TableCell>
                <TableCell>
                  <span className="text-xs bg-secondary px-2 py-1 rounded">
                    {collection.embedding_model || 'Default'}
                  </span>
                </TableCell>
                <TableCell>
                  <div className="flex items-center gap-1 text-sm text-muted-foreground">
                    <Clock className="h-4 w-4" />
                    {formatDistanceToNow(new Date(collection.created_at), { addSuffix: true })}
                  </div>
                </TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-2">
                    <Link to={`/collections/${collection.id}`}>
                      <Button variant="ghost" size="sm">
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </Link>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onEdit(collection)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(collection)}
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

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Total Collections</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{collections.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {collections.reduce((sum, c) => sum + c.total_documents, 0)}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Total Chunks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {collections.reduce((sum, c) => sum + c.total_chunks, 0).toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}