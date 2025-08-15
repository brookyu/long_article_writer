export interface ArticleReference {
  number: number
  title: string
  url: string
  engine: string
  accessed: string
}

export interface Article {
  id: number
  status: 'pending' | 'generating' | 'completed' | 'failed'
  topic: string
  title?: string
  content?: string
  word_count?: number
  generation_time_seconds?: number
  references?: ArticleReference[]
  created_at: string
  updated_at: string
}

export interface ArticleRequest {
  topic: string
  subtopics?: string[]
  article_type?: 'comprehensive' | 'summary' | 'technical' | 'overview'
  target_length?: 'short' | 'medium' | 'long'
  writing_style?: 'professional' | 'academic' | 'casual' | 'technical'
}

export interface ArticleListResponse {
  articles: Article[]
  total: number
  collection_id: number
}