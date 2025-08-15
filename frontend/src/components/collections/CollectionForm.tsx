import React, { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { collectionsApi } from '@/lib/api'
import { Collection, CollectionCreate } from '@/types/collections'

interface CollectionFormProps {
  isOpen: boolean
  onClose: () => void
  onSave: () => void
  collection?: Collection | null
}

export function CollectionForm({ isOpen, onClose, onSave, collection }: CollectionFormProps) {
  const [formData, setFormData] = useState<CollectionCreate>({
    name: '',
    description: '',
    embedding_model: 'nomic-embed-text',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const isEditing = !!collection

  useEffect(() => {
    if (collection) {
      setFormData({
        name: collection.name,
        description: collection.description || '',
        embedding_model: collection.embedding_model || 'nomic-embed-text',
      })
    } else {
      setFormData({
        name: '',
        description: '',
        embedding_model: 'nomic-embed-text',
      })
    }
    setError(null)
  }, [collection, isOpen])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      if (isEditing && collection) {
        await collectionsApi.update(collection.id, formData)
      } else {
        await collectionsApi.create(formData)
      }
      onSave()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save collection')
    } finally {
      setLoading(false)
    }
  }

  const handleChange = (field: keyof CollectionCreate, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {isEditing ? 'Edit Collection' : 'Create New Collection'}
          </DialogTitle>
          <DialogDescription>
            {isEditing 
              ? 'Update the collection details below.'
              : 'Create a new knowledge base collection to organize your documents.'
            }
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 text-sm text-destructive bg-destructive/10 border border-destructive/20 rounded-md">
              {error}
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="name">Collection Name *</Label>
            <Input
              id="name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              placeholder="Enter collection name"
              required
              disabled={loading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Input
              id="description"
              value={formData.description}
              onChange={(e) => handleChange('description', e.target.value)}
              placeholder="Enter collection description (optional)"
              disabled={loading}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="embedding_model">Embedding Model</Label>
            <Input
              id="embedding_model"
              value={formData.embedding_model}
              onChange={(e) => handleChange('embedding_model', e.target.value)}
              placeholder="nomic-embed-text"
              disabled={loading}
            />
            <p className="text-xs text-muted-foreground">
              The embedding model to use for document processing
            </p>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={loading}>
              Cancel
            </Button>
            <Button type="submit" disabled={loading || !formData.name.trim()}>
              {loading && (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-current mr-2" />
              )}
              {isEditing ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}