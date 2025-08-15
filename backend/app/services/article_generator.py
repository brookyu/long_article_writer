"""
AI-powered article generation service using knowledge base and LLM
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class ArticleResearcher:
    """Research assistant that finds relevant content from knowledge base"""
    
    def __init__(self, search_function):
        self.search_function = search_function
    
    async def research_topic(
        self, 
        collection_id: int, 
        topic: str, 
        subtopics: List[str] = None,
        max_chunks_per_search: int = 5
    ) -> Dict[str, Any]:
        """
        Research a topic using semantic search across the knowledge base
        
        Returns:
            Dict containing research results organized by search queries
        """
        try:
            research_results = {
                "main_topic": topic,
                "research_data": {},
                "total_chunks_found": 0,
                "unique_documents": set(),
                "search_queries_used": []
            }
            
            # Research main topic
            logger.info(f"Researching main topic: {topic}")
            main_results = await self.search_function(collection_id, topic)
            
            research_results["research_data"]["main_topic"] = {
                "query": topic,
                "results": main_results.get("matches", [])[:max_chunks_per_search],
                "total_found": main_results.get("total_matches", 0)
            }
            research_results["search_queries_used"].append(topic)
            
            # Track statistics
            for match in main_results.get("matches", []):
                research_results["unique_documents"].add(match.get("document_id"))
                research_results["total_chunks_found"] += 1
            
            # Research subtopics if provided
            if subtopics:
                for subtopic in subtopics:
                    logger.info(f"Researching subtopic: {subtopic}")
                    subtopic_results = await self.search_function(collection_id, subtopic)
                    
                    research_results["research_data"][f"subtopic_{subtopic}"] = {
                        "query": subtopic,
                        "results": subtopic_results.get("matches", [])[:max_chunks_per_search],
                        "total_found": subtopic_results.get("total_matches", 0)
                    }
                    research_results["search_queries_used"].append(subtopic)
                    
                    # Update statistics
                    for match in subtopic_results.get("matches", []):
                        research_results["unique_documents"].add(match.get("document_id"))
                        research_results["total_chunks_found"] += 1
            
            # Convert set to list for JSON serialization
            research_results["unique_documents"] = list(research_results["unique_documents"])
            
            logger.info(f"Research completed: {research_results['total_chunks_found']} chunks from {len(research_results['unique_documents'])} documents")
            
            return research_results
            
        except Exception as e:
            logger.error(f"Research failed: {e}")
            return {
                "main_topic": topic,
                "research_data": {},
                "total_chunks_found": 0,
                "unique_documents": [],
                "search_queries_used": [],
                "error": str(e)
            }


class ArticleOutlineGenerator:
    """Generates article outlines using AI"""
    
    def __init__(self, llm_function):
        self.llm_function = llm_function
    
    async def generate_outline(
        self, 
        topic: str, 
        research_summary: str,
        article_type: str = "comprehensive",
        target_length: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate an article outline based on topic and research
        
        Args:
            topic: Main article topic
            research_summary: Summary of research findings
            article_type: Type of article (comprehensive, tutorial, analysis, etc.)
            target_length: Target length (short, medium, long)
        
        Returns:
            Dict containing the generated outline
        """
        
        length_guidance = {
            "short": "3-5 main sections, suitable for a brief overview (500-1000 words)",
            "medium": "5-7 main sections with subsections, comprehensive coverage (1000-2500 words)",
            "long": "7+ main sections with detailed subsections, in-depth analysis (2500+ words)"
        }
        
        type_guidance = {
            "comprehensive": "Cover all major aspects of the topic with balanced depth",
            "tutorial": "Step-by-step instructional format with practical examples",
            "analysis": "Critical examination with pros/cons, implications, and conclusions",
            "overview": "High-level summary suitable for general audiences",
            "technical": "Detailed technical content for expert audiences"
        }
        
        prompt = f"""Create a detailed article outline for the topic: "{topic}"

Article Type: {article_type} - {type_guidance.get(article_type, "Comprehensive coverage")}
Target Length: {target_length} - {length_guidance.get(target_length, "Medium length")}

Available Research Context:
{research_summary}

Please generate a well-structured outline that includes:
1. A compelling title
2. Introduction that hooks the reader
3. Main sections with descriptive headings
4. Relevant subsections where appropriate
5. A strong conclusion
6. Estimated word count for each section

Format the outline as follows:
# [Article Title]

## Introduction
- [Brief description of what will be covered]
- Estimated words: [X]

## [Section 1 Title]
- [Key points to cover]
- Subsections if needed
- Estimated words: [X]

[Continue for all sections...]

## Conclusion
- [Summary and final thoughts]
- Estimated words: [X]

Please ensure the outline flows logically and covers the topic comprehensively based on the available research."""

        try:
            logger.info(f"Generating outline for: {topic}")
            outline_text = await self.llm_function(prompt, max_tokens=1500)
            
            return {
                "topic": topic,
                "article_type": article_type,
                "target_length": target_length,
                "outline_text": outline_text,
                "generated_at": datetime.now().isoformat(),
                "sections": self._parse_outline_sections(outline_text)
            }
            
        except Exception as e:
            logger.error(f"Outline generation failed: {e}")
            return {
                "topic": topic,
                "article_type": article_type,
                "target_length": target_length,
                "outline_text": f"Error generating outline: {str(e)}",
                "generated_at": datetime.now().isoformat(),
                "sections": [],
                "error": str(e)
            }
    
    def _parse_outline_sections(self, outline_text: str) -> List[Dict[str, Any]]:
        """Parse outline text into structured sections"""
        sections = []
        
        # Simple parsing logic - can be enhanced
        lines = outline_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('# '):
                # Article title
                continue
            elif line.startswith('## '):
                # Main section
                if current_section:
                    sections.append(current_section)
                current_section = {
                    "title": line[3:].strip(),
                    "type": "section",
                    "content": [],
                    "estimated_words": 0
                }
            elif line.startswith('### '):
                # Subsection
                if current_section:
                    current_section["content"].append({
                        "type": "subsection",
                        "title": line[4:].strip()
                    })
            elif line.startswith('- ') and current_section:
                # Bullet point
                current_section["content"].append({
                    "type": "point",
                    "text": line[2:].strip()
                })
            elif "Estimated words:" in line and current_section:
                # Extract word count estimate
                try:
                    words = re.search(r'(\d+)', line)
                    if words:
                        current_section["estimated_words"] = int(words.group(1))
                except:
                    pass
        
        if current_section:
            sections.append(current_section)
        
        return sections


