from typing import List
from fastapi import HTTPException
from datetime import datetime
import uuid

from src.services.gemini_service import gemini_service
from src.core.data_store import get_pdf_metadata
from src.core.models import (
    QuestionPaperAnalysisResponse, 
    UnitAnalysis, 
    QuestionPattern
)

async def analyze_question_papers_service(
    syllabus_pdf_id: str, 
    question_paper_pdf_ids: List[str],
    user_id: str
) -> QuestionPaperAnalysisResponse:
    """
    Analyze question papers using syllabus and previous year papers
    """
    if not gemini_service:
        raise HTTPException(
            status_code=500,
            detail="Gemini API is not configured. Please set GEMINI_API_KEY."
        )
    
    try:
        # Get syllabus PDF metadata and verify ownership
        syllabus_pdf = await get_pdf_metadata(syllabus_pdf_id)
        if not syllabus_pdf:
            raise HTTPException(
                status_code=404,
                detail=f"Syllabus PDF with ID {syllabus_pdf_id} not found"
            )
        
        if syllabus_pdf["user_id"] != user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this syllabus PDF"
            )
        
        # Get question paper PDFs metadata and verify ownership
        question_papers = []
        for pdf_id in question_paper_pdf_ids:
            pdf = await get_pdf_metadata(pdf_id)
            if not pdf:
                raise HTTPException(
                    status_code=404,
                    detail=f"Question paper PDF with ID {pdf_id} not found"
                )
            
            if pdf["user_id"] != user_id:
                raise HTTPException(
                    status_code=403,
                    detail=f"You don't have permission to access question paper PDF {pdf_id}"
                )
            
            question_papers.append(pdf)
        
        # Extract text content from syllabus
        syllabus_content = await gemini_service.extract_text_from_pdf(syllabus_pdf["file_path"])
        
        # Extract text content from all question papers
        question_papers_content = []
        for paper in question_papers:
            content = await gemini_service.extract_text_from_pdf(paper["file_path"])
            question_papers_content.append(content)
        
        # Analyze using Gemini
        analysis_result = await gemini_service.analyze_question_papers(
            syllabus_content, 
            question_papers_content
        )
        
        # Generate analysis ID
        analysis_id = str(uuid.uuid4())
        
        # Convert to response model
        unit_analyses = [
            UnitAnalysis(
                unit_name=unit["unit_name"],
                weightage_percentage=unit["weightage_percentage"],
                important_topics=unit["important_topics"],
                difficulty_level=unit["difficulty_level"],
                recommendation=unit["recommendation"]
            )
            for unit in analysis_result["unit_wise_analysis"]
        ]
        
        question_patterns = [
            QuestionPattern(
                question_type=pattern["question_type"],
                marks_distribution=pattern["marks_distribution"],
                frequency=pattern["frequency"],
                examples=pattern["examples"]
            )
            for pattern in analysis_result["question_patterns"]
        ]
        
        return QuestionPaperAnalysisResponse(
            analysis_id=analysis_id,
            overall_summary=analysis_result["overall_summary"],
            focus_areas=analysis_result["focus_areas"],
            unit_wise_analysis=unit_analyses,
            question_patterns=question_patterns,
            sample_questions=analysis_result["sample_questions"],
            preparation_strategy=analysis_result["preparation_strategy"],
            created_at=datetime.now()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing question papers: {str(e)}"
        )
