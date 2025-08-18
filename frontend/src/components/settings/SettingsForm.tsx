import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Settings, Server, Brain, Globe, Save, TestTube, Palette } from 'lucide-react'
import { settingsApi } from '@/lib/api'

interface SettingsFormProps {
  onSave?: () => void
}

interface LLMSettings {
  provider: 'ollama' | 'openai' | 'anthropic'
  model: string
  apiKey?: string
  baseUrl?: string
  temperature?: number
  maxTokens?: number
}

interface EmbeddingSettings {
  provider: 'ollama' | 'openai'
  model: string
  apiKey?: string
  baseUrl?: string
}

interface SearchSettings {
  provider: 'searxng' | 'google' | 'bing' | 'duckduckgo'
  apiKey?: string
  baseUrl?: string
  enabled: boolean
}

interface UISettings {
  language: 'en' | 'zh'
  theme: 'light' | 'dark'
}

export function SettingsForm({ onSave }: SettingsFormProps) {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState<'llm' | 'embedding' | 'search' | 'ui'>('llm')
  const [llmSettings, setLlmSettings] = useState<LLMSettings>({
    provider: 'ollama',
    model: 'mixtral:latest',
    baseUrl: 'http://localhost:11434',
    temperature: 0.7,
    maxTokens: 2000
  })
  const [ollamaModels, setOllamaModels] = useState<Array<{name: string, size: number, parameter_size: string, family: string}>>([])
  const [loadingModels, setLoadingModels] = useState(false)

  const [embeddingSettings, setEmbeddingSettings] = useState<EmbeddingSettings>({
    provider: 'ollama',
    model: 'nomic-embed-text',
    baseUrl: 'http://localhost:11434'
  })

  const [searchSettings, setSearchSettings] = useState<SearchSettings>({
    provider: 'duckduckgo',
    baseUrl: '',
    enabled: true
  })

  const [uiSettings, setUiSettings] = useState<UISettings>({
    language: 'en',
    theme: 'light'
  })

  const [isLoading, setIsLoading] = useState(false)
  const [testResults, setTestResults] = useState<Record<string, 'success' | 'error' | 'testing'>>({})

  // Load Ollama models
  const loadOllamaModels = async () => {
    if (loadingModels) return
    setLoadingModels(true)
    try {
      const response = await settingsApi.listOllamaModels()
      if (response.status === 'success') {
        setOllamaModels(response.models)
      }
    } catch (error) {
      console.error('Failed to load Ollama models:', error)
      // Set fallback models if API fails
      setOllamaModels([
        { name: 'gpt-oss:20b', size: 0, parameter_size: '20.9B', family: 'gptoss' },
        { name: 'nomic-embed-text:latest', size: 0, parameter_size: '137M', family: 'nomic-bert' },
        { name: 'mixtral:latest', size: 0, parameter_size: '46.7B', family: 'llama' }
      ])
    } finally {
      setLoadingModels(false)
    }
  }

  // Load settings from backend on component mount
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await fetch('/api/settings/config')
        if (response.ok) {
          const data = await response.json()
          
          // Update state with loaded settings
          setLlmSettings({
            provider: data.llm_settings.provider || 'ollama',
            model: data.llm_settings.model || 'mixtral:latest',
            baseUrl: data.llm_settings.baseUrl || 'http://localhost:11434',
            temperature: data.llm_settings.temperature || 0.7,
            maxTokens: data.llm_settings.maxTokens || 2000,
            ...(data.llm_settings.apiKey && { apiKey: data.llm_settings.apiKey })
          })
          
          setEmbeddingSettings({
            provider: data.embedding_settings.provider || 'ollama',
            model: data.embedding_settings.model || 'nomic-embed-text',
            baseUrl: data.embedding_settings.baseUrl || 'http://localhost:11434',
            ...(data.embedding_settings.apiKey && { apiKey: data.embedding_settings.apiKey })
          })
          
          setSearchSettings({
            provider: data.search_settings.provider || 'duckduckgo',
            baseUrl: data.search_settings.baseUrl || '',
            enabled: data.search_settings.enabled !== false,
            ...(data.search_settings.apiKey && { apiKey: data.search_settings.apiKey })
          })

          setUiSettings({
            language: data.ui_settings?.language || 'en',
            theme: data.ui_settings?.theme || 'light'
          })
        }
      } catch (error) {
        console.error('Failed to load settings:', error)
        // Fall back to DuckDuckGo default
        setSearchSettings({
          provider: 'duckduckgo',
          baseUrl: '',
          enabled: true
        })
      }
    }
    
    loadSettings()
    loadOllamaModels()  // Load available Ollama models
  }, [])

  const handleSave = async () => {
    setIsLoading(true)
    try {
      const response = await fetch('/api/settings/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          llm_settings: llmSettings,
          embedding_settings: embeddingSettings,
          search_settings: searchSettings,
          ui_settings: uiSettings
        })
      })
      
      if (!response.ok) {
        throw new Error(`Failed to save settings: ${response.status}`)
      }
      
      const result = await response.json()
      console.log('Settings saved successfully:', result.message)
      
      onSave?.()
    } catch (error) {
      console.error('Failed to save settings:', error)
      alert('Failed to save settings. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const testConnection = async (type: 'llm' | 'embedding' | 'search') => {
    setTestResults(prev => ({ ...prev, [type]: 'testing' }))
    
    try {
      let response: Response
      
      if (type === 'llm') {
        // Test LLM connection
        response = await fetch('/api/settings/test-llm', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: llmSettings.provider,
            model: llmSettings.model,
            api_key: llmSettings.apiKey,
            base_url: llmSettings.baseUrl
          })
        })
      } else if (type === 'embedding') {
        // Test embedding connection
        response = await fetch('/api/settings/test-embedding', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: embeddingSettings.provider,
            model: embeddingSettings.model,
            api_key: embeddingSettings.apiKey,
            base_url: embeddingSettings.baseUrl
          })
        })
      } else {
        // Test search connection
        response = await fetch('/api/settings/test-search', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider: searchSettings.provider,
            api_key: searchSettings.apiKey,
            base_url: searchSettings.baseUrl
          })
        })
      }
      
      if (response.ok) {
        setTestResults(prev => ({ ...prev, [type]: 'success' }))
      } else {
        const error = await response.json()
        console.error(`${type} test failed:`, error)
        setTestResults(prev => ({ ...prev, [type]: 'error' }))
      }
    } catch (error) {
      console.error(`${type} test error:`, error)
      setTestResults(prev => ({ ...prev, [type]: 'error' }))
    }
  }

  const getStatusBadge = (type: string) => {
    const status = testResults[type]
    if (status === 'testing') return <Badge variant="secondary">Testing...</Badge>
    if (status === 'success') return <Badge variant="default" className="bg-green-500">Connected</Badge>
    if (status === 'error') return <Badge variant="destructive">Failed</Badge>
    return <Badge variant="outline">Not tested</Badge>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Settings className="w-6 h-6 text-primary" />
        <div>
          <h2 className="text-2xl font-bold">Settings</h2>
          <p className="text-muted-foreground">Configure AI providers and services</p>
        </div>
      </div>

      <div className="space-y-4">
        <div className="flex space-x-1 rounded-lg bg-muted p-1">
          <Button
            variant={activeTab === 'llm' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('llm')}
            className="flex items-center gap-2"
          >
            <Brain className="w-4 h-4" />
            LLM Provider
          </Button>
          <Button
            variant={activeTab === 'embedding' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('embedding')}
            className="flex items-center gap-2"
          >
            <Server className="w-4 h-4" />
            Embeddings
          </Button>
          <Button
            variant={activeTab === 'search' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('search')}
            className="flex items-center gap-2"
          >
            <Globe className="w-4 h-4" />
            {t('settings.tabs.search')}
          </Button>
          <Button
            variant={activeTab === 'ui' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('ui')}
            className="flex items-center gap-2"
          >
            <Palette className="w-4 h-4" />
            {t('settings.tabs.ui')}
          </Button>
        </div>

        {activeTab === 'llm' && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>LLM Configuration</CardTitle>
                  <CardDescription>
                    Configure your language model for article generation
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge('llm')}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => testConnection('llm')}
                    disabled={testResults.llm === 'testing'}
                  >
                    <TestTube className="w-4 h-4 mr-2" />
                    Test
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Provider</Label>
                <select
                  value={llmSettings.provider}
                  onChange={(e) => {
                    const provider = e.target.value as 'ollama' | 'openai' | 'anthropic'
                    const defaultModels = {
                      ollama: 'mixtral:latest',
                      openai: 'gpt-4',
                      anthropic: 'claude-3-5-sonnet-20241022'
                    }
                    setLlmSettings(prev => ({ 
                      ...prev, 
                      provider,
                      model: defaultModels[provider]
                    }))
                  }}
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                >
                  <option value="ollama">Ollama (Local)</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                </select>
              </div>

              <div>
                <Label className="flex items-center justify-between">
                  Model
                  {llmSettings.provider === 'ollama' && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={loadOllamaModels}
                      disabled={loadingModels}
                      className="ml-2 h-6 text-xs"
                    >
                      {loadingModels ? 'Loading...' : 'Refresh'}
                    </Button>
                  )}
                </Label>
                <select
                  value={llmSettings.model}
                  onChange={(e) => setLlmSettings(prev => ({ ...prev, model: e.target.value }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                  disabled={llmSettings.provider === 'ollama' && loadingModels}
                >
                  {llmSettings.provider === 'ollama' && (
                    <>
                      {loadingModels ? (
                        <option value="">Loading models...</option>
                      ) : ollamaModels.length > 0 ? (
                        ollamaModels.map((model) => (
                          <option key={model.name} value={model.name}>
                            {model.name} ({model.parameter_size})
                          </option>
                        ))
                      ) : (
                        <option value="">No models available</option>
                      )}
                    </>
                  )}
                  {llmSettings.provider === 'openai' && (
                    <>
                      <option value="gpt-4">gpt-4</option>
                      <option value="gpt-4-turbo">gpt-4-turbo</option>
                      <option value="gpt-3.5-turbo">gpt-3.5-turbo</option>
                      <option value="gpt-4o">gpt-4o</option>
                      <option value="gpt-4o-mini">gpt-4o-mini</option>
                    </>
                  )}
                  {llmSettings.provider === 'anthropic' && (
                    <>
                      <option value="claude-3-5-sonnet-20241022">claude-3.5-sonnet</option>
                      <option value="claude-3-opus-20240229">claude-3-opus</option>
                      <option value="claude-3-haiku-20240307">claude-3-haiku</option>
                    </>
                  )}
                </select>
              </div>

              {llmSettings.provider !== 'ollama' && (
                <div>
                  <Label>API Key</Label>
                  <Input
                    type="password"
                    value={llmSettings.apiKey || ''}
                    onChange={(e) => setLlmSettings(prev => ({ ...prev, apiKey: e.target.value }))}
                    placeholder="Enter your API key"
                  />
                </div>
              )}

              <div>
                <Label>Base URL</Label>
                <Input
                  value={llmSettings.baseUrl || ''}
                  onChange={(e) => setLlmSettings(prev => ({ ...prev, baseUrl: e.target.value }))}
                  placeholder="e.g., http://localhost:11434"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Temperature</Label>
                  <Input
                    type="number"
                    min="0"
                    max="2"
                    step="0.1"
                    value={llmSettings.temperature || 0.7}
                    onChange={(e) => setLlmSettings(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
                  />
                </div>
                <div>
                  <Label>Max Tokens</Label>
                  <Input
                    type="number"
                    min="100"
                    max="4000"
                    value={llmSettings.maxTokens || 2000}
                    onChange={(e) => setLlmSettings(prev => ({ ...prev, maxTokens: parseInt(e.target.value) }))}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === 'embedding' && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Embedding Configuration</CardTitle>
                  <CardDescription>
                    Configure embeddings for knowledge base search
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge('embedding')}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => testConnection('embedding')}
                    disabled={testResults.embedding === 'testing'}
                  >
                    <TestTube className="w-4 h-4 mr-2" />
                    Test
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>Provider</Label>
                <select
                  value={embeddingSettings.provider}
                  onChange={(e) => {
                    const provider = e.target.value as 'ollama' | 'openai'
                    const defaultModels = {
                      ollama: 'nomic-embed-text',
                      openai: 'text-embedding-3-large'
                    }
                    setEmbeddingSettings(prev => ({ 
                      ...prev, 
                      provider,
                      model: defaultModels[provider]
                    }))
                  }}
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                >
                  <option value="ollama">Ollama (Local)</option>
                  <option value="openai">OpenAI</option>
                </select>
              </div>

              <div>
                <Label className="flex items-center justify-between">
                  Model
                  {embeddingSettings.provider === 'ollama' && (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={loadOllamaModels}
                      disabled={loadingModels}
                      className="ml-2 h-6 text-xs"
                    >
                      {loadingModels ? 'Loading...' : 'Refresh'}
                    </Button>
                  )}
                </Label>
                <select
                  value={embeddingSettings.model}
                  onChange={(e) => setEmbeddingSettings(prev => ({ ...prev, model: e.target.value }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                  disabled={embeddingSettings.provider === 'ollama' && loadingModels}
                >
                  {embeddingSettings.provider === 'ollama' && (
                    <>
                      {loadingModels ? (
                        <option value="">Loading models...</option>
                      ) : ollamaModels.length > 0 ? (
                        ollamaModels
                          .filter(model => model.family === 'nomic-bert' || model.name.includes('embed'))
                          .map((model) => (
                            <option key={model.name} value={model.name}>
                              {model.name} ({model.parameter_size})
                            </option>
                          ))
                      ) : (
                        <option value="">No embedding models available</option>
                      )}
                    </>
                  )}
                  {embeddingSettings.provider === 'openai' && (
                    <>
                      <option value="text-embedding-3-large">text-embedding-3-large</option>
                      <option value="text-embedding-3-small">text-embedding-3-small</option>
                      <option value="text-embedding-ada-002">text-embedding-ada-002</option>
                    </>
                  )}
                </select>
              </div>

              {embeddingSettings.provider !== 'ollama' && (
                <div>
                  <Label>API Key</Label>
                  <Input
                    type="password"
                    value={embeddingSettings.apiKey || ''}
                    onChange={(e) => setEmbeddingSettings(prev => ({ ...prev, apiKey: e.target.value }))}
                    placeholder="Enter your API key"
                  />
                </div>
              )}

              <div>
                <Label>Base URL</Label>
                <Input
                  value={embeddingSettings.baseUrl || ''}
                  onChange={(e) => setEmbeddingSettings(prev => ({ ...prev, baseUrl: e.target.value }))}
                  placeholder="e.g., http://localhost:11434"
                />
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === 'search' && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>Web Search Configuration</CardTitle>
                  <CardDescription>
                    Configure web search for supplementary research
                  </CardDescription>
                </div>
                <div className="flex items-center gap-2">
                  {getStatusBadge('search')}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => testConnection('search')}
                    disabled={testResults.search === 'testing'}
                  >
                    <TestTube className="w-4 h-4 mr-2" />
                    Test
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="search-enabled"
                  checked={searchSettings.enabled}
                  onChange={(e) => setSearchSettings(prev => ({ ...prev, enabled: e.target.checked }))}
                />
                <Label htmlFor="search-enabled">Enable web search fallback</Label>
              </div>

              <div>
                <Label>Provider</Label>
                <select
                  key="search-provider-select"
                  value={searchSettings.provider}
                  onChange={(e) => setSearchSettings(prev => ({ ...prev, provider: e.target.value as any }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                  disabled={!searchSettings.enabled}
                >
                  <option value="duckduckgo">DuckDuckGo (Free)</option>
                  <option value="searxng">SearXNG (Self-hosted)</option>
                  <option value="google">Google Search API</option>
                  <option value="bing">Bing Search API</option>
                </select>
              </div>

              <div>
                <Label>Base URL</Label>
                <Input
                  value={searchSettings.baseUrl || ''}
                  onChange={(e) => setSearchSettings(prev => ({ ...prev, baseUrl: e.target.value }))}
                  placeholder="e.g., http://localhost:8080"
                  disabled={!searchSettings.enabled}
                />
              </div>

              {searchSettings.provider !== 'searxng' && (
                <div>
                  <Label>API Key</Label>
                  <Input
                    type="password"
                    value={searchSettings.apiKey || ''}
                    onChange={(e) => setSearchSettings(prev => ({ ...prev, apiKey: e.target.value }))}
                    placeholder="Enter your API key"
                    disabled={!searchSettings.enabled}
                  />
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === 'ui' && (
          <Card>
            <CardHeader>
              <div>
                <CardTitle>{t('settings.ui.title')}</CardTitle>
                <CardDescription>
                  {t('settings.ui.description')}
                </CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>{t('settings.ui.language')}</Label>
                <select
                  value={uiSettings.language}
                  onChange={(e) => setUiSettings(prev => ({ ...prev, language: e.target.value as 'en' | 'zh' }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                >
                  <option value="en">English</option>
                  <option value="zh">中文 (Chinese)</option>
                </select>
              </div>

              <div>
                <Label>{t('settings.ui.theme')}</Label>
                <select
                  value={uiSettings.theme}
                  onChange={(e) => setUiSettings(prev => ({ ...prev, theme: e.target.value as 'light' | 'dark' }))}
                  className="w-full mt-1 px-3 py-2 border rounded-md"
                >
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                </select>
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      <div className="flex justify-end">
        <Button onClick={handleSave} disabled={isLoading}>
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              Save Settings
            </>
          )}
        </Button>
      </div>
    </div>
  )
}