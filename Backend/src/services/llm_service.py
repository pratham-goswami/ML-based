import json
import asyncio
from typing import Dict, Any, Optional, Tuple
from fastapi import HTTPException
from src.services.pdf_service import get_relevant_context
from src.services.gemini_service import gemini_service

async def ask_question(question: str, pdf_id: Optional[str] = None, stream: bool = False):
    """
    Ask a question to the LLM with or without PDF context
    """
    context = ""
    
    # Get context from PDF if pdf_id is provided
    if pdf_id:
        try:
            context, _ = await get_relevant_context(pdf_id, question, top_k=3)
        except Exception as e:
            raise HTTPException(
                status_code=400, 
                detail=f"Error getting context from PDF: {str(e)}"
            )
    
    # Generate the prompt with or without context
    if context:
        prompt = f"""You are an AI tutor. Answer the question strictly based on the provided textbook excerpts.  

        - Provide a clear, concise, and well-structured answer.  
        - Focus on key points that are important for exams.  
        - Avoid unnecessary introductions—start directly with the answer.  
        - If necessary, break down complex ideas into simpler explanations.  
        - If the context does not contain relevant information, state that the question is not covered in the given context.  

        **Context:** {context}  

        **Question:** {question}  

        **Exam-Focused Answer:**  

        """
    else:
        prompt = f"""You are an AI tutor. 

        - Provide a clear, concise, and well-structured answer.  
        - Focus on key points that are important for exams.  
        - Avoid unnecessary introductions—start directly with the answer.  
        - If necessary, break down complex ideas into simpler explanations.  

        **Question:** {question}  

        **Exam-Focused Answer:**  

        """
    
    # Handle streaming or non-streaming response
    if stream:
        return await stream_llm_response(prompt, context)
    else:
        return await get_llm_response(prompt, context)

async def get_llm_response(prompt: str, context: str = ""):
    """
    Get a non-streaming response from Gemini LLM
    """
    if not gemini_service:
        raise HTTPException(
            status_code=503,
            detail="Gemini service is not available. Please check GEMINI_API_KEY configuration."
        )
    
    try:
        # Send request to Gemini API
        response = gemini_service.model.generate_content(prompt)
        
        if not response or not response.text:
            raise HTTPException(
                status_code=500,
                detail="Empty response from Gemini API"
            )
        
        return {
            "answer": response.text.strip(),
            "context": context
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error generating response from Gemini: {str(e)}"
        )

async def stream_llm_response(prompt: str, context: str = ""):
    """
    Get a streaming response from Gemini LLM
    """
    if not gemini_service:
        async def error_response():
            yield json.dumps({"error": "Gemini service is not available. Please check GEMINI_API_KEY configuration."}) + "\n"
        return error_response
    
    async def stream_response():
        try:
            # Add context as first chunk if available
            if context:
                context_data = {"context": context}
                yield json.dumps(context_data) + "\n"
            
            # Use Gemini's streaming API
            response = gemini_service.model.generate_content(prompt, stream=True)
            
            # Stream the response chunks
            for chunk in response:
                if chunk.text:
                    # Format as JSON similar to Ollama's response format
                    data = {
                        "response": chunk.text,
                        "done": False
                    }
                    yield json.dumps(data) + "\n"
            
            # Send final chunk indicating completion
            yield json.dumps({"response": "", "done": True}) + "\n"
            
        except Exception as e:
            error_data = {"error": f"Error generating streaming response from Gemini: {str(e)}"}
            yield json.dumps(error_data) + "\n"
    
    return stream_response
