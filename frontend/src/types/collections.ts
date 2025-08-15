export interface Collection {
  id: number
  name: string
  description?: string
  embedding_model?: string
  total_documents: number
  total_chunks: number
  created_at: string
  updated_at: string
}

export interface CollectionCreate {
  name: string
  description?: string
  embedding_model?: string
}

export interface CollectionListResponse {
  collections: Collection[]
  total: number
}