/**
 * Simple Upload Test Component
 * Tests the new Open WebUI-inspired simplified upload system
 */

import React, { useState } from 'react'
import { folderUploadApi } from '@/lib/api'

interface UploadResult {
  success: boolean
  message: string
  summary?: {
    total: number
    successful: number
    failed: number
    skipped: number
  }
  results?: Array<{
    success: boolean
    filename: string
    error?: string
    skipped?: boolean
    reason?: string
  }>
}

export default function SimpleUploadTest() {
  const [collectionId, setCollectionId] = useState<number>(2) // Default to collection 2
  const [isUploading, setIsUploading] = useState(false)
  const [result, setResult] = useState<UploadResult | null>(null)

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    setIsUploading(true)
    setResult(null)

    try {
      console.log(`🚀 Testing simplified upload with ${files.length} files...`)
      
      const uploadResult = await folderUploadApi.uploadSimple(collectionId, files)
      
      console.log('✅ Upload completed:', uploadResult)
      setResult(uploadResult)
      
    } catch (error) {
      console.error('❌ Upload failed:', error)
      setResult({
        success: false,
        message: error instanceof Error ? error.message : 'Upload failed'
      })
    } finally {
      setIsUploading(false)
    }
  }

  const handleFolderUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    setResult(null)

    try {
      console.log('🚀 Testing simplified folder upload...')
      
      const uploadResult = await folderUploadApi.uploadFolderSimple(collectionId, file)
      
      console.log('✅ Folder upload completed:', uploadResult)
      setResult(uploadResult)
      
    } catch (error) {
      console.error('❌ Folder upload failed:', error)
      setResult({
        success: false,
        message: error instanceof Error ? error.message : 'Folder upload failed'
      })
    } finally {
      setIsUploading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">
        🧪 Simple Upload Test (Open WebUI Inspired)
      </h2>
      
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Collection ID:
        </label>
        <input
          type="number"
          value={collectionId}
          onChange={(e) => setCollectionId(parseInt(e.target.value))}
          className="border border-gray-300 rounded-md px-3 py-2 w-32"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Individual Files Upload */}
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3">📄 Upload Files</h3>
          <input
            type="file"
            multiple
            onChange={handleFileUpload}
            disabled={isUploading}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <p className="text-sm text-gray-500 mt-2">
            Select multiple files to test direct processing
          </p>
        </div>

        {/* Folder Upload */}
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold mb-3">📁 Upload Folder (ZIP)</h3>
          <input
            type="file"
            accept=".zip"
            onChange={handleFolderUpload}
            disabled={isUploading}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100"
          />
          <p className="text-sm text-gray-500 mt-2">
            Select a ZIP file to test folder processing
          </p>
        </div>
      </div>

      {/* Loading State */}
      {isUploading && (
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center">
            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-3"></div>
            <span className="text-blue-800">Processing files using simplified approach...</span>
          </div>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className={`p-4 rounded-lg ${
          result.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}>
          <h3 className="text-lg font-semibold mb-3">
            {result.success ? '✅ Upload Results' : '❌ Upload Failed'}
          </h3>
          
          <div className="mb-3">
            <p className="text-sm font-medium">{result.message}</p>
          </div>

          {result.summary && (
            <div className="mb-4 p-3 bg-white rounded border">
              <h4 className="font-medium mb-2">📊 Summary:</h4>
              <div className="grid grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Total:</span>
                  <span className="ml-1 font-semibold">{result.summary.total}</span>
                </div>
                <div>
                  <span className="text-green-600">Successful:</span>
                  <span className="ml-1 font-semibold">{result.summary.successful}</span>
                </div>
                <div>
                  <span className="text-red-600">Failed:</span>
                  <span className="ml-1 font-semibold">{result.summary.failed}</span>
                </div>
                <div>
                  <span className="text-yellow-600">Skipped:</span>
                  <span className="ml-1 font-semibold">{result.summary.skipped}</span>
                </div>
              </div>
            </div>
          )}

          {result.results && result.results.length > 0 && (
            <div>
              <h4 className="font-medium mb-2">📋 File Details:</h4>
              <div className="max-h-60 overflow-y-auto">
                {result.results.map((fileResult, index) => (
                  <div
                    key={index}
                    className={`p-2 mb-2 rounded text-sm ${
                      fileResult.success
                        ? fileResult.skipped
                          ? 'bg-yellow-100 text-yellow-800'
                          : 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}
                  >
                    <div className="font-medium">{fileResult.filename}</div>
                    {fileResult.skipped && fileResult.reason && (
                      <div className="text-xs mt-1">Skipped: {fileResult.reason}</div>
                    )}
                    {fileResult.error && (
                      <div className="text-xs mt-1">Error: {fileResult.error}</div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="mt-6 p-4 bg-gray-50 rounded-lg">
        <h3 className="font-semibold mb-2">🎯 What This Tests:</h3>
        <ul className="text-sm text-gray-700 space-y-1">
          <li>• <strong>Apache Tika</strong> document extraction</li>
          <li>• <strong>Direct processing</strong> without job queues</li>
          <li>• <strong>Database transaction fixes</strong></li>
          <li>• <strong>Immediate feedback</strong> to users</li>
          <li>• <strong>Robust error handling</strong></li>
        </ul>
      </div>
    </div>
  )
}