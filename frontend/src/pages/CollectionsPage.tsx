import React, { useState } from 'react'
import { CollectionList } from '@/components/collections/CollectionList'
import { CollectionForm } from '@/components/collections/CollectionForm'
import { Collection } from '@/types/collections'
import { collectionsApi } from '@/lib/api'

export function CollectionsPage() {
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [editingCollection, setEditingCollection] = useState<Collection | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const handleCreateNew = () => {
    setEditingCollection(null)
    setIsFormOpen(true)
  }

  const handleEdit = (collection: Collection) => {
    setEditingCollection(collection)
    setIsFormOpen(true)
  }

  const handleDelete = async (collection: Collection) => {
    if (window.confirm(`Are you sure you want to delete "${collection.name}"? This action cannot be undone.`)) {
      try {
        await collectionsApi.delete(collection.id)
        setRefreshKey(prev => prev + 1) // Trigger refresh
      } catch (error) {
        alert('Failed to delete collection: ' + (error instanceof Error ? error.message : 'Unknown error'))
      }
    }
  }

  const handleFormSave = () => {
    setRefreshKey(prev => prev + 1) // Trigger refresh
  }

  const handleFormClose = () => {
    setIsFormOpen(false)
    setEditingCollection(null)
  }

  return (
    <div className="container mx-auto py-8">
      <CollectionList
        key={refreshKey}
        onCreateNew={handleCreateNew}
        onEdit={handleEdit}
        onDelete={handleDelete}
      />
      
      <CollectionForm
        isOpen={isFormOpen}
        onClose={handleFormClose}
        onSave={handleFormSave}
        collection={editingCollection}
      />
    </div>
  )
}