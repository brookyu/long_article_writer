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
  ThumbsUp, 
  ThumbsDown,
  RefreshCw,
  FileText,
  Users,
  Clock,
  Target
} from 'lucide-react';

interface EnhancedAgentChatProps {
  collectionId: number;
}

interface GenerationSession {
  session_id: string;
  current_phase: string;
  topic: string;
  sections_completed: number;
  total_sections: number;
}

interface SectionContent {
  section_id: string;
  title: string;
  content: string;
  word_count: number;
  status: 'draft' | 'approved' | 'needs_revision';
  sources_used: string[];
  confidence_score: number;
}

interface GenerationPhase {
  id: string;
  name: string;
  description: string;
  completed: boolean;
  current: boolean;
}

export function EnhancedAgentChat({ collectionId }: EnhancedAgentChatProps) {
  const { t } = useTranslation();
  
  // Core state
  const [session, setSession] = useState<GenerationSession | null>(null);
  const [currentPhase, setCurrentPhase] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState(false);
  
  // Generation content
  const [topic, setTopic] = useState('');
  const [articleType, setArticleType] = useState('comprehensive');
  const [targetLength, setTargetLength] = useState('medium');
  const [writingStyle, setWritingStyle] = useState('professional');
  
  // Research and outline
  const [researchData, setResearchData] = useState<any>(null);
  const [outline, setOutline] = useState<any>(null);
  const [outlineApproved, setOutlineApproved] = useState(false);
  
  // Sections
  const [sections, setSections] = useState<Record<string, SectionContent>>({});
  const [currentSectionId, setCurrentSectionId] = useState<string>('');
  const [sectionOrder, setSectionOrder] = useState<string[]>([]);
  
  // Feedback
  const [feedbackText, setFeedbackText] = useState('');
  const [feedbackType, setFeedbackType] = useState<'approve' | 'request_changes'>('approve');
  const [showFeedbackPanel, setShowFeedbackPanel] = useState(false);
  
  // UI state
  const [activeTab, setActiveTab] = useState('generation');
  const [messages, setMessages] = useState<Array<{
    type: string;
    content: string;
    timestamp: Date;
    phase?: string;
  }>>([]);
  
  // Progress tracking
  const phases: GenerationPhase[] = [
    { id: 'research', name: 'Research', description: 'Gathering relevant information', completed: false, current: false },
    { id: 'outline', name: 'Outline', description: 'Creating article structure', completed: false, current: false },
    { id: 'section_generation', name: 'Content', description: 'Writing sections', completed: false, current: false },
    { id: 'final_review', name: 'Review', description: 'Final review and refinement', completed: false, current: false },
    { id: 'completed', name: 'Complete', description: 'Article ready', completed: false, current: false }
  ];
  
  const [phaseProgress, setPhaseProgress] = useState<GenerationPhase[]>(phases);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const addMessage = (type: string, content: string, phase?: string) => {
    setMessages(prev => [...prev, {
      type,
      content,
      timestamp: new Date(),
      phase
    }]);
  };
  
  const updatePhaseProgress = (currentPhase: string) => {
    setPhaseProgress(prev => prev.map(phase => ({
      ...phase,
      completed: phases.findIndex(p => p.id === phase.id) < phases.findIndex(p => p.id === currentPhase),
      current: phase.id === currentPhase
    })));
  };
  
  const startGeneration = async () => {
    if (!topic.trim()) {
      addMessage('error', 'Please enter a topic for your article');
      return;
    }
    
    setIsGenerating(true);
    addMessage('system', `Starting enhanced article generation for: "${topic}"`);
    
    try {
      const response = await fetch(`/api/enhanced-agents/${collectionId}/start-generation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic,
          article_type: articleType,
          target_length: targetLength,
          writing_style: writingStyle,
          user_preferences: {}
        })
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        setSession({
          session_id: result.session_id,
          current_phase: result.current_phase,
          topic,
          sections_completed: 0,
          total_sections: 0
        });
        
        setCurrentPhase(result.current_phase);
        updatePhaseProgress(result.current_phase);
        addMessage('success', `Generation session started: ${result.session_id}`);
        
        // Automatically start research
        await processResearch(result.session_id);
      } else {
        addMessage('error', `Failed to start generation: ${result.message || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Generation start failed:', error);
      addMessage('error', `Failed to start generation: ${error}`);
    } finally {
      setIsGenerating(false);
    }
  };
  
  const processResearch = async (sessionId: string) => {
    addMessage('system', 'Starting research phase...', 'research');
    updatePhaseProgress('research');
    
    try {
      const response = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${sessionId}/research`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        setResearchData(result.data);
        addMessage('success', 'Research completed successfully', 'research');
        addMessage('info', `Found ${result.data?.data?.total_chunks_found || 0} relevant sources`);
        
        // Automatically generate outline
        await generateOutline(sessionId);
      } else {
        addMessage('error', 'Research phase failed');
      }
    } catch (error) {
      console.error('Research failed:', error);
      addMessage('error', `Research failed: ${error}`);
    }
  };
  
  const generateOutline = async (sessionId: string, researchFeedback = '') => {
    addMessage('system', 'Generating article outline...', 'outline');
    updatePhaseProgress('outline');
    
    try {
      const response = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${sessionId}/outline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ research_feedback: researchFeedback })
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        setOutline(result.outline);
        setShowFeedbackPanel(true);
        addMessage('success', 'Outline generated successfully', 'outline');
        addMessage('info', 'Please review the outline and provide feedback');
        setActiveTab('outline');
      } else {
        addMessage('error', 'Outline generation failed');
      }
    } catch (error) {
      console.error('Outline generation failed:', error);
      addMessage('error', `Outline generation failed: ${error}`);
    }
  };
  
  const approveOutline = async () => {
    if (!session) return;
    
    setOutlineApproved(true);
    setShowFeedbackPanel(false);
    addMessage('success', 'Outline approved, starting section generation');
    
    // Extract sections from outline and start generation
    if (outline && outline.sections) {
      const sectionIds = outline.sections.map((section: any, index: number) => 
        section.id || `section_${index}`
      );
      setSectionOrder(sectionIds);
      
      // Start generating first section
      if (sectionIds.length > 0) {
        await generateSection(session.session_id, sectionIds[0]);
      }
    }
  };
  
  const generateSection = async (sessionId: string, sectionId: string, sectionFeedback = '') => {
    setCurrentSectionId(sectionId);
    updatePhaseProgress('section_generation');
    
    const sectionTitle = outline?.sections?.find((s: any) => (s.id || `section_${outline.sections.indexOf(s)}`) === sectionId)?.title || 'Section';
    
    addMessage('system', `Generating section: ${sectionTitle}`, 'section_generation');
    
    try {
      const response = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${sessionId}/sections/${sectionId}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ section_feedback: sectionFeedback })
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        const sectionContent = result.section_content;
        setSections(prev => ({
          ...prev,
          [sectionId]: sectionContent
        }));
        
        addMessage('success', `Section "${sectionTitle}" generated (${sectionContent.word_count} words)`);
        setShowFeedbackPanel(true);
        setActiveTab('sections');
      } else {
        addMessage('error', `Section generation failed: ${result.message}`);
      }
    } catch (error) {
      console.error('Section generation failed:', error);
      addMessage('error', `Section generation failed: ${error}`);
    }
  };
  
  const provideSectionFeedback = async (sectionId: string, approved: boolean) => {
    if (!session) return;
    
    const feedback = {
      feedback_type: approved ? 'approve' : 'request_changes',
      feedback_text: approved ? 'Section approved' : feedbackText,
      specific_changes: approved ? null : feedbackText,
      priority: 'medium'
    };
    
    try {
      const response = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${session.session_id}/sections/${sectionId}/feedback`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(feedback)
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        if (approved) {
          // Update section status
          setSections(prev => ({
            ...prev,
            [sectionId]: { ...prev[sectionId], status: 'approved' }
          }));
          
          addMessage('success', `Section approved`);
          
          // Move to next section or finalize
          const currentIndex = sectionOrder.indexOf(sectionId);
          if (currentIndex < sectionOrder.length - 1) {
            const nextSectionId = sectionOrder[currentIndex + 1];
            await generateSection(session.session_id, nextSectionId);
          } else {
            // All sections complete, finalize article
            await finalizeArticle(session.session_id);
          }
        } else {
          // Section needs revision
          setSections(prev => ({
            ...prev,
            [sectionId]: { ...prev[sectionId], status: 'needs_revision' }
          }));
          
          addMessage('info', 'Section revised based on feedback');
          setShowFeedbackPanel(true);
        }
        
        setFeedbackText('');
      } else {
        addMessage('error', 'Failed to process feedback');
      }
    } catch (error) {
      console.error('Feedback processing failed:', error);
      addMessage('error', `Feedback processing failed: ${error}`);
    }
  };
  
  const finalizeArticle = async (sessionId: string) => {
    addMessage('system', 'Finalizing article...', 'final_review');
    updatePhaseProgress('final_review');
    
    try {
      const response = await fetch(`/api/enhanced-agents/${collectionId}/sessions/${sessionId}/finalize`, {
        method: 'POST'
      });
      
      const result = await response.json();
      
      if (result.status === 'success') {
        const finalizationResult = result.finalization_result;
        
        if (finalizationResult.status === 'completed') {
          addMessage('success', `Article completed! ${finalizationResult.total_words} words, ${finalizationResult.sections_count} sections`);
          updatePhaseProgress('completed');
          setActiveTab('final');
        } else {
          addMessage('info', 'Article ready for final review');
          setShowFeedbackPanel(true);
        }
      } else {
        addMessage('error', 'Article finalization failed');
      }
    } catch (error) {
      console.error('Finalization failed:', error);
      addMessage('error', `Finalization failed: ${error}`);
    }
  };
  
  const resetGeneration = () => {
    setSession(null);
    setCurrentPhase('');
    setResearchData(null);
    setOutline(null);
    setOutlineApproved(false);
    setSections({});
    setCurrentSectionId('');
    setSectionOrder([]);
    setMessages([]);
    setPhaseProgress(phases);
    setShowFeedbackPanel(false);
    setActiveTab('generation');
  };
  
  const getPhaseIcon = (phase: GenerationPhase) => {
    if (phase.completed) return <CheckCircle2 className="h-5 w-5 text-green-500" />;
    if (phase.current) return <RefreshCw className="h-5 w-5 text-blue-500 animate-spin" />;
    return <div className="h-5 w-5 rounded-full border-2 border-gray-300" />;
  };
  
  const calculateProgress = () => {
    const completedPhases = phaseProgress.filter(p => p.completed).length;
    return (completedPhases / phaseProgress.length) * 100;
  };
  
  return (
    <div className="flex flex-col h-full max-h-screen">
      {/* Header with Progress */}
      <div className="border-b p-4 bg-white">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold">Enhanced AI Article Generation</h2>
          {session && (
            <Badge variant="outline" className="text-sm">
              Session: {session.session_id.slice(-8)}
            </Badge>
          )}
        </div>
        
        {/* Progress Bar */}
        <div className="space-y-2">
          <Progress value={calculateProgress()} className="w-full" />
          <div className="flex justify-between items-center">
            {phaseProgress.map((phase, index) => (
              <div key={phase.id} className="flex flex-col items-center space-y-1">
                {getPhaseIcon(phase)}
                <span className={`text-xs ${phase.current ? 'text-blue-600 font-medium' : phase.completed ? 'text-green-600' : 'text-gray-500'}`}>
                  {phase.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Generation Controls */}
        <div className="w-1/3 border-r p-4 overflow-y-auto">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-4">
              <TabsTrigger value="generation">Setup</TabsTrigger>
              <TabsTrigger value="outline">Outline</TabsTrigger>
              <TabsTrigger value="sections">Sections</TabsTrigger>
              <TabsTrigger value="final">Final</TabsTrigger>
            </TabsList>
            
            <TabsContent value="generation" className="space-y-4">
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
                      value={topic}
                      onChange={(e) => setTopic(e.target.value)}
                      placeholder="Enter your article topic..."
                      className="min-h-[80px]"
                      disabled={!!session}
                    />
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">Type</label>
                      <select
                        value={articleType}
                        onChange={(e) => setArticleType(e.target.value)}
                        className="w-full p-2 border rounded-md"
                        disabled={!!session}
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
                        disabled={!!session}
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
                      disabled={!!session}
                    >
                      <option value="professional">Professional</option>
                      <option value="casual">Casual</option>
                      <option value="academic">Academic</option>
                      <option value="technical">Technical</option>
                    </select>
                  </div>
                  
                  <div className="flex gap-2">
                    <Button
                      onClick={startGeneration}
                      disabled={isGenerating || !!session}
                      className="flex-1"
                    >
                      {isGenerating ? (
                        <>
                          <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                          Starting...
                        </>
                      ) : (
                        'Start Generation'
                      )}
                    </Button>
                    
                    {session && (
                      <Button
                        onClick={resetGeneration}
                        variant="outline"
                      >
                        Reset
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>
            
            <TabsContent value="outline" className="space-y-4">
              {outline && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <FileText className="h-5 w-5" />
                      Article Outline
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="prose prose-sm max-w-none">
                      <pre className="whitespace-pre-wrap text-sm bg-gray-50 p-3 rounded">
                        {outline.outline_text || JSON.stringify(outline, null, 2)}
                      </pre>
                    </div>
                    
                    {!outlineApproved && showFeedbackPanel && (
                      <div className="mt-4 space-y-3 p-3 bg-gray-50 rounded-md">
                        <h4 className="font-medium">Outline Feedback</h4>
                        <Textarea
                          value={feedbackText}
                          onChange={(e) => setFeedbackText(e.target.value)}
                          placeholder="Provide feedback on the outline..."
                          className="min-h-[60px]"
                        />
                        <div className="flex gap-2">
                          <Button
                            onClick={approveOutline}
                            className="flex items-center gap-2"
                          >
                            <ThumbsUp className="h-4 w-4" />
                            Approve
                          </Button>
                          <Button
                            onClick={() => generateOutline(session?.session_id || '', feedbackText)}
                            variant="outline"
                            className="flex items-center gap-2"
                          >
                            <Edit3 className="h-4 w-4" />
                            Request Changes
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </TabsContent>
            
            <TabsContent value="sections" className="space-y-4">
              {Object.entries(sections).map(([sectionId, section]) => (
                <Card key={sectionId}>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span className="flex items-center gap-2">
                        <FileText className="h-4 w-4" />
                        {section.title}
                      </span>
                      <Badge
                        variant={
                          section.status === 'approved' ? 'default' :
                          section.status === 'needs_revision' ? 'destructive' : 'secondary'
                        }
                      >
                        {section.status}
                      </Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-sm text-gray-600 mb-2">
                      {section.word_count} words • Confidence: {(section.confidence_score * 100).toFixed(0)}%
                    </div>
                    <div className="prose prose-sm max-w-none">
                      <div className="whitespace-pre-wrap text-sm">{section.content}</div>
                    </div>
                    
                    {currentSectionId === sectionId && showFeedbackPanel && section.status !== 'approved' && (
                      <div className="mt-4 space-y-3 p-3 bg-gray-50 rounded-md">
                        <h4 className="font-medium">Section Feedback</h4>
                        <Textarea
                          value={feedbackText}
                          onChange={(e) => setFeedbackText(e.target.value)}
                          placeholder="Provide feedback on this section..."
                          className="min-h-[60px]"
                        />
                        <div className="flex gap-2">
                          <Button
                            onClick={() => provideSectionFeedback(sectionId, true)}
                            className="flex items-center gap-2"
                          >
                            <ThumbsUp className="h-4 w-4" />
                            Approve
                          </Button>
                          <Button
                            onClick={() => provideSectionFeedback(sectionId, false)}
                            variant="outline"
                            className="flex items-center gap-2"
                            disabled={!feedbackText.trim()}
                          >
                            <Edit3 className="h-4 w-4" />
                            Request Changes
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </TabsContent>
            
            <TabsContent value="final" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5" />
                    Article Complete
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2 text-sm">
                    <div>Total Sections: {Object.keys(sections).length}</div>
                    <div>Total Words: {Object.values(sections).reduce((sum, s) => sum + s.word_count, 0)}</div>
                    <div>Approved Sections: {Object.values(sections).filter(s => s.status === 'approved').length}</div>
                  </div>
                  
                  <Button className="w-full mt-4">
                    Export Article
                  </Button>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
        
        {/* Right Panel - Messages and Activity */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 p-4 overflow-y-auto">
            <div className="space-y-3">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`p-3 rounded-lg ${
                    message.type === 'error' ? 'bg-red-50 border border-red-200' :
                    message.type === 'success' ? 'bg-green-50 border border-green-200' :
                    message.type === 'system' ? 'bg-blue-50 border border-blue-200' :
                    'bg-gray-50 border border-gray-200'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {message.type === 'error' && <AlertCircle className="h-4 w-4 text-red-500 mt-0.5" />}
                    {message.type === 'success' && <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5" />}
                    {message.type === 'system' && <RefreshCw className="h-4 w-4 text-blue-500 mt-0.5" />}
                    {message.type === 'info' && <MessageSquare className="h-4 w-4 text-gray-500 mt-0.5" />}
                    
                    <div className="flex-1">
                      <div className="text-sm">{message.content}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {message.timestamp.toLocaleTimeString()}
                        {message.phase && ` • ${message.phase}`}
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