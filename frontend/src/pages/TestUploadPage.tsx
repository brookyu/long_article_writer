/**
 * Test Upload Page
 * Testing the streaming upload system with real-time progress
 */

import React from 'react'
import { StreamingDocumentUpload } from '@/components/documents/StreamingDocumentUpload'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export default function TestUploadPage() {
  const handleUploadComplete = (successCount: number, totalCount: number) => {
    console.log(`Upload test completed: ${successCount}/${totalCount} files processed successfully`)
  }

  const handleUploadError = (error: string) => {
    console.error('Upload test error:', error)
  }

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="container mx-auto max-w-6xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🚀 Upload System Test - Real-Time Progress
          </h1>
          <p className="text-gray-600">
            Testing the streaming upload system with real-time progress updates
          </p>
        </div>
        
        <Card>
          <CardHeader>
            <CardTitle>🚀 Real-Time Streaming Upload</CardTitle>
            <p className="text-muted-foreground">
              Upload files and folders with real-time progress tracking. Perfect for testing with your nested folder structure!
            </p>
          </CardHeader>
          <CardContent>
            <StreamingDocumentUpload
              collectionId={2}
              onUploadComplete={handleUploadComplete}
              onUploadError={handleUploadError}
              onClose={() => {}}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}