class ArticleContentGenerator:
    """Generates article content based on outline and research"""
    
    def __init__(self, llm_function, search_function):
        self.llm_function = llm_function
        self.search_function = search_function
    
    async def generate_section(
        self,
        collection_id: int,
        section_title: str,
        section_context: str,
        research_data: Dict[str, Any],
        writing_style: str = "professional"
    ) -> str:
        """Generate content for a specific section"""
        
        # Find most relevant research chunks for this section
        relevant_chunks = await self._find_relevant_content(
            collection_id, section_title, research_data
        )
        
        style_instructions = {
            "professional": "Use formal, authoritative tone with clear explanations",
            "conversational": "Use friendly, engaging tone that speaks directly to the reader",
            "academic": "Use scholarly tone with precise terminology and citations",
            "technical": "Use technical language appropriate for expert audiences",
            "casual": "Use relaxed, approachable tone suitable for general audiences"
        }
        
        relevant_content = "\n\n".join([
            f"Source {i+1}: {chunk.get('preview', '')}"
            for i, chunk in enumerate(relevant_chunks[:3])  # Use top 3 most relevant
        ])
        
        prompt = f"""Write a detailed section for an article with the following specifications:

Section Title: {section_title}
Section Context: {section_context}
Writing Style: {writing_style} - {style_instructions.get(writing_style, 'Professional tone')}

Relevant Source Material:
{relevant_content}

Please write a comprehensive section that:
1. Directly addresses the section title
2. Uses information from the provided sources naturally
3. Maintains the specified writing style
4. Includes specific examples and details where appropriate
5. Flows well and engages the reader
6. Is approximately 200-400 words

Write only the section content without the section heading."""

        try:
            logger.info(f"Generating content for section: {section_title}")
            section_content = await self.llm_function(prompt, max_tokens=800)
            return section_content.strip()
            
        except Exception as e:
            logger.error(f"Section generation failed for '{section_title}': {e}")
            return f"[Error generating content for section: {section_title}]"
    
    async def _find_relevant_content(
        self, 
        collection_id: int, 
        section_title: str, 
        research_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Find the most relevant research content for a section"""
        
        # Try semantic search for this specific section
        try:
            section_results = await self.search_function(collection_id, section_title)
            section_chunks = section_results.get("matches", [])
        except:
            section_chunks = []
        
        # Combine with existing research data
        all_chunks = section_chunks[:]
        
        for research_key, research_info in research_data.get("research_data", {}).items():
            all_chunks.extend(research_info.get("results", []))
        
        # Simple relevance scoring based on title keywords
        section_keywords = set(section_title.lower().split())
        
        for chunk in all_chunks:
            preview = chunk.get("preview", "").lower()
            keyword_matches = sum(1 for keyword in section_keywords if keyword in preview)
            chunk["section_relevance"] = keyword_matches / len(section_keywords) if section_keywords else 0
        
        # Sort by relevance and return top chunks
        all_chunks.sort(key=lambda x: x.get("section_relevance", 0), reverse=True)
        
        return all_chunks[:5]  # Return top 5 most relevant chunks


class ArticleGenerator:
    """Main article generation orchestrator"""
    
    def __init__(self, llm_function, search_function):
        self.researcher = ArticleResearcher(search_function)
        self.outline_generator = ArticleOutlineGenerator(llm_function)
        self.content_generator = ArticleContentGenerator(llm_function, search_function)
    
    async def generate_article(
        self,
        collection_id: int,
        topic: str,
        subtopics: List[str] = None,
        article_type: str = "comprehensive",
        target_length: str = "medium",
        writing_style: str = "professional"
    ) -> Dict[str, Any]:
        """
        Generate a complete article using the full pipeline
        
        Returns:
            Dict containing the complete article and metadata
        """
        generation_start = datetime.now()
        
        try:
            logger.info(f"Starting article generation for: {topic}")
            
            # Step 1: Research the topic
            logger.info("Step 1: Researching topic...")
            research_results = await self.researcher.research_topic(
                collection_id, topic, subtopics
            )
            
            if research_results.get("error"):
                return {
                    "status": "failed",
                    "error": f"Research failed: {research_results['error']}",
                    "topic": topic
                }
            
            # Create research summary
            research_summary = f"""
Research Summary for "{topic}":
- Total relevant chunks found: {research_results['total_chunks_found']}
- Documents consulted: {len(research_results['unique_documents'])}
- Search queries used: {', '.join(research_results['search_queries_used'])}

Key findings from research:
"""
            
            for research_key, research_info in research_results["research_data"].items():
                top_result = research_info["results"][0] if research_info["results"] else None
                if top_result:
                    research_summary += f"- {research_info['query']}: {top_result.get('preview', '')[:100]}...\n"
            
            # Step 2: Generate outline
            logger.info("Step 2: Generating article outline...")
            outline_result = await self.outline_generator.generate_outline(
                topic, research_summary, article_type, target_length
            )
            
            if outline_result.get("error"):
                return {
                    "status": "failed",
                    "error": f"Outline generation failed: {outline_result['error']}",
                    "topic": topic,
                    "research_results": research_results
                }
            
            # Step 3: Generate content for each section
            logger.info("Step 3: Generating article content...")
            full_article_content = []
            
            # Add title and introduction
            article_lines = outline_result["outline_text"].split('\n')
            title = next((line[2:].strip() for line in article_lines if line.startswith('# ')), topic)
            
            full_article_content.append(f"# {title}\n")
            
            # Generate content for each section
            sections_generated = 0
            for section in outline_result.get("sections", []):
                section_title = section.get("title", "")
                section_context = f"Section about {section_title} in an article about {topic}"
                
                section_content = await self.content_generator.generate_section(
                    collection_id,
                    section_title,
                    section_context,
                    research_results,
                    writing_style
                )
                
                full_article_content.append(f"## {section_title}\n")
                full_article_content.append(f"{section_content}\n")
                sections_generated += 1
                
                logger.info(f"Generated section {sections_generated}/{len(outline_result.get('sections', []))}: {section_title}")
            
            # Combine all content
            article_text = "\n".join(full_article_content)
            
            generation_end = datetime.now()
            generation_time = (generation_end - generation_start).total_seconds()
            
            # Calculate statistics
            word_count = len(article_text.split())
            
            result = {
                "status": "success",
                "topic": topic,
                "article": {
                    "title": title,
                    "content": article_text,
                    "word_count": word_count,
                    "sections_count": sections_generated
                },
                "metadata": {
                    "article_type": article_type,
                    "target_length": target_length,
                    "writing_style": writing_style,
                    "generation_time_seconds": generation_time,
                    "generated_at": generation_end.isoformat()
                },
                "research_summary": {
                    "total_chunks_used": research_results["total_chunks_found"],
                    "documents_consulted": len(research_results["unique_documents"]),
                    "search_queries": research_results["search_queries_used"]
                },
                "outline": outline_result
            }
            
            logger.info(f"Article generation completed: {word_count} words in {generation_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Article generation failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "topic": topic,
                "generation_time_seconds": (datetime.now() - generation_start).total_seconds()
            }