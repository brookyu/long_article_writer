import React, { useState, useEffect } from 'react'
import { Search, FileText, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { documentsApi } from '@/lib/api'

interface DocumentSearchProps {
  collectionId: number
}

interface SearchResult {
  milvus_id: string
  chunk_id: number
  document_id: number
  chunk_index: number
  text: string
  char_count: number
  score: number
  metadata: any
}

export function DocumentSearch({ collectionId }: DocumentSearchProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [documentNames, setDocumentNames] = useState<Record<number, string>>({})

  // Fetch document names when component mounts
  useEffect(() => {
    const fetchDocumentNames = async () => {
      try {
        const response = await documentsApi.list(collectionId)
        const nameMap: Record<number, string> = {}
        response.documents.forEach((doc: any) => {
          nameMap[doc.id] = doc.original_filename || `Document ${doc.id}`
        })
        setDocumentNames(nameMap)
      } catch (error) {
        console.error('Failed to fetch document names:', error)
      }
    }
    fetchDocumentNames()
  }, [collectionId])

  const handleSearch = async () => {
    if (!query.trim()) return

    try {
      setLoading(true)
      console.log('Searching for:', query.trim(), 'in collection:', collectionId)
      const response = await documentsApi.search(collectionId, query.trim())
      console.log('Search response:', response) // Debug log
      console.log('Results array:', response.results)
      setResults(response.results || [])
      setHasSearched(true)
    } catch (error) {
      console.error('Search failed:', error)
      console.error('Error details:', error)
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Search className="h-5 w-5" />
          Search Documents
        </CardTitle>
        <CardDescription>
          Find relevant content across all documents in this collection
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Search Input */}
        <div className="flex gap-2">
          <Input
            placeholder="Enter your search query..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
            className="flex-1"
          />
          <Button 
            onClick={handleSearch} 
            disabled={loading || !query.trim()}
          >
            {loading ? (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
            ) : (
              <Search className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* Search Results */}
        {hasSearched && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-sm font-medium">
                Search Results
              </h4>
              {results.length > 0 && (
                <Badge variant="secondary">
                  {results.length} match{results.length !== 1 ? 'es' : ''}
                </Badge>
              )}
            </div>

            {results.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <FileText className="mx-auto h-12 w-12 mb-4 opacity-50" />
                <p>No documents match your search.</p>
                <p className="text-sm">Try different keywords or check if documents are processed.</p>
              </div>
            ) : (
              <div className="space-y-3">
                {results.map((result, index) => (
                  <Card key={`${result.document_id}-${index}`} className="border-l-4 border-l-primary/20">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <FileText className="h-4 w-4 text-muted-foreground" />
                            <span className="font-medium">
                              {documentNames[result.document_id] || `Document ${result.document_id}`}
                            </span>
                            <Badge variant="outline" className="text-xs">
                              <Sparkles className="h-3 w-3 mr-1" />
                              {Math.round(result.score * 100)}% match
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground line-clamp-3">
                            {result.text}
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Search Tips */}
        {!hasSearched && (
          <div className="bg-muted/30 rounded-lg p-4">
            <h4 className="text-sm font-medium mb-2">💡 Search Tips</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Use specific keywords for better results</li>
              <li>• Try different phrasings or synonyms</li>
              <li>• Search works on processed documents only</li>
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}