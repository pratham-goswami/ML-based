import json
import google.generativeai as genai
from typing import List, Dict, Any
from fastapi import HTTPException
from src.core.config import GEMINI_API_KEY
import PyPDF2

class GeminiService:
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not set in environment variables")
        
        genai.configure(api_key=GEMINI_API_KEY)
        
        # Configure generation settings for more reliable JSON output
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,  # Lower temperature for more consistent output
            top_p=0.8,
            top_k=40,
            max_output_tokens=8192,
        )
        
        self.model = genai.GenerativeModel(
            'gemini-2.0-flash-exp',
            generation_config=generation_config
        )
    
    async def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text content from a PDF file"""
        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            raise HTTPException(
                status_code=500, 
                detail=f"Error extracting text from PDF: {str(e)}"
            )
    
    async def analyze_question_papers(
        self, 
        syllabus_content: str, 
        question_papers_content: List[str]
    ) -> Dict[str, Any]:
        """Analyze question papers using Gemini 2.0 Flash"""
        
        # Combine all question papers content
        combined_question_papers = "\n\n---NEW QUESTION PAPER---\n\n".join(question_papers_content)
        
        prompt = f"""You are an expert academic analyst. Analyze the syllabus and question papers to generate insights.

SYLLABUS:
{syllabus_content[:2000]}

QUESTION PAPERS:
{combined_question_papers[:4000]}

RESPOND ONLY WITH VALID JSON IN THIS EXACT FORMAT:
{{
    "overall_summary": "Brief summary of patterns observed",
    "focus_areas": ["topic1", "topic2", "topic3", "topic4", "topic5"],
    "unit_wise_analysis": [
    There are typically 5 units in a syllabus, each with its own weightage and important topics.
    list them all and add a recommendation for each unit.
        {{
            "unit_name": "Unit 1",
            "weightage_percentage": 20.0,
            "important_topics": ["topic1", "topic2"],
            "difficulty_level": "Medium",
            "recommendation": "Study strategy"
        }}
    ],
    "question_patterns": [
        {{
            "question_type": "MCQ",
            "marks_distribution": {{"2_marks": 5, "5_marks": 3}},
            "frequency": 8,
            "examples": ["example1", "example2"]
        }}
    ],
    "sample_questions": [
        You need to generate sample questions based on the patterns observed in the syllabus and question papers. Provide 10 sample questions that reflect the types of questions typically asked in exams, such as conceptual understanding, problem-solving, and application-based questions.
        try to keep the questions relevant to the syllabus and question papers provided. 
        "Sample question 1?",
        "Sample question 2?",
        "Sample question 3?"
    ],
    "preparation_strategy": "Step by step preparation guide"
}}

IMPORTANT: Return ONLY the JSON object, no additional text or explanation."""
        
        try:
            response = self.model.generate_content(prompt)
            
            # Check if response is valid
            if not response or not response.text:
                raise HTTPException(
                    status_code=500,
                    detail="Empty response from Gemini API"
                )
            
            response_text = response.text.strip()
            
            # Log the raw response for debugging
            print(f"Raw Gemini response: {response_text[:500]}...")
            
            # Try to extract JSON from the response
            # Sometimes Gemini adds extra text before/after JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                # If no JSON found, create a fallback response
                return self._create_fallback_analysis()
            
            json_text = response_text[start_idx:end_idx]
            
            # Parse the JSON response
            analysis_result = json.loads(json_text)
            return analysis_result
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"Response text: {response.text if response else 'No response'}")
            return self._create_fallback_analysis()
            
        except Exception as e:
            print(f"General error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Error analyzing question papers with Gemini: {str(e)}"
            )
    
    def _create_fallback_analysis(self) -> Dict[str, Any]:
        """Create a fallback analysis when Gemini fails"""
        return {
            "overall_summary": "Unable to generate detailed analysis due to API response issues. Please ensure your documents contain clear, readable text and try again.",
            "focus_areas": [
                "Review your uploaded documents",
                "Ensure PDFs contain readable text",
                "Check document quality",
                "Retry analysis with better quality documents"
            ],
            "unit_wise_analysis": [
                {
                    "unit_name": "General Study Areas",
                    "weightage_percentage": 25.0,
                    "important_topics": ["Core concepts", "Fundamental principles", "Problem solving"],
                    "difficulty_level": "Medium",
                    "recommendation": "Focus on understanding basic concepts and practice regular problem solving"
                }
            ],
            "question_patterns": [
                {
                    "question_type": "Multiple Choice Questions",
                    "marks_distribution": {"2_marks": 10, "5_marks": 5, "10_marks": 2},
                    "frequency": 15,
                    "examples": ["Conceptual questions", "Application-based problems"]
                }
            ],
            "sample_questions": [
                "What are the fundamental concepts covered in this subject?",
                "Explain the key principles with examples.",
                "Solve problems related to core topics.",
                "Compare and contrast different approaches.",
                "Analyze the given scenario and provide solutions."
                "What are the common mistakes students make in this subject?",
            ],
            "preparation_strategy": "1. Start with basic concepts\n2. Practice previous year questions\n3. Focus on understanding rather than memorization\n4. Regular revision of important topics\n5. Time management during exams"
        }

# Create global instance with proper error handling
try:
    gemini_service = GeminiService() if GEMINI_API_KEY else None
    if gemini_service:
        print("✓ Gemini service initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize Gemini service: {str(e)}")
    gemini_service = None
