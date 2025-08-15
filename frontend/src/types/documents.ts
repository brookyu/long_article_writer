export interface Document {
  id: number
  collection_id: number
  filename: string
  original_filename: string
  mime_type?: string
  size_bytes?: number
  sha256: string
  status: DocumentStatus
  error_message?: string
  chunk_count?: number
  created_at: string
  updated_at: string
}

export enum DocumentStatus {
  PENDING = "pending",
  PROCESSING = "processing", 
  COMPLETED = "completed",
  FAILED = "failed"
}

export interface DocumentListResponse {
  documents: Document[]
  total: number
}