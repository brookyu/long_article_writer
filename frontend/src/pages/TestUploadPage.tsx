/**
 * Test Upload Page
 * Testing both simple and streaming upload systems
 */

import React from 'react'
import SimpleUploadTest from '@/components/documents/SimpleUploadTest'
import { StreamingUploadTest } from '@/components/documents/StreamingUploadTest'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function TestUploadPage() {
  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="container mx-auto max-w-6xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🚀 Upload System Test - Real-Time Progress
          </h1>
          <p className="text-gray-600">
            Testing both simple and streaming upload systems with real-time progress updates
          </p>
        </div>
        
        <Tabs defaultValue="streaming" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="streaming">🔥 NEW: Streaming Upload</TabsTrigger>
            <TabsTrigger value="simple">📁 Simple Upload</TabsTrigger>
          </TabsList>
          
          <TabsContent value="streaming" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>🚀 Real-Time Streaming Upload</CardTitle>
                <p className="text-muted-foreground">
                  This is the new system with real-time progress updates! Perfect for your 70-file folder.
                </p>
              </CardHeader>
              <CardContent>
                <StreamingUploadTest collectionId={2} />
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="simple" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>📁 Simple Upload (No Progress)</CardTitle>
                <p className="text-muted-foreground">
                  The basic upload without real-time updates (for comparison).
                </p>
              </CardHeader>
              <CardContent>
                <SimpleUploadTest />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}