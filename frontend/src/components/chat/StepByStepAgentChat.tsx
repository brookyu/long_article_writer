import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { 
  CheckCircle2, 
  AlertCircle, 
  MessageSquare, 
  Edit3, 
  ArrowRight,
  Download,
  RefreshCw,
  FileText,
  Target,
  Play,
  SkipForward
} from 'lucide-react';

interface StepByStepAgentChatProps {
  collectionId: number;
}

interface WorkflowState {
  phase: 'setup' | 'research' | 'outline' | 'section-generation' | 'section-refinement' | 'final-review' | 'completed';
  sessionId?: string;
  topic: string;
  outline?: any;
  sectionOrder: string[];
  currentSectionIndex: number;
  currentSectionId?: string;
  sections: Record<string, any>;
  finalArticle?: string;
  inRefinementMode: boolean;
  inFinalRefinementMode: boolean;
}

export function StepByStepAgentChat({ collectionId }: StepByStepAgentChatProps) {
  const { t } = useTranslation();
  
  // Workflow state
  const [workflow, setWorkflow] = useState<WorkflowState>({
    phase: 'setup',
    topic: '',
    sectionOrder: [],
    currentSectionIndex: 0,
    sections: {},
    inRefinementMode: false,
    inFinalRefinementMode: false
  });
  
  // Form inputs
  const [articleType, setArticleType] = useState('comprehensive');
  const [targetLength, setTargetLength] = useState('medium');
  const [writingStyle, setWritingStyle] = useState('professional');
  
  // Current section content and feedback
  const [currentSectionContent, setCurrentSectionContent] = useState('');
  const [feedbackText, setFeedbackText] = useState('');
  const [finalArticleText, setFinalArticleText] = useState('');
  
  // UI state
  const [isProcessing, setIsProcessing] = useState(false);
  const [messages, setMessages] = useState<Array<{
    type: string;
    content: string;
    timestamp: Date;
  }>>([]);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const addMessage = (type: string, content: string) => {
    setMessages(prev => [...prev, {
      type,
      content,
      timestamp: new Date()
    }]);
  };
  
  // Step 1: Start Generation
  const startGeneration = async () => {
    if (!workflow.topic.trim()) {
      addMessage('error', 'Please enter a topic for your article');
      return;
    }
    
    setIsProcessing(true);
    addMessage('system', `Starting step-by-step article generation for: "${workflow.topic}"`);
    
    try {
      // Start generation session
      const startResponse = await fetch(`/api/enhanced-agents/${collectionId}/start-generation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: workflow.topic,
          article_type: articleType,
          target_length: targetLength,
          writing_style: writingStyle
        })
      });
      
      const startResult = await startResponse.json();
      
      if (startResult.status === 'success') {
        setWorkflow(prev => ({ 
          ...prev, 
          sessionId: startResult.session_id,
          phase: 'research'
        }));
        
        addMessage('success', 'Generation session started');
        
        // Process research
        await processResearch(startResult.session_id);
        
      } else {
        addMessage('error', `Failed to start generation: ${startResult.message}`);
      }
    } catch (error) {
      console.error('Generation start failed:', error);
      addMessage('error', `Failed to start generation: ${error}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Step 2: Research
  const processResearch = async (sessionId: string) => {
    addMessage('system', 'Processing research phase...');
    
    try {
      const researchResponse = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${sessionId}/research`, {
        method: 'POST'
      });
      
      const researchResult = await researchResponse.json();
      
      if (researchResult.status === 'success') {
        addMessage('success', `Research completed: ${researchResult.data?.data?.total_sources || 0} sources found`);
        setWorkflow(prev => ({ ...prev, phase: 'outline' }));
        
        // Generate outline
        await generateOutline(sessionId);
      } else {
        addMessage('error', 'Research phase failed');
      }
    } catch (error) {
      console.error('Research failed:', error);
      addMessage('error', `Research failed: ${error}`);
    }
  };
  
  // Step 3: Generate Outline
  const generateOutline = async (sessionId: string) => {
    addMessage('system', 'Generating article outline...');
    
    try {
      const outlineResponse = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${sessionId}/outline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ research_feedback: '' })
      });
      
      const outlineResult = await outlineResponse.json();
      
      if (outlineResult.status === 'success') {
        setWorkflow(prev => ({
          ...prev,
          outline: outlineResult.outline,
          sectionOrder: outlineResult.section_order || [],
          currentSectionIndex: 0,
          currentSectionId: outlineResult.section_order?.[0],
          phase: 'section-generation'
        }));
        
        addMessage('success', `Outline generated with ${outlineResult.total_sections} sections`);
        addMessage('info', 'Ready to generate first section');
        
      } else {
        addMessage('error', 'Outline generation failed');
      }
    } catch (error) {
      console.error('Outline generation failed:', error);
      addMessage('error', `Outline generation failed: ${error}`);
    }
  };
  
  // Step 4: Generate Current Section
  const generateCurrentSection = async () => {
    if (!workflow.sessionId || !workflow.currentSectionId) return;
    
    setIsProcessing(true);
    const sectionTitle = getCurrentSectionTitle();
    addMessage('system', `Generating section: ${sectionTitle}`);
    
    try {
      const sectionResponse = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${workflow.sessionId}/sections/${workflow.currentSectionId}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_feedback: '' })
      });
      
      const sectionResult = await sectionResponse.json();
      
      if (sectionResult.status === 'success') {
        const sectionContent = sectionResult.section_content;
        setCurrentSectionContent(sectionContent.content);
        setWorkflow(prev => ({
          ...prev,
          sections: { ...prev.sections, [workflow.currentSectionId!]: sectionContent },
          phase: 'section-refinement',
          inRefinementMode: true
        }));
        
        addMessage('success', `Section "${sectionTitle}" generated (${sectionContent.word_count} words)`);
        addMessage('info', 'Review the section and provide feedback, or click "Move On" to proceed');
        
      } else {
        addMessage('error', `Section generation failed: ${sectionResult.message}`);
      }
    } catch (error) {
      console.error('Section generation failed:', error);
      addMessage('error', `Section generation failed: ${error}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Step 5: Refine Current Section
  const refineCurrentSection = async () => {
    if (!workflow.sessionId || !workflow.currentSectionId || !feedbackText.trim()) return;
    
    setIsProcessing(true);
    addMessage('system', 'Refining section based on feedback...');
    
    try {
      const feedbackResponse = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${workflow.sessionId}/sections/${workflow.currentSectionId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feedback_type: 'request_changes',
          feedback_text: feedbackText,
          specific_changes: feedbackText
        })
      });
      
      const feedbackResult = await feedbackResponse.json();
      
      if (feedbackResult.status === 'success') {
        const refinedContent = feedbackResult.feedback_result.refined_content;
        setCurrentSectionContent(refinedContent);
        setWorkflow(prev => ({
          ...prev,
          sections: { 
            ...prev.sections, 
            [workflow.currentSectionId!]: { 
              ...prev.sections[workflow.currentSectionId!], 
              content: refinedContent 
            }
          }
        }));
        
        addMessage('success', 'Section refined based on feedback');
        setFeedbackText('');
        
      } else {
        addMessage('error', 'Section refinement failed');
      }
    } catch (error) {
      console.error('Section refinement failed:', error);
      addMessage('error', `Section refinement failed: ${error}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Step 6: Move to Next Section
  const moveToNextSection = async () => {
    if (!workflow.sessionId) return;
    
    setIsProcessing(true);
    addMessage('system', 'Moving to next section...');
    
    try {
      const moveResponse = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${workflow.sessionId}/move-to-next`, {
        method: 'POST'
      });
      
      const moveResult = await moveResponse.json();
      
      if (moveResult.status === 'success') {
        const result = moveResult.move_result;
        
        if (result.status === 'moved_to_next') {
          // Move to next section
          setWorkflow(prev => ({
            ...prev,
            currentSectionIndex: prev.currentSectionIndex + 1,
            currentSectionId: result.next_section_id,
            phase: 'section-generation',
            inRefinementMode: false
          }));
          
          setCurrentSectionContent('');
          setFeedbackText('');
          addMessage('success', `Moved to section ${result.section_index}/${result.total_sections}`);
          
        } else if (result.status === 'all_sections_complete') {
          // All sections done, move to final review
          setWorkflow(prev => ({
            ...prev,
            phase: 'final-review',
            inRefinementMode: false,
            inFinalRefinementMode: true,
            finalArticle: result.final_article
          }));
          
          setFinalArticleText(result.final_article);
          addMessage('success', `All sections complete! Final article ready for review (${result.total_words} words)`);
        }
        
      } else {
        addMessage('error', 'Failed to move to next section');
      }
    } catch (error) {
      console.error('Move to next failed:', error);
      addMessage('error', `Move to next failed: ${error}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Step 7: Refine Final Article
  const refineFinalArticle = async () => {
    if (!workflow.sessionId || !feedbackText.trim()) return;
    
    setIsProcessing(true);
    addMessage('system', 'Refining final article...');
    
    try {
      const refineResponse = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${workflow.sessionId}/refine-final`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feedback: feedbackText })
      });
      
      const refineResult = await refineResponse.json();
      
      if (refineResult.status === 'success') {
        const refinedArticle = refineResult.refinement_result.final_article;
        setFinalArticleText(refinedArticle);
        setWorkflow(prev => ({
          ...prev,
          finalArticle: refinedArticle
        }));
        
        addMessage('success', 'Final article refined based on feedback');
        setFeedbackText('');
        
      } else {
        addMessage('error', 'Final article refinement failed');
      }
    } catch (error) {
      console.error('Final refinement failed:', error);
      addMessage('error', `Final refinement failed: ${error}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Step 8: Complete Article
  const completeArticle = async () => {
    if (!workflow.sessionId) return;
    
    setIsProcessing(true);
    addMessage('system', 'Finalizing article...');
    
    try {
      const completeResponse = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${workflow.sessionId}/complete`, {
        method: 'POST'
      });
      
      const completeResult = await completeResponse.json();
      
      if (completeResult.status === 'success') {
        setWorkflow(prev => ({
          ...prev,
          phase: 'completed',
          inFinalRefinementMode: false
        }));
        
        addMessage('success', 'Article completed successfully! Ready for download.');
        
      } else {
        addMessage('error', 'Article completion failed');
      }
    } catch (error) {
      console.error('Article completion failed:', error);
      addMessage('error', `Article completion failed: ${error}`);
    } finally {
      setIsProcessing(false);
    }
  };
  
  // Download Article
  const downloadArticle = async () => {
    if (!workflow.sessionId) return;
    
    try {
      const response = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${workflow.sessionId}/download`);
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${workflow.topic.replace(/[^a-zA-Z0-9]/g, '_')}.md`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        addMessage('success', 'Article downloaded successfully!');
      } else {
        addMessage('error', 'Download failed');
      }
    } catch (error) {
      console.error('Download failed:', error);
      addMessage('error', `Download failed: ${error}`);
    }
  };
  
  const resetWorkflow = () => {
    setWorkflow({
      phase: 'setup',
      topic: '',
      sectionOrder: [],
      currentSectionIndex: 0,
      sections: {},
      inRefinementMode: false,
      inFinalRefinementMode: false
    });
    setCurrentSectionContent('');
    setFeedbackText('');
    setFinalArticleText('');
    setMessages([]);
  };
  
  const getCurrentSectionTitle = () => {
    if (!workflow.outline?.outline?.sections || !workflow.currentSectionId) return 'Unknown Section';
    const section = workflow.outline.outline.sections.find((s: any) => s.id === workflow.currentSectionId);
    return section?.title || 'Unknown Section';
  };
  
  const getProgressPercentage = () => {
    if (workflow.phase === 'setup') return 0;
    if (workflow.phase === 'research') return 10;
    if (workflow.phase === 'outline') return 20;
    if (workflow.phase === 'section-generation' || workflow.phase === 'section-refinement') {
      const baseProgress = 30;
      const sectionProgress = workflow.sectionOrder.length > 0 
        ? (workflow.currentSectionIndex / workflow.sectionOrder.length) * 60
        : 0;
      return baseProgress + sectionProgress;
    }
    if (workflow.phase === 'final-review') return 90;
    if (workflow.phase === 'completed') return 100;
    return 0;
  };
  
  return (
    <div className="flex flex-col h-full max-h-screen">
      {/* Header with Progress */}
      <div className="border-b p-4 bg-white">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Step-by-Step Article Generation</h2>
          {workflow.sessionId && (
            <Badge variant="outline" className="text-sm">
              Session: {workflow.sessionId.slice(-8)}
            </Badge>
          )}
        </div>
        
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600">
            <span>{workflow.phase.replace('-', ' ').toUpperCase()}</span>
            <span>{Math.round(getProgressPercentage())}%</span>
          </div>
          <Progress value={getProgressPercentage()} className="w-full" />
          {workflow.sectionOrder.length > 0 && (workflow.phase === 'section-generation' || workflow.phase === 'section-refinement') && (
            <div className="text-sm text-gray-600">
              Section {workflow.currentSectionIndex + 1} of {workflow.sectionOrder.length}: {getCurrentSectionTitle()}
            </div>
          )}
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Current Step */}
        <div className="w-2/3 border-r flex flex-col">
          <div className="p-4 border-b bg-gray-50">
            <h3 className="font-semibold mb-2">Current Step</h3>
            <div className="text-sm text-gray-600">
              {workflow.phase === 'setup' && 'Configure your article and start generation'}
              {workflow.phase === 'research' && 'Gathering relevant information...'}
              {workflow.phase === 'outline' && 'Creating article structure...'}
              {workflow.phase === 'section-generation' && 'Generating section content'}
              {workflow.phase === 'section-refinement' && 'Refining section content'}
              {workflow.phase === 'final-review' && 'Reviewing complete article'}
              {workflow.phase === 'completed' && 'Article ready for download'}
            </div>
          </div>
          
          <div className="flex-1 p-4 overflow-y-auto">
            {/* Setup Phase */}
            {workflow.phase === 'setup' && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Target className="h-5 w-5" />
                    Article Configuration
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Topic</label>
                    <Textarea
                      value={workflow.topic}
                      onChange={(e) => setWorkflow(prev => ({ ...prev, topic: e.target.value }))}
                      placeholder="Enter your article topic..."
                      className="min-h-[80px]"
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Type</label>
                      <select
                        value={articleType}
                        onChange={(e) => setArticleType(e.target.value)}
                        className="w-full p-2 border rounded-md"
                      >
                        <option value="comprehensive">Comprehensive</option>
                        <option value="tutorial">Tutorial</option>
                        <option value="analysis">Analysis</option>
                        <option value="overview">Overview</option>
                      </select>
                    </div>
                    
                    <div>
                      <label className="block text-sm font-medium mb-1">Length</label>
                      <select
                        value={targetLength}
                        onChange={(e) => setTargetLength(e.target.value)}
                        className="w-full p-2 border rounded-md"
                      >
                        <option value="short">Short</option>
                        <option value="medium">Medium</option>
                        <option value="long">Long</option>
                      </select>
                    </div>
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium mb-1">Writing Style</label>
                    <select
                      value={writingStyle}
                      onChange={(e) => setWritingStyle(e.target.value)}
                      className="w-full p-2 border rounded-md"
                    >
                      <option value="professional">Professional</option>
                      <option value="casual">Casual</option>
                      <option value="academic">Academic</option>
                      <option value="technical">Technical</option>
                    </select>
                  </div>
                  
                  <Button
                    onClick={startGeneration}
                    disabled={isProcessing || !workflow.topic.trim()}
                    className="w-full"
                  >
                    {isProcessing ? (
                      <>
                        <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                        Starting...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 mr-2" />
                        Start Generation
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}
            
            {/* Section Generation/Refinement Phase */}
            {(workflow.phase === 'section-generation' || workflow.phase === 'section-refinement') && (
              <div className="space-y-4">
                {workflow.phase === 'section-generation' && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <FileText className="h-5 w-5" />
                        Generate Section
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <p className="text-sm text-gray-600 mb-4">
                        Ready to generate: {getCurrentSectionTitle()}
                      </p>
                      <Button
                        onClick={generateCurrentSection}
                        disabled={isProcessing}
                        className="w-full"
                      >
                        {isProcessing ? (
                          <>
                            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                            Generating...
                          </>
                        ) : (
                          <>
                            <FileText className="h-4 w-4 mr-2" />
                            Generate Section
                          </>
                        )}
                      </Button>
                    </CardContent>
                  </Card>
                )}
                
                {workflow.phase === 'section-refinement' && currentSectionContent && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2">
                        <Edit3 className="h-5 w-5" />
                        {getCurrentSectionTitle()}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="max-h-60 overflow-y-auto p-3 bg-gray-50 rounded text-sm">
                        <div className="whitespace-pre-wrap">{currentSectionContent}</div>
                      </div>
                      
                      <div className="space-y-3">
                        <Textarea
                          value={feedbackText}
                          onChange={(e) => setFeedbackText(e.target.value)}
                          placeholder="Provide feedback to refine this section, or click 'Move On' to proceed..."
                          className="min-h-[80px]"
                        />
                        
                        <div className="flex gap-2">
                          <Button
                            onClick={refineCurrentSection}
                            disabled={isProcessing || !feedbackText.trim()}
                            variant="outline"
                            className="flex-1"
                          >
                            {isProcessing ? (
                              <>
                                <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                                Refining...
                              </>
                            ) : (
                              <>
                                <Edit3 className="h-4 w-4 mr-2" />
                                Refine Section
                              </>
                            )}
                          </Button>
                          
                          <Button
                            onClick={moveToNextSection}
                            disabled={isProcessing}
                            className="flex-1"
                          >
                            <SkipForward className="h-4 w-4 mr-2" />
                            Move On
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
            
            {/* Final Review Phase */}
            {workflow.phase === 'final-review' && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5" />
                    Final Article Review
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="max-h-80 overflow-y-auto p-3 bg-gray-50 rounded text-sm">
                    <div className="whitespace-pre-wrap">{finalArticleText}</div>
                  </div>
                  
                  <div className="space-y-3">
                    <Textarea
                      value={feedbackText}
                      onChange={(e) => setFeedbackText(e.target.value)}
                      placeholder="Provide feedback to refine the complete article, or click 'Confirm as Completed'..."
                      className="min-h-[80px]"
                    />
                    
                    <div className="flex gap-2">
                      <Button
                        onClick={refineFinalArticle}
                        disabled={isProcessing || !feedbackText.trim()}
                        variant="outline"
                        className="flex-1"
                      >
                        {isProcessing ? (
                          <>
                            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                            Refining...
                          </>
                        ) : (
                          <>
                            <Edit3 className="h-4 w-4 mr-2" />
                            Refine Article
                          </>
                        )}
                      </Button>
                      
                      <Button
                        onClick={completeArticle}
                        disabled={isProcessing}
                        className="flex-1"
                      >
                        <CheckCircle2 className="h-4 w-4 mr-2" />
                        Confirm as Completed
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            
            {/* Completed Phase */}
            {workflow.phase === 'completed' && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                    Article Completed
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-center text-gray-600">
                    Your article has been completed successfully!
                  </p>
                  
                  <div className="flex gap-2">
                    <Button
                      onClick={downloadArticle}
                      className="flex-1"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Download Markdown
                    </Button>
                    
                    <Button
                      onClick={resetWorkflow}
                      variant="outline"
                      className="flex-1"
                    >
                      Start New Article
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
        
        {/* Right Panel - Activity Log */}
        <div className="w-1/3 flex flex-col">
          <div className="p-4 border-b bg-gray-50">
            <h3 className="font-semibold">Activity Log</h3>
          </div>
          
          <div className="flex-1 p-4 overflow-y-auto">
            <div className="space-y-3">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg text-sm ${
                    message.type === 'error' ? 'bg-red-50 border border-red-200 text-red-700' :
                    message.type === 'success' ? 'bg-green-50 border border-green-200 text-green-700' :
                    message.type === 'system' ? 'bg-blue-50 border border-blue-200 text-blue-700' :
                    'bg-gray-50 border border-gray-200 text-gray-700'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {message.type === 'error' && <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />}
                    {message.type === 'success' && <CheckCircle2 className="h-4 w-4 mt-0.5 flex-shrink-0" />}
                    {message.type === 'system' && <RefreshCw className="h-4 w-4 mt-0.5 flex-shrink-0" />}
                    {message.type === 'info' && <MessageSquare className="h-4 w-4 mt-0.5 flex-shrink-0" />}
                    
                    <div className="flex-1">
                      <div>{message.content}</div>
                      <div className="text-xs opacity-70 mt-1">
                        {message.timestamp.toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}