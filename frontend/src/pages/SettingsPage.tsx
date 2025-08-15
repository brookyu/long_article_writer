import { useState } from 'react'
import { Link } from 'react-router-dom'
import { SettingsForm } from '@/components/settings/SettingsForm'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'

export function SettingsPage() {
  const [saveSuccess, setSaveSuccess] = useState(false)

  const handleSave = () => {
    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 3000)
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <div className="border-b bg-card">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Button asChild variant="ghost" size="sm">
                <Link to="/">
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Back to Home
                </Link>
              </Button>
            </div>

            {saveSuccess && (
              <div className="text-sm text-green-600 font-medium">
                ✓ Settings saved successfully
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <SettingsForm onSave={handleSave} />
        </div>
      </div>
    </div>
  )
}